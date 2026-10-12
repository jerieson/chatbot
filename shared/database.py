# shared/database.py - Async MySQL using aiomysql

import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Dict

import aiomysql

from shared import config

logger = logging.getLogger(__name__)


class Database:
    _pool: Optional[aiomysql.Pool] = None

    @classmethod
    async def init(cls):
        """Initialize connection pool"""
        if cls._pool is None:
            cls._pool = await aiomysql.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                db=config.DB_NAME,
                charset="utf8mb4",
                autocommit=True,
                minsize=1,
                maxsize=5,
            )
            logger.info("Database pool initialized")

    @classmethod
    async def close(cls):
        """Close connection pool"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("Database pool closed")

    @classmethod
    @asynccontextmanager
    async def get_connection(cls):
        """Get connection from pool"""
        if cls._pool is None:
            await cls.init()
        async with cls._pool.acquire() as conn:
            yield conn

    @classmethod
    async def fetch_one(cls, query: str, args: tuple = None) -> Optional[Dict]:
        """Fetch one row"""
        async with cls.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, args or ())
                return await cursor.fetchone()

    @classmethod
    async def fetch_all(cls, query: str, args: tuple = None) -> List[Dict]:
        """Fetch all rows"""
        async with cls.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, args or ())
                return await cursor.fetchall()

    @classmethod
    async def execute(cls, query: str, args: tuple = None):
        """Execute a query"""
        async with cls.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, args or ())
                return cursor


async def log_conversation(
    session_id: str,
    user_message: str,
    predicted_intent: str,
    confidence: float,
    bot_response: str,
    response_time_ms: int = 0,
    used_fallback: bool = False,
) -> int:
    """Log a conversation to the database"""
    query = """
        INSERT INTO conversations
        (session_id, user_message, predicted_intent, confidence, bot_response,
         response_time_ms, used_fallback)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor = await Database.execute(query, (
        session_id, user_message, predicted_intent, confidence, bot_response,
        response_time_ms, used_fallback,
    ))
    return cursor.lastrowid


async def get_random_response(intent_tag: str) -> Optional[str]:
    """Get a random response for an intent"""
    query = """
        SELECT r.text
        FROM responses r
        JOIN intents i ON r.intent_id = i.id
        WHERE i.tag = %s
        ORDER BY RAND()
        LIMIT 1
    """
    result = await Database.fetch_one(query, (intent_tag,))
    return result["text"] if result else None


async def get_conversation_history(session_id: str, limit: int = 10) -> List[Dict]:
    """Get conversation history for a session, newest first"""
    query = """
        SELECT * FROM conversations
        WHERE session_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT %s
    """
    return await Database.fetch_all(query, (session_id, limit))


async def get_stats() -> Dict:
    """Aggregate conversation statistics"""
    totals = await Database.fetch_one(
        """
        SELECT COUNT(*) AS total_conversations,
               COUNT(DISTINCT session_id) AS total_sessions,
               AVG(confidence) AS avg_confidence,
               AVG(response_time_ms) AS avg_response_time_ms,
               SUM(used_fallback) AS fallback_count
        FROM conversations
        """
    )
    top_intents = await Database.fetch_all(
        """
        SELECT predicted_intent AS intent, COUNT(*) AS count
        FROM conversations
        GROUP BY predicted_intent
        ORDER BY count DESC
        LIMIT 10
        """
    )
    return {
        "total_conversations": int(totals["total_conversations"] or 0),
        "total_sessions": int(totals["total_sessions"] or 0),
        "avg_confidence": float(totals["avg_confidence"] or 0),
        "avg_response_time_ms": float(totals["avg_response_time_ms"] or 0),
        "fallback_count": int(totals["fallback_count"] or 0),
        "top_intents": top_intents,
    }
