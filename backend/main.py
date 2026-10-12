# backend/main.py - FastAPI backend

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.chatbot_service import ChatService
from backend.dex_api import create_router
from backend.llm_fallback import LLMFallbackService
from backend.models import ChatRequest, ChatResponse
from chatbot import Chatbot
from chatbot.embedder import Embedder
from chatbot.pokedex import Pokedex
from chatbot.retriever import Retriever
from shared import config
from shared.database import Database, get_conversation_history, get_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Initialize services
pokedex = Pokedex()  # shared by the chatbot and the Pokedex browser
try:
    embedder = Embedder()  # shared by the intent classifier and RAG search
    chat_service = ChatService(
        Chatbot(pokedex=pokedex, embedder=embedder),
        LLMFallbackService(),
        pokedex,
        Retriever(embedder, pokedex),
    )
except Exception:
    logger.exception("Failed to initialize chatbot")
    chat_service = None


# Database lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    await Database.init()
    yield
    await Database.close()


app = FastAPI(
    title="EY-AY Chatbot API",
    description="PyTorch-powered chatbot with LLM fallback",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(create_router(pokedex))

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes
@app.get("/")
async def root():
    return {
        "message": "EY-AY Chatbot API",
        "status": "online",
        "version": "2.0.0",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "chatbot_ready": chat_service is not None,
        "llm_fallback_ready": chat_service is not None and chat_service.llm_fallback.enabled,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if chat_service is None:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")

    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = await chat_service.get_response(message, request.session_id, request.use_fallback)
    except Exception:
        logger.exception("Error processing chat message")
        raise HTTPException(status_code=500, detail="Internal error while processing the message")

    return ChatResponse(timestamp=datetime.now().isoformat(), **result)


@app.get("/history/{session_id}")
async def history(session_id: str, limit: int = Query(10, ge=1, le=100)):
    return {"history": await get_conversation_history(session_id, limit)}


@app.get("/stats")
async def stats():
    return await get_stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
