import pytest

from backend import chatbot_service
from backend.chatbot_service import DEFAULT_RESPONSE, ChatService
from chatbot.pokedex import Pokedex
from chatbot.retriever import Passage, SearchResult


class FakeChatbot:
    def __init__(self, intent, confidence):
        self.result = (intent, confidence)

    def predict(self, message):
        return self.result


class FakeLLM:
    def __init__(self, reply="llm reply", enabled=True):
        self.reply = reply
        self.enabled = enabled
        self.calls = []

    async def get_response(self, message, history, intent, reference=""):
        self.calls.append({"message": message, "history": history, "intent": intent, "reference": reference})
        return self.reply


@pytest.fixture(scope="module")
def pokedex():
    return Pokedex()


@pytest.fixture
def db(monkeypatch):
    """Replace the DB helpers used by the service with in-memory fakes."""
    state = {"responses": {"team_build": "Cover your weaknesses.", "pokemon_type": "Which Pokémon?"},
             "logged": []}

    async def get_random_response(tag):
        return state["responses"].get(tag)

    async def log_conversation(**kwargs):
        state["logged"].append(kwargs)

    async def get_conversation_history(session_id, limit=10):
        return [r for r in state["logged"] if r["session_id"] == session_id][::-1][:limit]

    monkeypatch.setattr(chatbot_service, "get_random_response", get_random_response)
    monkeypatch.setattr(chatbot_service, "log_conversation", log_conversation)
    monkeypatch.setattr(chatbot_service, "get_conversation_history", get_conversation_history)
    return state


class FakeRetriever:
    """Returns one guide passage with a fixed similarity score."""

    def __init__(self, score, title="EVs (Effort Values)", text="EVs are points earned in battle."):
        self.hit = SearchResult(Passage(f"guide:test:{title}", "guide", title, text), score)

    def search(self, query, k=4, kinds=None, min_score=0.0):
        return [self.hit] if self.hit.score >= min_score else []


def make_service(pokedex, intent, confidence, llm=None, retriever=None):
    return ChatService(FakeChatbot(intent, confidence), llm or FakeLLM(enabled=False), pokedex, retriever)


async def test_confident_prediction_answers_from_pokedex(db, pokedex):
    llm = FakeLLM()
    service = make_service(pokedex, "pokemon_type", 0.95, llm)

    result = await service.get_response("What type is Pikachu?", session_id="s1")

    assert result["message"] == "Pikachu is an Electric-type Pokémon."
    assert result["source"] == "pokedex"
    assert result["used_fallback"] is False
    assert llm.calls == []
    assert db["logged"][0]["session_id"] == "s1"


async def test_follow_up_uses_entities_from_history(db, pokedex):
    service = make_service(pokedex, "pokemon_type", 0.95)
    await service.get_response("Tell me about Charmander", session_id="s1")

    service.chatbot = FakeChatbot("evolution", 0.95)
    result = await service.get_response("How does it evolve?", session_id="s1")

    assert "Charmeleon (at level 16)" in result["message"]
    assert result["source"] == "pokedex"


async def test_low_confidence_uses_llm_with_pokedex_facts(db, pokedex):
    llm = FakeLLM("Pikachu is great.")
    service = make_service(pokedex, "pokemon_type", 0.30, llm)

    result = await service.get_response("is pikachu good in competitive?", session_id="s1")

    assert result["message"] == "Pikachu is great."
    assert result["source"] == "llm"
    assert result["intent"] == "llm_fallback"
    assert result["fallback_reason"].startswith("Low confidence")
    assert llm.calls[0]["intent"] is None
    assert "Mouse Pokémon" in llm.calls[0]["reference"]
    assert db["logged"][0]["used_fallback"] is True


async def test_open_ended_intent_goes_to_llm_before_static_response(db, pokedex):
    llm = FakeLLM("Use a balanced team.")
    service = make_service(pokedex, "team_build", 0.95, llm)

    result = await service.get_response("How do I build a team?", session_id="s1")

    assert result["source"] == "llm"
    assert llm.calls[0]["intent"] == "team_build"


async def test_static_response_when_llm_disabled(db, pokedex):
    service = make_service(pokedex, "team_build", 0.95)

    result = await service.get_response("How do I build a team?", session_id="s1")

    assert result["message"] == "Cover your weaknesses."
    assert result["source"] == "database"


