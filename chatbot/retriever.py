# chatbot/retriever.py - Semantic search over guides and Pokedex data (the "R" in RAG)

"""
Retrieval-Augmented Generation (RAG)

1. Split knowledge into short passages (guide sections, one passage per Pokemon/move/item)
2. Embed every passage once and save the vectors (the "index")
3. For a question, embed it and find the passages with the most similar vectors
4. Give those passages to the LLM as reference material, or show the best guide
   passage directly when no LLM is configured

With a few thousand passages, a numpy dot product is fast enough; no vector database needed.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

from shared import config
from .embedder import Embedder
from .pokedex import Pokedex

logger = logging.getLogger(__name__)

# bge models retrieve better when queries (not passages) carry this instruction
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@dataclass
class Passage:
    id: str
    kind: str  # guide | pokemon | move | item
    title: str
    text: str


@dataclass
class SearchResult:
    passage: Passage
    score: float  # cosine similarity, roughly 0.3 (unrelated) to 0.9 (near-identical)


def load_guides(directory: Path) -> List[Passage]:
    """Each "## Heading" section of the Markdown guides becomes one passage."""
    passages = []
    for path in sorted(directory.glob("*.md")):
        for section in re.split(r"^## ", path.read_text(encoding="utf-8"), flags=re.MULTILINE)[1:]:
            title, _, body = section.partition("\n")
            passages.append(Passage(
                id=f"guide:{path.stem}:{title.strip()}", kind="guide",
                title=title.strip(), text=" ".join(body.split()),
            ))
    return passages


def pokedex_passages(dex: Pokedex) -> List[Passage]:
    passages = []
    for slug, p in dex.pokemon.items():
        types = "/".join(t.title() for t in p["types"])
        status = [label for flag, label in ((p["legendary"], "Legendary"), (p["mythical"], "Mythical"),
                                            (dex.is_pseudo_legendary(slug), "pseudo-legendary")) if flag]
        text = (f"{p['name']} is the {p['genus']}, a {types}-type Pokémon from Generation {p['generation']}"
                f"{' (' + ', '.join(status) + ')' if status else ''}. {p['flavor_text']}")
        passages.append(Passage(f"pokemon:{slug}", "pokemon", p["name"], text))
    for slug, m in dex.moves.items():
        text = (f"{m['name']} is a {m['type'].title()}-type {m['damage_class']} move with "
                f"{m['power'] or 'no'} power. {m['effect']}")
        passages.append(Passage(f"move:{slug}", "move", m["name"], text))
    for slug, item in dex.items.items():
        if item["effect"] and item["category"] != "all machines":  # skip TMs: one per move already
            passages.append(Passage(f"item:{slug}", "item", item["name"],
                                    f"{item['name']} ({item['category']}): {item['effect']}"))
    return passages


class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        pokedex: Pokedex,
        guides_dir: Optional[Path] = None,
        index_path: Optional[Path] = None,
    ):
        self.embedder = embedder
        self.passages = load_guides(guides_dir or config.KNOWLEDGE_DIR) + pokedex_passages(pokedex)
        self.index_path = Path(index_path or config.RAG_INDEX_PATH)
        self.vectors = self._load_or_build()

    def _fingerprint(self) -> str:
        """Changes whenever the passages or the embedding model change, so the index is rebuilt."""
        digest = hashlib.sha256(self.embedder.model_name.encode())
        for p in self.passages:
            digest.update(f"{p.id}\0{p.text}\0".encode())
        return digest.hexdigest()

    def _load_or_build(self) -> np.ndarray:
        fingerprint = self._fingerprint()
        meta_path = self.index_path.with_suffix(".json")
        if self.index_path.exists() and meta_path.exists():
            if json.loads(meta_path.read_text())["fingerprint"] == fingerprint:
                return np.load(self.index_path)
        logger.info(f"Building RAG index for {len(self.passages)} passages (one-time, takes a minute)...")
        vectors = self.embedder.encode([f"{p.title}. {p.text}" for p in self.passages])
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(self.index_path, vectors)
        meta_path.write_text(json.dumps({"fingerprint": fingerprint, "passages": len(self.passages)}))
        logger.info(f"RAG index saved to {self.index_path}")
        return vectors

    def search(self, query: str, k: int = 4, kinds: Optional[set] = None,
               min_score: float = 0.0) -> List[SearchResult]:
        query_vector = self.embedder.encode([QUERY_PREFIX + query])[0]
        scores = self.vectors @ query_vector
        results = []
        for i in np.argsort(-scores):
            if scores[i] < min_score or len(results) == k:
                break
            if kinds is None or self.passages[i].kind in kinds:
                results.append(SearchResult(self.passages[i], float(scores[i])))
        return results
