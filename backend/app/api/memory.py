"""
Memory API Router

Handles memory ingestion and retrieval from browsing history.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.services.chrome_extractor import ChromeHistoryExtractor
from app.services.vector_store import PineconeStore
from app.services.gemini_structurer import GeminiStructurer
from app.services.firecrawl_scraper import FirecrawlScraper
from app.utils.config import get_settings

router = APIRouter(prefix="/api/memory", tags=["memory"])

# Lazy-loaded singletons
_vector_store: Optional[PineconeStore] = None


def get_vector_store() -> PineconeStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = PineconeStore()
    return _vector_store


class IngestRequest(BaseModel):
    days_back: int = 30
    max_urls: int = 20
    ecommerce_only: bool = True
    enrich_with_firecrawl: bool = False  # Optional: scrape page content


class IngestResponse(BaseModel):
    status: str
    entries_processed: int
    entries_indexed: int
    message: str


class MemoryStats(BaseModel):
    total_vectors: int
    browsing_count: int
    products_count: int
    last_ingest: Optional[str] = None


@router.post("/ingest", response_model=IngestResponse)
async def ingest_browsing_history(request: IngestRequest):
    """
    Ingest browsing history from Chrome into Pinecone.
    
    Extracts e-commerce URLs from Chrome history, optionally enriches
    with Firecrawl content, extracts product info with Gemini, and
    stores embeddings in Pinecone.
    """
    try:
        settings = get_settings()
        
        # Extract Chrome history
        extractor = ChromeHistoryExtractor()
        raw_entries = extractor.extract(
            days_back=request.days_back,
            limit=request.max_urls,
            ecommerce_only=request.ecommerce_only
        )
        
        if not raw_entries:
            return IngestResponse(
                status="success",
                entries_processed=0,
                entries_indexed=0,
                message="No browsing history found matching criteria"
            )
        
        # Prepare entries for indexing
        structurer = GeminiStructurer()
        firecrawl = FirecrawlScraper() if request.enrich_with_firecrawl else None
        
        entries_to_index = []
        for entry in raw_entries:
            entry_data = {
                "id": f"browse_{entry.id}_{int(datetime.now().timestamp())}",
                "url": entry.url,
                "title": entry.title,
                "domain": entry.url.split("/")[2] if "/" in entry.url else "",
                "visit_time": ChromeHistoryExtractor.chrome_time_to_datetime(
                    entry.last_visit_time
                ).isoformat(),
                "visit_count": entry.visit_count,
                "product": {}
            }
            
            # Optionally enrich with Firecrawl
            content = ""
            if firecrawl and settings.firecrawl_api_key:
                try:
                    result = firecrawl.scrape(entry.url)
                    if result and result.get("success"):
                        content = result.get("markdown", "")[:2000]
                except Exception:
                    pass  # Skip failed scrapes
            
            # Extract product info with Gemini
            if entry.title or content:
                product_info = structurer.extract_product_from_page(
                    url=entry.url,
                    title=entry.title,
                    content=content or entry.title
                )
                if product_info:
                    entry_data["product"] = {
                        "name": product_info.name,
                        "price": product_info.price or 0,
                        "category": product_info.category or "other",
                        "brand": product_info.brand or "",
                        "description": product_info.description or ""
                    }
            
            entries_to_index.append(entry_data)
        
        # Index in Pinecone
        store = get_vector_store()
        indexed_count = store.upsert_browsing_memory(entries_to_index)
        
        if firecrawl:
            firecrawl.close()
        
        return IngestResponse(
            status="success",
            entries_processed=len(raw_entries),
            entries_indexed=indexed_count,
            message=f"Successfully indexed {indexed_count} browsing entries"
        )
        
    except FileNotFoundError:
        return IngestResponse(
            status="warning",
            entries_processed=0,
            entries_indexed=0,
            message="Chrome history file not found"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStats)
async def get_memory_stats():
    """Get statistics about stored memory"""
    try:
        store = get_vector_store()
        stats = store.get_stats()
        
        return MemoryStats(
            total_vectors=stats.get("total_vectors", 0),
            browsing_count=stats.get("namespaces", {}).get("browsing-memory", 0),
            products_count=stats.get("namespaces", {}).get("products", 0),
            last_ingest=None  # Could track this in SQLite
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_memory(query: str, top_k: int = 5):
    """Search browsing memory for relevant entries"""
    try:
        store = get_vector_store()
        results = store.search_browsing(query, top_k=top_k)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_memory():
    """Clear all browsing memory (use with caution!)"""
    try:
        store = get_vector_store()
        store.delete_namespace("browsing-memory")
        return {"status": "success", "message": "Browsing memory cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
