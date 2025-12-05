from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.config import get_settings
from app.api import health
from app.api import (
    chat_router,
    memory_router,
    recommendations_router,
    conversations_router,
    data_router,
)

settings = get_settings()

app = FastAPI(
    title="Nora Browsing Memory API",
    description="Personal shopping memory with RAG-powered recommendations",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routes
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(recommendations_router)
app.include_router(conversations_router)
app.include_router(data_router)


@app.on_event("startup")
async def startup_event():
    print("🚀 Nora API starting up...")
    print(f"📍 Frontend URL: {settings.frontend_url}")
    print(f"🔌 Backend Port: {settings.backend_port}")
    print("📚 Available endpoints:")
    print("   - POST /api/chat         (chat with RAG)")
    print("   - POST /api/chat/stream  (streaming chat)")
    print("   - POST /api/memory/ingest (import Chrome history)")
    print("   - GET  /api/memory/stats  (memory statistics)")
    print("   - GET  /api/recommendations (product recommendations)")
    print("   - GET  /api/conversations (conversation history)")


@app.on_event("shutdown")
async def shutdown_event():
    print("👋 Nora API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True
    )

