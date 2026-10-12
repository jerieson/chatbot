# backend/chatbot_service.py - Orchestrates intent model, Pokedex answers, RAG, DB responses and LLM fallback

import logging
import time
import uuid
from typing import Dict, List, Optional

from chatbot import Chatbot
from chatbot.answers import AnswerBuilder
from chatbot.pokedex import Entities, Pokedex
from chatbot.retriever import Retriever
from shared import config
from shared.database import get_conversation_history, get_random_response, log_conversation
from backend.llm_fallback import LLMFallbackService

logger = logging.getLogger(__name__)

DEFAULT_RESPONSE = "I'm not sure I understand. Could you rephrase that?"
HISTORY_TURNS = 3
# Small talk gets the stored reply directly; no need to spend an LLM call on "hi"
STATIC_INTENTS = {"greeting", "goodbye", "thanks", "bot_help", "out_of_scope"}
# Intents whose answers live in the Markdown guides rather than the Pokedex data
GUIDE_INTENTS = {"team_build", "game_mechanics", "item_location", "region"}
# Without a guide intent, only show a guide passage when it matches very closely
STRONG_MATCH_SCORE = 0.72


class ChatService:
    def __init__(
        self,
        chatbot: Chatbot,
        llm_fallback: LLMFallbackService,
        pokedex: Pokedex,
        retriever: Optional[Retriever] = None,
    ):
        self.chatbot = chatbot
        self.llm_fallback = llm_fallback
        self.pokedex = pokedex
        self.retriever = retriever
        self.answers = AnswerBuilder(pokedex)

    async def get_response(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        use_fallback: bool = True,
    ) -> Dict:
        start = time.perf_counter()
        session_id = session_id or uuid.uuid4().hex

        intent, confidence = self.chatbot.predict(user_message)
        mentioned = self.pokedex.extract(user_message)
        entities = mentioned  # may gain context from earlier turns below
        confident = confidence >= config.CONFIDENCE_THRESHOLD
        history: Optional[List[Dict]] = None

        response, source = None, None
        fallback_reason = None if confident else (
            f"Low confidence: {confidence:.2%} < {config.CONFIDENCE_THRESHOLD:.2%}"
        )

        if confident and intent in STATIC_INTENTS:
            response = await self._db_response(intent)
            source = "database" if response else None

        if confident and not response:
            response = self.answers.answer(intent, user_message, entities)
            if not response:
                # Follow-ups like "how does it evolve?" refer to something from earlier turns
                history = await self._history(session_id)
                context = self._entities_from_history(history)
                if not context.is_empty():
                    entities = entities.merged_with(context)
                    response = self.answers.answer(intent, user_message, entities)
            if response:
                source = "pokedex"

        if not response and use_fallback and self.llm_fallback.enabled:
            if history is None:
                history = await self._history(session_id)
            response = await self.llm_fallback.get_response(
                user_message, history, intent if confident else None, self._reference(user_message, entities)
            )
            if response:
                source = "llm"
                fallback_reason = fallback_reason or f"No Pokédex answer for intent: {intent}"

        if not response and self.retriever:
            # No LLM (or it failed): answer from the best matching guide section, if it fits
            hits = self.retriever.search(user_message, k=1, kinds={"guide"})
            if hits:
                needed = config.RAG_MIN_SCORE if confident and intent in GUIDE_INTENTS else STRONG_MATCH_SCORE
                if hits[0].score >= needed:
                    response, source = hits[0].passage.text, "knowledge"

        if not response and confident:
            # Opinion questions ("Which starter is best?") still get the relevant data
            response = self.answers.answer(intent, user_message, entities, allow_open_ended=True)
            source = "pokedex" if response else None

        if not response:
            # Unsure what was asked, but it names a Pokemon/move/item/type: describe that
            response = self.answers.best_guess(mentioned)
            source = "pokedex" if response else None

        if not response and confident:
            # Static replies: clarifying questions ("Which Pokemon?") and general tips
            response = await self._db_response(intent)
            source = "database" if response else None

        if not response:
            response, source = DEFAULT_RESPONSE, "default"

        used_fallback = source == "llm"
        response_time_ms = int((time.perf_counter() - start) * 1000)

        try:
            await log_conversation(
                session_id=session_id,
                user_message=user_message,
                predicted_intent=intent,
                confidence=confidence,
                bot_response=response,
                response_time_ms=response_time_ms,
                used_fallback=used_fallback,
            )
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")

        return {
            "message": response,
            "intent": "llm_fallback" if used_fallback else intent,
            "confidence": confidence,
            "session_id": session_id,
            "source": source,
            "used_fallback": used_fallback,
            "fallback_reason": fallback_reason,
        }

    def _reference(self, user_message: str, entities: Entities) -> str:
        """Grounding for the LLM: Pokedex facts about mentioned names plus retrieved passages."""
        parts = [self.answers.facts(entities)]
        if self.retriever:
            for hit in self.retriever.search(user_message, k=4, min_score=config.RAG_MIN_SCORE - 0.05):
                parts.append(f"{hit.passage.title}: {hit.passage.text}")
        return "\n\n".join(p for p in parts if p)

    async def _history(self, session_id: str) -> List[Dict]:
        try:
            return await get_conversation_history(session_id, limit=HISTORY_TURNS)
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    def _entities_from_history(self, history: List[Dict]) -> Entities:
        """Entities from the most recent earlier message that mentioned any (history is newest first)."""
        for turn in history:
            found = self.pokedex.extract(turn["user_message"])
            if not found.is_empty():
                return found
        return Entities()

    async def _db_response(self, intent: str) -> Optional[str]:
        try:
            return await get_random_response(intent)
        except Exception as e:
            logger.error(f"Failed to load response for {intent}: {e}")
            return None
