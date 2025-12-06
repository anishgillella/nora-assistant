"""
Recommendations API Router

Handles product recommendation endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.vector_store import PineconeStore
from app.services.shopify_scraper import ShopifyScraper
from app.utils.config import get_settings

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

# Lazy-loaded singletons
_vector_store: Optional[PineconeStore] = None


def get_vector_store() -> PineconeStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = PineconeStore()
    return _vector_store


class ProductRecommendation(BaseModel):
    id: str
    name: str
    price: float
    brand: str
    category: str
    description: str
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    store_name: Optional[str] = None
    score: float


class RecommendationResponse(BaseModel):
    recommendations: List[ProductRecommendation]
    based_on: str  # What the recommendations are based on


@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    query: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 5
):
    """
    Get product recommendations.
    
    If query is provided, returns products matching the query.
    Otherwise, returns products similar to user's browsing history.
    """
    try:
        store = get_vector_store()
        
        # Build filter if category specified
        filter_dict = None
        if category:
            filter_dict = {"category": category}
        
        if query:
            # Direct product search
            results = store.search_products(query, top_k=top_k, filter_dict=filter_dict)
            based_on = f"Search: {query}"
        else:
            # Get recommendations based on browsing history
            # First, get user's recent browsing
            browsing = store.search_browsing("products shoes clothing", top_k=3)
            
            if browsing:
                # Use browsing history to find similar products
                browsing_context = " ".join([
                    f"{b.get('product_name', '')} {b.get('product_category', '')}"
                    for b in browsing
                ])
                results = store.search_products(
                    browsing_context, 
                    top_k=top_k, 
                    filter_dict=filter_dict
                )
                based_on = "Your browsing history"
            else:
                # Fallback to general popular products
                results = store.search_products(
                    "popular trending products", 
                    top_k=top_k,
                    filter_dict=filter_dict
                )
                based_on = "Popular products"
        
        recommendations = [
            ProductRecommendation(
                id=r.get("id", ""),
                name=r.get("name", "Unknown"),
                price=float(r.get("price", 0)),
                brand=r.get("brand", ""),
                category=r.get("category", "other"),
                description=r.get("description", ""),
                image_url=r.get("image_url"),
                product_url=r.get("product_url"),
                store_name=r.get("store_name"),
                score=float(r.get("score", 0))
            )
            for r in results
        ]
        
        return RecommendationResponse(
            recommendations=recommendations,
            based_on=based_on
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_product_catalog(max_stores: int = 3, products_per_store: int = 10):
    """
    Refresh the product catalog from Shopify stores.
    
    Scrapes products from configured Shopify stores and indexes them
    in Pinecone for recommendations.
    """
    try:
        scraper = ShopifyScraper()
        store = get_vector_store()
        
        # Scrape products
        products = await scraper.scrape_and_convert_all()
        
        if not products:
            return {
                "status": "warning",
                "products_indexed": 0,
                "message": "No products scraped"
            }
        
        # Convert to dicts for indexing
        product_dicts = [
            {
                "id": p.id or f"product_{i}",
                "name": p.name,
                "price": p.price,
                "category": p.category.value if hasattr(p.category, 'value') else str(p.category),
                "brand": p.brand,
                "description": p.description,
                "image_url": p.image_url,
                "product_url": p.product_url,
                "store_name": p.store_name,
                "tags": p.tags
            }
            for i, p in enumerate(products)
        ]
        
        # Index in Pinecone
        indexed_count = store.upsert_products(product_dicts)
        
        await scraper.close()
        
        return {
            "status": "success",
            "products_indexed": indexed_count,
            "stores_scraped": len(set(p.get("store_name") for p in product_dicts)),
            "message": f"Successfully indexed {indexed_count} products"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_product_catalog():
    """Clear all products from the catalog."""
    try:
        store = get_vector_store()
        store.delete_namespace("products")
        return {"status": "success", "message": "Product catalog cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
