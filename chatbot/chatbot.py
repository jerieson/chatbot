# chatbot/chatbot.py - Intent prediction with the trained PyTorch model

import logging
from pathlib import Path
from typing import Optional, Tuple, Union

import torch

from shared import config
from .embedder import Embedder
from .intent_classifier import IntentClassifier
from .pokedex import Pokedex

logger = logging.getLogger(__name__)


class Chatbot:
    """Predicts intents: mask names -> sentence embedding -> classifier.

    Holds no per-user state, so one instance can be shared across all requests.
    """

    def __init__(
        self,
        model_path: Union[str, Path, None] = None,
        pokedex: Optional[Pokedex] = None,
        embedder: Optional[Embedder] = None,
    ):
        model_path = Path(model_path or config.MODEL_PATH)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}. Run: python chatbot/train.py")

        data = torch.load(model_path, map_location=self.device)
        self.tags = data["tags"]
        self.pokedex = pokedex or Pokedex()
        self.embedder = embedder or Embedder(data["embedding_model"])
        if self.embedder.model_name != data["embedding_model"]:
            raise ValueError(
                f"Model was trained with {data['embedding_model']} but the embedder uses "
                f"{self.embedder.model_name}. Retrain with: python chatbot/train.py"
            )

        self.model = IntentClassifier(
            data["input_size"],
            data["hidden_size"],
            len(self.tags)
        ).to(self.device)
        self.model.load_state_dict(data["model_state"])
        self.model.eval()

        logger.info(f"Model loaded: {len(self.tags)} intents, embeddings from {data['embedding_model']}")

    @torch.no_grad()
    def predict(self, user_input: str) -> Tuple[str, float]:
        """Return (intent tag, confidence) for a message"""
        X = torch.from_numpy(self.embedder.encode([self.pokedex.mask(user_input)])).to(self.device)

        probs = torch.softmax(self.model(X), dim=1)
        confidence, predicted = torch.max(probs, dim=1)

        return self.tags[predicted.item()], confidence.item()


# Standalone CLI for testing predictions (no database needed)
if __name__ == "__main__":
    bot = Chatbot()
    for q in ["What type is Pikachu?", "How does Charmander evolve?", "Is Mewtwo legendary?", "hello there"]:
        intent, confidence = bot.predict(q)
        print(f"Q: {q}\n  Intent: {intent} ({confidence:.2%})\n")
