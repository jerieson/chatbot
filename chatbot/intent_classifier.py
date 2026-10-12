# chatbot/intent_classifier.py

"""
Intent Classifier Neural Network

A small feedforward neural network (Multi-Layer Perceptron) on top of sentence embeddings.

Architecture:
Sentence embedding (384 numbers) -> Hidden Layer -> Output Layer (one score per intent)

The embedding model already understands language; this network only has to learn which
region of "meaning space" belongs to which intent, so it trains in seconds.

Key Concepts:
1. Linear layers: perform matrix multiplication (y = Wx + b)
2. ReLU activation: adds non-linearity (helps learn complex patterns)
3. Dropout: randomly zeroes neurons during training so the network can't memorize
4. Forward pass: data flows through the network
"""

import torch
import torch.nn as nn


class IntentClassifier(nn.Module):
    """
    Args:
        input_size: size of the sentence embedding
        hidden_size: number of neurons in the hidden layer
        num_classes: number of intents to classify
    """

    def __init__(self, input_size, hidden_size, num_classes):
        super(IntentClassifier, self).__init__()

        self.l1 = nn.Linear(input_size, hidden_size)
        self.l2 = nn.Linear(hidden_size, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)

    def forward(self, x):
        out = self.dropout(x)
        out = self.l1(out)
        out = self.relu(out)
        out = self.dropout(out)
        return self.l2(out)


if __name__ == "__main__":
    # Test the model
    print("=== Testing Neural Network ===\n")

    embedding_size = 384  # bge-small embedding size
    hidden_size = 64
    num_intents = 25

    model = IntentClassifier(embedding_size, hidden_size, num_intents)
    print(f"Model architecture:\n{model}\n")

    dummy_input = torch.randn(1, embedding_size)  # batch_size=1
    output = model(dummy_input)
    print(f"Input shape: {dummy_input.shape}")
    print(f"Output shape: {output.shape}")

    _, predicted = torch.max(output, dim=1)
    print(f"Predicted intent: {predicted.item()}")

    total_params = sum(p.numel() for p in model.parameters())
    print(f"\nTotal parameters: {total_params}")
