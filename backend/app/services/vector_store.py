"""
Pinecone Vector Store

Manages vector storage and retrieval using Pinecone.
Two namespaces: browsing-memory and products
"""
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Optional, Any
from app.utils.config import get_settings
from app.services.embeddings import VoyageEmbeddings
import uuid


class PineconeStore:
    """Manage vector storage in Pinecone"""
    
    # Namespace constants
    NS_BROWSING = "browsing-memory"
    NS_PRODUCTS = "products"
    
    def __init__(self):
        settings = get_settings()
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self.embeddings = VoyageEmbeddings()
        
        # Initialize index
        self._ensure_index()
        self.index = self.pc.Index(self.index_name)
    
    def _ensure_index(self):
        """Create index if it doesn't exist"""
        existing = [idx.name for idx in self.pc.list_indexes()]
        
        if self.index_name not in existing:
            print(f"📦 Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.embeddings.dimension,  # 512 for voyage-3-lite
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            print(f"✅ Index created: {self.index_name}")
    
    def upsert_browsing_memory(
        self, 
        entries: List[Dict[str, Any]]
    ) -> int:
        """
        Upsert browsing history entries to the browsing-memory namespace
        
        Args:
            entries: List of dicts with url, title, product_info, etc.
        
        Returns:
            Number of vectors upserted
        """
        if not entries:
            return 0
        
        # Create text representations for embedding
        texts = []
        for e in entries:
            text = f"{e.get('title', '')} {e.get('url', '')}"
            if e.get('product'):
                p = e['product']
                text += f" {p.get('name', '')} {p.get('brand', '')} {p.get('category', '')} ${p.get('price', 0)}"
            texts.append(text)
        
        # Generate embeddings
        embeddings = self.embeddings.embed_documents(texts)
        
        # Prepare vectors for upsert
        vectors = []
        for i, entry in enumerate(entries):
            vector_id = entry.get('id') or str(uuid.uuid4())
            vectors.append({
                "id": vector_id,
                "values": embeddings[i],
                "metadata": {
                    "url": entry.get("url", ""),
                    "title": entry.get("title", ""),
                    "domain": entry.get("domain", ""),
                    "visit_time": str(entry.get("visit_time", "")),
                    "product_name": entry.get("product", {}).get("name", ""),
                    "product_price": entry.get("product", {}).get("price", 0),
                    "product_category": entry.get("product", {}).get("category", ""),
                    "product_brand": entry.get("product", {}).get("brand", ""),
                }
            })
        
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch, namespace=self.NS_BROWSING)
        
        return len(vectors)
    
    def upsert_products(self, products: List[Dict[str, Any]]) -> int:
        """
        Upsert products to the products namespace
        
        Args:
            products: List of product dicts
        
        Returns:
            Number of vectors upserted
        """
        if not products:
            return 0
        
        # Create text representations
        texts = []
        for p in products:
            text = f"{p.get('name', '')} {p.get('brand', '')} {p.get('category', '')} "
            text += f"{p.get('description', '')} ${p.get('price', 0)}"
            if p.get('tags'):
                text += f" {' '.join(p['tags'][:5])}"
            texts.append(text)
        
        # Generate embeddings
        embeddings = self.embeddings.embed_documents(texts)
        
        # Prepare vectors
        vectors = []
        for i, p in enumerate(products):
            vector_id = p.get('id') or str(uuid.uuid4())
            vectors.append({
                "id": vector_id,
                "values": embeddings[i],
                "metadata": {
                    "name": p.get("name", ""),
                    "price": p.get("price", 0),
                    "currency": p.get("currency", "USD"),
                    "category": str(p.get("category", "")),
                    "brand": p.get("brand", ""),
                    "description": p.get("description", "")[:200],
                    "image_url": p.get("image_url", ""),
                    "product_url": p.get("product_url", ""),
                    "store_name": p.get("store_name", ""),
                }
            })
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch, namespace=self.NS_PRODUCTS)
        
        return len(vectors)
    
    def search_browsing(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search browsing history for relevant entries
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_dict: Optional metadata filter
        
        Returns:
            List of matching entries with scores
        """
        query_embedding = self.embeddings.embed_query(query)
        
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=self.NS_BROWSING,
            include_metadata=True,
            filter=filter_dict
        )
        
        return [
            {
                "id": match.id,
                "score": match.score,
                **match.metadata
            }
            for match in results.matches
        ]
    
    def search_products(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search products for recommendations
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_dict: Optional metadata filter
        
        Returns:
            List of matching products with scores
        """
        query_embedding = self.embeddings.embed_query(query)
        
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k * 2,  # Fetch extra to account for duplicates
            namespace=self.NS_PRODUCTS,
            include_metadata=True,
            filter=filter_dict
        )
        
        # Deduplicate by product name
        seen_names = set()
        unique_results = []
        for match in results.matches:
            name = match.metadata.get("name", "").lower().strip()
            if name and name not in seen_names:
                seen_names.add(name)
                unique_results.append({
                    "id": match.id,
                    "score": match.score,
                    **match.metadata
                })
                if len(unique_results) >= top_k:
                    break
        
        return unique_results
    
    def get_stats(self) -> Dict:
        """Get index statistics"""
        stats = self.index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "namespaces": {
                ns: data.vector_count 
                for ns, data in stats.namespaces.items()
            }
        }
    
    def delete_namespace(self, namespace: str):
        """Delete all vectors in a namespace"""
        self.index.delete(delete_all=True, namespace=namespace)
    
    def close(self):
        """Cleanup resources"""
        self.embeddings.close()
