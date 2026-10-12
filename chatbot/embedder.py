# chatbot/embedder.py - Sentence embeddings with a small local model (free, runs on CPU)

"""
Sentence Embeddings

An embedding model turns a sentence into a vector of numbers (384 for bge-small) so that
sentences with similar meaning get similar vectors:
- "what is Fire weak to?" and "what beats fire types?" end up close together
- "what is Fire weak to?" and "tell me a joke" end up far apart

That is what makes the intent classifier understand paraphrases it never saw in training,
and it powers the semantic search used for RAG.

The model (~130 MB) downloads from Hugging Face on first use and is cached locally.
"""

from typing import List, Optional

import numpy as np

from shared import config


class Embedder:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or config.EMBEDDING_MODEL
        self._model = None

    @property
    def model(self):
        # Imported lazily: loading the library and weights takes a few seconds
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def encode(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        """Unit-length float32 vectors, so a dot product is the cosine similarity."""
        return self.model.encode(
            texts, batch_size=batch_size, normalize_embeddings=True, convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(np.float32)
