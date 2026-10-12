import pytest

from chatbot import Chatbot


@pytest.fixture(scope="module")
def bot():
    return Chatbot()


@pytest.mark.parametrize("question, intent", [
    ("What type is Garchomp?", "pokemon_type"),
    ("How does Eevee evolve?", "evolution"),
    ("Compare Lucario and Garchomp", "compare"),
    ("hello there", "greeting"),
    ("what's the weather like today?", "out_of_scope"),
])
def test_trained_model_predicts_intents(bot, question, intent):
    predicted, confidence = bot.predict(question)
    assert predicted == intent
    assert 0.0 <= confidence <= 1.0
