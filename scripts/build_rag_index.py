# scripts/build_rag_index.py - Build (or refresh) the RAG vector index ahead of time
#
# Usage (from project root):  python scripts/build_rag_index.py
#
# The backend also builds the index on startup when it is missing or out of date
# (after editing chatbot/data/knowledge/*.md or re-importing the Pokedex); running
# this first just avoids that one-time delay.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chatbot.embedder import Embedder  # noqa: E402
from chatbot.pokedex import Pokedex  # noqa: E402
from chatbot.retriever import Retriever  # noqa: E402

if __name__ == "__main__":
    retriever = Retriever(Embedder(), Pokedex())
    kinds = {}
    for p in retriever.passages:
        kinds[p.kind] = kinds.get(p.kind, 0) + 1
    print(f"Index ready at {retriever.index_path}: " + ", ".join(f"{n} {k}" for k, n in kinds.items()))
