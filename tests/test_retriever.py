import pytest

from chatbot.embedder import Embedder
from chatbot.pokedex import Pokedex
from chatbot.retriever import Retriever, load_guides
from shared import config


@pytest.fixture(scope="module")
def retriever():
    # Uses the cached index in data/ (built on first run, rebuilt when sources change)
    return Retriever(Embedder(), Pokedex())


def test_guides_split_into_sections():
    passages = load_guides(config.KNOWLEDGE_DIR)
    titles = {p.title for p in passages}
    assert {"EVs (Effort Values)", "Nuzlocke challenge", "Kanto"} <= titles
    assert all(p.kind == "guide" and p.text for p in passages)


@pytest.mark.parametrize("question, title", [
    ("how do EVs work?", "EVs (Effort Values)"),
    ("what does same type attack bonus mean", "STAB (Same Type Attack Bonus)"),
    ("what's a good team for a nuzlocke?", "Nuzlocke challenge"),
    ("who is the champion in sinnoh", "Sinnoh"),
])
def test_search_finds_the_right_guide(retriever, question, title):
    best = retriever.search(question, k=1, kinds={"guide"})[0]
    assert best.passage.title == title
    assert best.score >= config.RAG_MIN_SCORE


def test_search_covers_pokedex_passages(retriever):
    titles = [r.passage.title for r in retriever.search("pokemon that stores electricity in its cheeks", k=3)]
    assert "Pikachu" in titles


def test_unrelated_questions_score_low(retriever):
    assert retriever.search("what's the capital of Japan?", k=1)[0].score < config.RAG_MIN_SCORE
