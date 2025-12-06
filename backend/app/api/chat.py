"""
Chat API Router

Handles chat endpoints with streaming support using RAG engine.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio
from openai import OpenAI
from app.services.rag_engine import RAGEngine
from app.utils.config import get_settings
from app.utils.token_utils import get_tracker
# Import profile module to access global state
from app.api import profile

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Lazy-loaded singleton RAG engine
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = None
    stream: bool = True


class ChatResponse(BaseModel):
    response: str
    query_type: Optional[str] = None  # Removed - let LLM handle intent
    sources: Dict[str, Any]


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message and get a response with hybrid retrieval."""
    try:
        rag = get_rag_engine()
        
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        # Get current user profile
        # Get current user profile (optional - continue without if not available)
        try:
            current_profile = profile.load_profile()
        except Exception:
            current_profile = None
        
        result = rag.chat(
            query=request.message,
            conversation_history=history,
            user_profile=current_profile
        )
        
        return ChatResponse(
            response=result["response"],
            sources=result["sources"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat with LLM query rewriting and hybrid retrieval.
    """
    async def generate():
        try:
            rag = get_rag_engine()
            settings = get_settings()
            
            # Convert conversation history
            history = None
            if request.conversation_history:
                history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.conversation_history
                ]
            
            # Get current user profile
            # Get current user profile (optional - continue without if not available)
            try:
                current_profile = profile.load_profile()
            except Exception:
                current_profile = None
            
            # 1. Direct embedding search
            yield f"data: {json.dumps({'type': 'start', 'query': request.message})}\n\n"
            
            browsing, products = rag.retrieve(
                query=request.message, 
                user_profile=current_profile
            )
            yield f"data: {json.dumps({'type': 'sources', 'browsing': len(browsing), 'products': len(products)})}\n\n"
            
            # 2. Format context
            context = rag.format_context(browsing, products, user_profile=current_profile)
            
            # 3. Generate response with LLM-selected products
            response_text, selected_products = rag.generate_response(
                query=request.message,
                context=context,
                products=products,
                conversation_history=history
            )
            
            # Stream the response
            for i in range(0, len(response_text), 3):
                chunk = response_text[i:i+3]
                yield f"data: {json.dumps({'type': 'content', 'value': chunk})}\n\n"
                await asyncio.sleep(0.01)
            
            # Send completion with LLM-selected products
            yield f"data: {json.dumps({'type': 'done', 'full_response': response_text, 'browsing': browsing[:3], 'products': selected_products})}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/stats")
async def get_chat_stats():
    """Get chat/token usage statistics"""
    tracker = get_tracker()
    return tracker.to_dict()
