# app/startup.py - Fixed version

import logging
import asyncio
from typing import Optional

from app.settings import APP_SETTINGS
from app.embeddings.gemini_embedding import GeminiEmbeddingsModel
from app.llm_loader.gemini_llm import GeminiLLM
from app.vector_db.qdrant_vectordb import QdrantVectorDatabase
from app.core.state import (
    app_state,
    set_service,
    mark_as_initialized,
    increment_init_attempts,
)

logger = logging.getLogger(__name__)


def create_gemini_embedding_model() -> Optional[GeminiEmbeddingsModel]:
    """Create Gemini embedding model with proper error handling"""
    try:
        # 1. Check if API key exists
        api_key = APP_SETTINGS.GEMINI_API_KEY
        if not api_key:
            logger.error("❌ GEMINI_API_KEY not found in settings!")
            logger.error(f"Available settings: {dir(APP_SETTINGS)}")
            return None

        logger.info(f"🔑 Found API key: {api_key[:10]}...")

        # 2. Create embedding model
        embed_model = GeminiEmbeddingsModel(
            api_key=api_key, model_name="models/embedding-001"
        )
        logger.info("✅ Gemini embedding model created successfully")
        return embed_model

    except Exception as e:
        logger.error(f"❌ Failed to create Gemini embedding model: {e}")
        return None


def create_gemini_llm() -> Optional[GeminiLLM]:
    """Create Gemini LLM with proper error handling"""
    try:
        api_key = APP_SETTINGS.GEMINI_API_KEY
        if not api_key:
            logger.error("❌ GEMINI_API_KEY not found for LLM!")
            return None

        llm = GeminiLLM(api_key=api_key, model_name="gemini-1.5-flash")
        logger.info("✅ Gemini LLM created successfully")
        return llm

    except Exception as e:
        logger.error(f"❌ Failed to create Gemini LLM: {e}")
        return None


def create_vector_database(
    embed_model: GeminiEmbeddingsModel,
) -> Optional[QdrantVectorDatabase]:
    """Create vector database with embedding model"""
    try:
        vector_db = QdrantVectorDatabase(
            embed_model=embed_model,
            collection_name="dat_614943",
            documents=[],  # Pass empty list or your actual documents
            vector_size=768,  # Optional: adjust if needed
            distance_metric="COSINE",  # Optional: adjust if needed
            timeout=10,  # Optional: adjust if needed
        )
        logger.info("✅ Vector database created successfully")
        return vector_db

    except Exception as e:
        logger.error(f"❌ Failed to create vector database: {e}")
        return None


def initialize_app_services_sync() -> bool:
    """Synchronous initialization of all app services"""
    try:
        # Increment attempt counter
        increment_init_attempts()
        attempt_num = app_state.get("init_attempts", 1)

        logger.info("🔧 Starting app services initialization...")
        logger.info(f"🔄 Initialization attempt #{attempt_num}")

        # Debug: Check settings
        logger.info(f"🔍 Checking APP_SETTINGS:")
        logger.info(
            f"  - GEMINI_API_KEY exists: {hasattr(APP_SETTINGS, 'GEMINI_API_KEY')}"
        )
        if hasattr(APP_SETTINGS, "GEMINI_API_KEY"):
            api_key = getattr(APP_SETTINGS, "GEMINI_API_KEY", None)
            logger.info(f"  - API key value: {api_key[:10] if api_key else 'None'}...")

        # 1. Create embedding model first
        logger.info("🤖 Initializing Gemini Embedding Model...")
        embed_model = create_gemini_embedding_model()
        if not embed_model:
            logger.error("❌ Failed to create embedding model")
            return False

        # 2. Create LLM
        logger.info("🧠 Initializing Gemini LLM...")
        llm = create_gemini_llm()
        if not llm:
            logger.error("❌ Failed to create LLM")
            return False

        # 3. Create vector database
        logger.info("🗂️ Initializing Vector Database...")
        vector_db = create_vector_database(embed_model)
        if not vector_db:
            logger.error("❌ Failed to create vector database")
            return False

        # 4. Store in app state
        set_service("embed_model", embed_model)
        set_service("llm", llm)
        set_service("vector_db", vector_db)
        set_service("metadata", {"initialized_at": "startup"})

        mark_as_initialized()

        logger.info("✅ All services initialized successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        return False


async def initialize_app_services_async() -> bool:
    """Async wrapper for initialization"""
    try:
        logger.info("🔄 Starting async initialization...")
        return await asyncio.to_thread(initialize_app_services_sync)
    except Exception as e:
        logger.error(f"❌ Async initialization failed: {e}")
        return False
