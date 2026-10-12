# shared/config.py - Settings loaded from the project-root .env

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "chatbot_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "chatbot_db")

# Model
MODEL_PATH = PROJECT_ROOT / os.getenv("MODEL_PATH", "chatbot/data/processed/chatbot_model.pth")
INTENTS_PATH = PROJECT_ROOT / os.getenv("INTENTS_PATH", "chatbot/data/intents.json")
POKEDEX_PATH = PROJECT_ROOT / os.getenv("POKEDEX_PATH", "chatbot/data/pokedex.json")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.5))

# Embeddings (local sentence-transformers model, downloaded once from Hugging Face)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# RAG: guides to search, where the (generated) vector index is cached, and the minimum
# similarity for showing a guide passage as the answer when no LLM is configured
KNOWLEDGE_DIR = PROJECT_ROOT / os.getenv("KNOWLEDGE_DIR", "chatbot/data/knowledge")
RAG_INDEX_PATH = PROJECT_ROOT / os.getenv("RAG_INDEX_PATH", "data/rag_index.npy")
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", 0.6))

# Training
HIDDEN_SIZE = int(os.getenv("HIDDEN_SIZE", 64))
NUM_EPOCHS = int(os.getenv("NUM_EPOCHS", 150))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 16))
LEARNING_RATE = float(os.getenv("LEARNING_RATE", 0.003))

# LLM fallback (each provider is skipped when its key is unset)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", 30))

# API
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
