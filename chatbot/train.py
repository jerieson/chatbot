# chatbot/train.py

"""
Training Script

This script:
1. Loads the training data (intents.json)
2. Masks names ("What type is Pikachu?" -> "what type is pokemon")
3. Turns each sentence into an embedding with a pretrained model
4. Trains a small neural network to map embeddings to intents
5. Measures accuracy on held-out questions (intent_eval.json)
6. Saves the trained model

Key Training Concepts:
- Loss function: measures how wrong the model is
- Optimizer: adjusts weights to minimize loss
- Epochs: number of times to go through all training data
- Backpropagation: how the network learns from mistakes
- Label smoothing / weight decay: keep the model from becoming overconfident, so its
  confidence score is meaningful for the fallback threshold

Run from the project root:  python chatbot/train.py
"""

import json
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Make the project root importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import config  # noqa: E402
from chatbot.embedder import Embedder  # noqa: E402
from chatbot.intent_classifier import IntentClassifier  # noqa: E402
from chatbot.pokedex import Pokedex  # noqa: E402

EVAL_PATH = config.PROJECT_ROOT / "chatbot" / "data" / "intent_eval.json"


def evaluate(model, embedder, pokedex, tags, examples, device, threshold):
    """Accuracy on held-out (question, intent) pairs, overall and above the threshold."""
    model.eval()
    with torch.no_grad():
        X = torch.from_numpy(embedder.encode([pokedex.mask(q) for q, _ in examples])).to(device)
        probs = torch.softmax(model(X), dim=1)
        confidence, predicted = torch.max(probs, dim=1)

    results = [(q, expected, tags[p], c) for (q, expected), p, c
               in zip(examples, predicted.tolist(), confidence.tolist())]
    correct = sum(expected == got for _, expected, got, _ in results)
    confident = [r for r in results if r[3] >= threshold]
    confident_correct = sum(expected == got for _, expected, got, _ in confident)
    return {
        "accuracy": correct / len(results),
        "coverage": len(confident) / len(results),  # share of questions above the threshold
        "precision": confident_correct / len(confident) if confident else 0.0,  # accuracy above it
        "mistakes": [r for r in results if r[1] != r[2]],
    }


def train_chatbot(
    data_path=config.INTENTS_PATH,
    save_path=config.MODEL_PATH,
    hidden_size=config.HIDDEN_SIZE,
    num_epochs=config.NUM_EPOCHS,
    batch_size=config.BATCH_SIZE,
    learning_rate=config.LEARNING_RATE,
    seed=42,
):
    """
    Main training function

    Args:
        data_path: path to intents.json
        save_path: where to write the trained model
        hidden_size: number of neurons in the hidden layer
        num_epochs: number of training iterations
        batch_size: number of samples per batch
        learning_rate: how fast the model learns
        seed: makes training reproducible
    """
    torch.manual_seed(seed)

    print("=" * 50)
    print("Starting Training Process")
    print("=" * 50)

    # 1. Load intents data
    print(f"\n[1/6] Loading training data from {data_path}...")
    with open(data_path, "r", encoding="utf-8") as f:
        intents = json.load(f)

    tags = sorted(intent["tag"] for intent in intents["intents"])
    sentences, labels = [], []
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            sentences.append(pattern)
            labels.append(tags.index(intent["tag"]))
    print(f"   Found {len(sentences)} examples for {len(tags)} intents")

    # 2. Mask names so the model learns question shapes, not specific Pokemon
    print("[2/6] Masking names...")
    pokedex = Pokedex()
    masked = [pokedex.mask(s) for s in sentences]
    print(f"   e.g. \"{sentences[-1]}\" -> \"{masked[-1]}\"")

    # 3. Embed every sentence
    embedder = Embedder()
    print(f"[3/6] Embedding sentences with {embedder.model_name}...")
    X_train = torch.from_numpy(embedder.encode(masked))
    y_train = torch.tensor(labels, dtype=torch.long)

    # 4. Set up model, loss, and optimizer
    print("[4/6] Initializing model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_size = X_train.shape[1]
    model = IntentClassifier(input_size, hidden_size, len(tags)).to(device)

    # CrossEntropyLoss for classification; label smoothing keeps confidences honest
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    # AdamW = Adam with weight decay, which discourages large (memorizing) weights
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    print(f"   Model: {input_size} -> {hidden_size} -> {len(tags)} on {device}")

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=batch_size, shuffle=True)

    # 5. Training loop
    print(f"[5/6] Training for {num_epochs} epochs...")
    for epoch in range(num_epochs):
        model.train()
        for embeddings, targets in train_loader:
            embeddings, targets = embeddings.to(device), targets.to(device)

            # Forward pass
            loss = criterion(model(embeddings), targets)

            # Backward pass and optimization
            optimizer.zero_grad()  # Clear old gradients
            loss.backward()  # Calculate new gradients
            optimizer.step()  # Update weights

        if (epoch + 1) % max(1, num_epochs // 5) == 0:
            print(f"   Epoch [{epoch + 1}/{num_epochs}], Loss: {loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        train_acc = (model(X_train.to(device)).argmax(dim=1).cpu() == y_train).float().mean().item()
    print(f"   Training accuracy: {train_acc:.1%}")

    if EVAL_PATH.exists():
        examples = json.loads(EVAL_PATH.read_text(encoding="utf-8"))["examples"]
        report = evaluate(model, embedder, pokedex, tags, examples, device, config.CONFIDENCE_THRESHOLD)
        print(f"   Held-out accuracy: {report['accuracy']:.1%} on {len(examples)} questions")
        print(f"   Above the {config.CONFIDENCE_THRESHOLD:.0%} threshold: {report['coverage']:.1%} of questions, "
              f"{report['precision']:.1%} of those correct")
        for q, expected, got, conf in report["mistakes"]:
            print(f"     x \"{q}\": expected {expected}, got {got} ({conf:.0%})")

    # 6. Save the model
    print("[6/6] Saving model...")
    data = {
        "model_state": model.state_dict(),
        "input_size": input_size,
        "hidden_size": hidden_size,
        "output_size": len(tags),
        "tags": tags,
        "embedding_model": embedder.model_name,
    }
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(data, save_path)
    print(f"   Model saved to {save_path}")

    print("\n" + "=" * 50)
    print("Training Complete!")
    print("=" * 50)


if __name__ == "__main__":
    train_chatbot()
