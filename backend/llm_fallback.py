# backend/llm_fallback.py - LLM fallback for messages the Pokedex can't answer directly

import logging
from typing import Dict, List, Optional

import httpx

from shared import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are EY-AY, a friendly and knowledgeable Pokemon assistant.

Answer questions about Pokemon: types, weaknesses, evolutions, moves, items, regions,
legendaries, team building and game mechanics.

Guidelines:
1. Be concise - a few sentences unless the user asks for detail.
2. When reference data is provided, treat it as correct and prefer it over your own memory.
3. If you are not sure about a fact, say so rather than guessing.
4. If a question is not about Pokemon, politely steer the conversation back to Pokemon.
5. Light Markdown is fine (bold, short bullet lists); no headings or tables."""

PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": config.GROQ_API_KEY,
        "model": config.GROQ_MODEL,
        "headers": {},
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key": config.OPENROUTER_API_KEY,
        "model": config.OPENROUTER_MODEL,
        "headers": {"X-Title": "EY-AY Chatbot"},
    },
}


class LLMFallbackService:
    """Queries OpenAI-compatible chat APIs in priority order: Groq, then OpenRouter."""

    def __init__(self):
        self.providers = [name for name, p in PROVIDERS.items() if p["api_key"]]
        if self.providers:
            logger.info(f"LLM fallback providers: {', '.join(self.providers)}")
        else:
            logger.warning("No LLM API keys configured; LLM fallback disabled")

    @property
    def enabled(self) -> bool:
        return bool(self.providers)

    def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]],
        original_intent: Optional[str],
        reference: str,
    ) -> List[Dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # History rows arrive newest first; replay the last 3 exchanges in order
        for conv in reversed((conversation_history or [])[:3]):
            messages.append({"role": "user", "content": conv["user_message"]})
            messages.append({"role": "assistant", "content": conv["bot_response"]})

        content = user_message
        if reference:
            content = f"Reference data from the Pokedex:\n{reference}\n\nQuestion: {user_message}"
        if original_intent:
            content += f"\n[Context: the intent classifier guessed '{original_intent}']"
        messages.append({"role": "user", "content": content})
        return messages

    async def get_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        original_intent: Optional[str] = None,
        reference: str = "",
    ) -> Optional[str]:
        """Return an LLM-generated reply, or None if every provider fails"""
        messages = self._build_messages(user_message, conversation_history, original_intent, reference)

        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT_SECONDS) as client:
            for name in self.providers:
                reply = await self._query(client, name, messages)
                if reply:
                    return reply

        if self.providers:
            logger.error("All LLM providers failed")
        return None

    async def _query(self, client: httpx.AsyncClient, name: str, messages: List[Dict]) -> Optional[str]:
        provider = PROVIDERS[name]
        try:
            resp = await client.post(
                provider["url"],
                headers={"Authorization": f"Bearer {provider['api_key']}", **provider["headers"]},
                json={
                    "model": provider["model"],
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 1024,  # reasoning models (gpt-oss) spend part of this thinking
                },
            )
            if resp.status_code != 200:
                logger.error(f"{name} API error {resp.status_code}: {resp.text[:500]}")
                return None
            reply = resp.json()["choices"][0]["message"]["content"]
            logger.info(f"{name} response received ({len(reply)} chars)")
            return reply.strip() or None
        except Exception as e:
            logger.error(f"{name} query failed: {e}")
            return None
