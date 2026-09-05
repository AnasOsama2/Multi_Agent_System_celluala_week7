import os
from fastapi import APIRouter
from app.config import settings
from app.database.registry import registry
from app.database.vector_store import vector_store

router = APIRouter(prefix="/api/v1", tags=["Health & Status"])

@router.get("/health")
async def health_check():
    # Check SQLite
    db_ok = False
    source_count = 0
    try:
        sources = registry.get_all_sources()
        source_count = len(sources)
        db_ok = True
    except Exception:
        pass

    # Check Chroma
    chroma_ok = False
    chunk_count = 0
    try:
        chunk_count = vector_store.collection.count()
        chroma_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if (db_ok and chroma_ok) else "degraded",
        "database": {"sqlite_connected": db_ok, "registered_sources": source_count},
        "vector_store": {"chroma_connected": chroma_ok, "indexed_chunks": chunk_count},
        "models": {
            "llm": settings.llm_model,
            "groq_configured": bool(settings.effective_groq_key),
            "reranker": settings.reranker_model,
            "hf_configured": bool(settings.effective_hf_token)
        }
    }
