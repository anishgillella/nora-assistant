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
        
        Now supports BrowsingActivity schema with semantic_summary and visit_timestamp.
        """
        if not entries:
            return 0
        
        # Create text representations for embedding
        # Prioritize semantic_summary if available, fallback to legacy format
        texts = []
        for e in entries:
            if e.get('semantic_summary'):
                # New BrowsingActivity format - use semantic_summary
                text = e['semantic_summary']
            elif e.get('product'):
                # Legacy product format
                p = e['product']
                text = f"{e.get('title', '')} {p.get('name', '')} {p.get('brand', '')} {p.get('category', '')} ${p.get('price', 0)}"
            else:
                # Fallback
                text = f"{e.get('title', '')} {e.get('url', '')}"
            texts.append(text)
        
        # Generate embeddings
        embeddings = self.embeddings.embed_documents(texts)
        
        # Prepare vectors for upsert
        vectors = []
        for i, entry in enumerate(entries):
            vector_id = entry.get('id') or str(uuid.uuid4())
            
            # Build metadata - handle both new and legacy formats
            metadata = {
                "url": entry.get("url", ""),
                "title": entry.get("title", ""),
                "domain": entry.get("domain", ""),
                "visit_time": str(entry.get("visit_time", "")),
            }
            
            # New BrowsingActivity fields
            if entry.get("visit_timestamp"):
                metadata["visit_timestamp"] = entry["visit_timestamp"]  # Numeric for filtering
            if entry.get("activity_type"):
                metadata["activity_type"] = entry["activity_type"]
            if entry.get("category"):
                metadata["category"] = entry["category"]
            if entry.get("topics"):
                metadata["topics"] = ",".join(entry["topics"])  # Pinecone doesn't support lists well, join
            if entry.get("context"):
                metadata["context"] = ",".join(entry["context"])
            if entry.get("vibe"):
                metadata["vibe"] = ",".join(entry["vibe"])
            if entry.get("inferred_needs"):
                metadata["inferred_needs"] = ",".join(entry["inferred_needs"])
            if entry.get("semantic_summary"):
                metadata["semantic_summary"] = entry["semantic_summary"][:500]  # Truncate for Pinecone limits
            if entry.get("brand"):
                metadata["brand"] = entry["brand"]
            if entry.get("price"):
                metadata["price"] = entry["price"]
            
            # Legacy product fields (backward compatibility)
            if entry.get("product"):
                p = entry["product"]
                metadata["product_name"] = p.get("name", "")
                metadata["product_price"] = p.get("price", 0)
                metadata["product_category"] = p.get("category", "")
                metadata["product_brand"] = p.get("brand", "")
            
            vectors.append({
                "id": vector_id,
                "values": embeddings[i],
                "metadata": metadata
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
            # Base features
            text = f"{p.get('name', '')} {p.get('brand', '')} {p.get('category', '')} "
            text += f"{p.get('description', '')} ${p.get('price', 0)}"
            
            # Add Rich Attributes tokens to embedding text
            rich_features = []
            if p.get('materials'): rich_features.extend(p['materials'])
            if p.get('visual_characteristics'): rich_features.extend(p['visual_characteristics'])
            if p.get('occasion'): rich_features.extend(p['occasion'])
            if p.get('gender_target'): rich_features.append(p['gender_target'])
            if p.get('sustainability'): rich_features.extend(p['sustainability'])
            
            if rich_features:
                text += f" {' '.join(rich_features)}"
                
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
                    "description": p.get("description", "")[:500],
                    "image_url": p.get("image_url", ""),
                    "product_url": p.get("product_url", ""),
                    "store_name": p.get("store_name", ""),
                    # Store rich attributes in metadata for potential future filtering
                    "materials": p.get("materials", []),
                    "occasion": p.get("occasion", []),
                    "visual_characteristics": p.get("visual_characteristics", []),
                    "gender_target": p.get("gender_target") or "",
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
    
    def list_all_browsing(self, limit: int = 500) -> List[Dict]:
        """List all browsing entries from Pinecone"""
        # Use a dummy query to get results (Pinecone doesn't have a list operation)
        # We'll use a zero vector to get random results
        dummy_vector = [0.0] * self.embeddings.dimension
        
        results = self.index.query(
            vector=dummy_vector,
            top_k=limit,
            namespace=self.NS_BROWSING,
            include_metadata=True
        )
        
        items = []
        for match in results.matches:
            meta = match.metadata or {}
            items.append({
                "id": match.id,
                "url": meta.get("url", ""),
                "title": meta.get("title", ""),
                "domain": meta.get("domain", ""),
                "visit_time": meta.get("visit_time", ""),
                # New unified fields
                "activity_type": meta.get("activity_type", ""),
                "category": meta.get("category", ""),
                "topics": meta.get("topics", "").split(",") if meta.get("topics") else [],
                "context": meta.get("context", "").split(",") if meta.get("context") else [],
                "vibe": meta.get("vibe", "").split(",") if meta.get("vibe") else [],
                "inferred_needs": meta.get("inferred_needs", "").split(",") if meta.get("inferred_needs") else [],
                "semantic_summary": meta.get("semantic_summary", ""),
                "brand": meta.get("brand", ""),
                "price": meta.get("price", 0),
                # Legacy fields for backward compatibility
                "product_name": meta.get("product_name", ""),
                "product_price": meta.get("product_price", 0),
                "product_category": meta.get("product_category", ""),
                "product_brand": meta.get("product_brand", ""),
            })
        return items
    
    def list_all_products(self, limit: int = 500) -> List[Dict]:
        """List all products from Pinecone"""
        dummy_vector = [0.0] * self.embeddings.dimension
        
        results = self.index.query(
            vector=dummy_vector,
            top_k=limit,
            namespace=self.NS_PRODUCTS,
            include_metadata=True
        )
        
        items = []
        for match in results.matches:
            meta = match.metadata or {}
            items.append({
                "id": match.id,
                "name": meta.get("name", ""),
                "brand": meta.get("brand", ""),
                "category": meta.get("category", ""),
                "price": meta.get("price", 0),
                "description": meta.get("description", ""),
                "image_url": meta.get("image_url", ""),
                "product_url": meta.get("product_url", ""),
                "store_name": meta.get("store_name", ""),
                # Rich attributes
                "materials": meta.get("materials", []),
                "occasion": meta.get("occasion", []),
                "visual_characteristics": meta.get("visual_characteristics", []),
                "gender_target": meta.get("gender_target"),
                "season": meta.get("season", []),
                "sustainability": meta.get("sustainability", []),
                "color_family": meta.get("color_family", []),
            })
        return items
    
    def delete_namespace(self, namespace: str):
        """Delete all vectors in a namespace"""
        self.index.delete(delete_all=True, namespace=namespace)
    
    def close(self):
        """Cleanup resources"""
        self.embeddings.close()
