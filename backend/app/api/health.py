from fastapi import APIRouter, Depends
from datetime import datetime
from app.utils.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    """Health check endpoint to verify service is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "nora-browsing-memory",
        "version": "1.0.0",
        "config": {
            "pinecone_index": settings.pinecone_index_name,
            "embedding_model": settings.embedding_model,
            "chat_model": settings.chat_model
        }
    }