async def test_missing_entity_gets_clarifying_question(db, pokedex):
    service = make_service(pokedex, "pokemon_type", 0.95)

    result = await service.get_response("What type is it?", session_id="new")

    assert result["message"] == "Which Pokémon?"
    assert result["source"] == "database"


async def test_unknown_question_about_known_pokemon_shows_profile(db, pokedex):
    service = make_service(pokedex, "team_build", 0.20)

    result = await service.get_response("snorlax??", session_id="s1")

    assert result["message"].startswith("Snorlax, the Sleeping Pokémon")
    assert result["source"] == "pokedex"


async def test_default_response_when_nothing_matches(db, pokedex):
    service = make_service(pokedex, "team_build", 0.20)

    result = await service.get_response("asdf qwerty", session_id="s1", use_fallback=False)

    assert result["message"] == DEFAULT_RESPONSE
    assert result["source"] == "default"


async def test_sessions_are_independent(db, pokedex):
    service = make_service(pokedex, "pokemon_type", 0.95)

    a = await service.get_response("What type is Pikachu?", session_id=None)
    b = await service.get_response("What type is Pikachu?", session_id=None)
    again = await service.get_response("What type is Pikachu?", session_id=a["session_id"])

    assert a["session_id"] != b["session_id"]
    assert again["session_id"] == a["session_id"]


async def test_llm_receives_only_this_sessions_history(db, pokedex):
    llm = FakeLLM()
    service = make_service(pokedex, "pokemon_type", 0.95, llm)
    await service.get_response("What type is Pikachu?", session_id="s1")
    await service.get_response("What type is Eevee?", session_id="s2")

    service.chatbot = FakeChatbot("team_build", 0.10)
    await service.get_response("any tips?", session_id="s1")

    assert [h["user_message"] for h in llm.calls[0]["history"]] == ["What type is Pikachu?"]


async def test_small_talk_uses_stored_reply_without_llm(db, pokedex):
    db["responses"]["greeting"] = "Hello, Trainer!"
    llm = FakeLLM()
    service = make_service(pokedex, "greeting", 0.95, llm)

    result = await service.get_response("hey there", session_id="s1")

    assert result["message"] == "Hello, Trainer!"
    assert result["source"] == "database"
    assert llm.calls == []


async def test_best_guess_ignores_entities_from_earlier_turns(db, pokedex):
    service = make_service(pokedex, "item_info", 0.95)
    await service.get_response("What does a Rare Candy do?", session_id="s1")

    service.chatbot = FakeChatbot("team_build", 0.95)
    result = await service.get_response("best team for beginners?", session_id="s1")

    assert result["message"] == "Cover your weaknesses."
    assert result["source"] == "database"


async def test_guide_intent_answers_from_knowledge_without_llm(db, pokedex):
    service = make_service(pokedex, "game_mechanics", 0.95, retriever=FakeRetriever(0.65))

    result = await service.get_response("how do EVs work?", session_id="s1")

    assert result["message"] == "EVs are points earned in battle."
    assert result["source"] == "knowledge"


async def test_weak_guide_match_is_not_shown_for_other_intents(db, pokedex):
    service = make_service(pokedex, "pokemon_type", 0.95, retriever=FakeRetriever(0.65))

    result = await service.get_response("What type is it?", session_id="new")

    assert result["source"] == "database"  # the clarifying question, not an unrelated guide


async def test_llm_reference_includes_retrieved_passages(db, pokedex):
    llm = FakeLLM()
    service = make_service(pokedex, "game_mechanics", 0.95, llm, FakeRetriever(0.8))

    await service.get_response("how do EVs work for Pikachu?", session_id="s1")

    reference = llm.calls[0]["reference"]
    assert "EVs (Effort Values): EVs are points earned in battle." in reference
    assert "Mouse Pokémon" in reference


async def test_opinion_question_goes_to_llm_when_available(db, pokedex):
    llm = FakeLLM("Piplup is a great pick.")
    service = make_service(pokedex, "starter", 0.95, llm)

    result = await service.get_response("Which starter is best in Sinnoh?", session_id="s1")

    assert result["source"] == "llm"
    assert "Turtwig" in llm.calls[0]["reference"]  # region facts ground the opinion


async def test_opinion_question_gets_data_without_llm(db, pokedex):
    service = make_service(pokedex, "starter", 0.95)

    result = await service.get_response("Which starter is best in Sinnoh?", session_id="s1")

    assert result["source"] == "pokedex"
    assert "Turtwig (Grass), Chimchar (Fire) and Piplup (Water)" in result["message"]
