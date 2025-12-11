"""
Data API Router

Provides endpoints to view and export browsing history and product data.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import os
from datetime import datetime
from app.services.vector_store import PineconeStore

router = APIRouter(prefix="/api/data", tags=["data"])

# Point to backend/data_ingestion/data
# __file__ is backend/app/api/data.py -> ... -> backend
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BACKEND_DIR, "data_ingestion", "data")
os.makedirs(DATA_DIR, exist_ok=True)


class DataResponse(BaseModel):
    count: int
    data: List[Dict[str, Any]]
    exported_at: str


def get_browsing_file_path():
    return os.path.join(DATA_DIR, "browsing_history.json")


def get_products_file_path():
    return os.path.join(DATA_DIR, "products.json")


@router.get("/browsing", response_model=DataResponse)
async def get_browsing_data(limit: int = 100, offset: int = 0):
    """
    Get browsing history data.
    Returns the data from the local JSON file if available.
    """
    file_path = get_browsing_file_path()
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            all_data = json.load(f)
        
        data = all_data[offset:offset + limit]
        return DataResponse(
            count=len(all_data),
            data=data,
            exported_at=datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        )
    
    return DataResponse(
        count=0,
        data=[],
        exported_at=datetime.now().isoformat()
    )


@router.get("/products", response_model=DataResponse)
async def get_products_data(limit: int = 100, offset: int = 0, category: Optional[str] = None):
    """
    Get products catalog data.
    Returns the data from the local JSON file if available.
    """
    file_path = get_products_file_path()
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            all_data = json.load(f)
        
        # Filter by category if specified
        if category:
            all_data = [p for p in all_data if p.get("category", "").lower() == category.lower()]
        
        data = all_data[offset:offset + limit]
        return DataResponse(
            count=len(all_data),
            data=data,
            exported_at=datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        )
    
    return DataResponse(
        count=0,
        data=[],
        exported_at=datetime.now().isoformat()
    )


@router.get("/export/browsing")
async def export_browsing():
    """Export browsing history as JSON file download."""
    file_path = get_browsing_file_path()
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="No browsing data exported yet")
    
    return FileResponse(
        file_path,
        media_type="application/json",
        filename="browsing_history.json"
    )


@router.get("/export/products")
async def export_products():
    """Export products catalog as JSON file download."""
    file_path = get_products_file_path()
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="No products data exported yet")
    
    return FileResponse(
        file_path,
        media_type="application/json",
        filename="products.json"
    )


@router.get("/categories")
async def get_categories():
    """Get unique product categories."""
    file_path = get_products_file_path()
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            all_data = json.load(f)
        
        categories = list(set(p.get("category", "unknown") for p in all_data if p.get("category")))
        return {"categories": sorted(categories)}
    
    return {"categories": []}


@router.post("/sync")
async def sync_from_pinecone():
    """
    Sync data from Pinecone to local JSON files.
    This ensures Data Explorer shows all vectors from the database.
    """
    store = PineconeStore()
    
    # Fetch all browsing entries
    browsing_data = store.list_all_browsing(limit=500)
    browsing_file = get_browsing_file_path()
    with open(browsing_file, "w") as f:
        json.dump(browsing_data, f, indent=2, default=str)
    
    # Fetch all products
    products_data = store.list_all_products(limit=500)
    products_file = get_products_file_path()
    with open(products_file, "w") as f:
        json.dump(products_data, f, indent=2, default=str)
    
    store.close()
    
    return {
        "status": "success",
        "browsing_synced": len(browsing_data),
        "products_synced": len(products_data),
        "message": f"Synced {len(browsing_data)} browsing entries and {len(products_data)} products"
    }


@router.get("/debug-stats")
async def debug_stats():
    """Debug endpoint to check Pinecone index stats"""
    store = PineconeStore()
    stats = store.index.describe_index_stats()
    
    # Also try a test query in each namespace
    dummy_vector = [0.0] * store.embeddings.dimension
    
    browsing_results = store.index.query(
        vector=dummy_vector,
        top_k=10,
        namespace=store.NS_BROWSING,
        include_metadata=True
    )
    
    products_results = store.index.query(
        vector=dummy_vector,
        top_k=10,
        namespace=store.NS_PRODUCTS,
        include_metadata=True
    )
    
    store.close()
    
    return {
        "index_stats": {
            "total_vectors": stats.total_vector_count,
            "namespaces": {ns: data.vector_count for ns, data in stats.namespaces.items()} if stats.namespaces else {}
        },
        "browsing_query_results": len(browsing_results.matches),
        "products_query_results": len(products_results.matches),
        "NS_BROWSING": store.NS_BROWSING,
        "NS_PRODUCTS": store.NS_PRODUCTS
    }


def save_browsing_data(data: List[Dict]):
    """Save browsing data to JSON file."""
    file_path = get_browsing_file_path()
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return file_path


def save_products_data(data: List[Dict]):
    """Save products data to JSON file."""
    file_path = get_products_file_path()
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return file_path
