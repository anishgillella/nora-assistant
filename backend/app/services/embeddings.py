"""
Voyage AI Embedding Service

Uses Voyage AI's voyage-3-lite model for text embeddings.
Optimized for semantic search and retrieval.
"""
import httpx
from typing import List, Optional
from app.utils.config import get_settings


class VoyageEmbeddings:
    """Generate embeddings using Voyage AI API"""
    
    BASE_URL = "https://api.voyageai.com/v1"
    
    def __init__(self, api_key: str = None):
        settings = get_settings()
        self.api_key = api_key or settings.voyage_api_key
        self.model = settings.embedding_model  # voyage-3-lite
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
        
        Returns:
            List of floats representing the embedding vector
        """
        return self.embed_batch([text])[0]
    
    def embed_batch(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            input_type: "document" for indexing, "query" for searching
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Voyage AI has a limit of 128 texts per request
        batch_size = 128
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            response = self.client.post(
                f"{self.BASE_URL}/embeddings",
                json={
                    "model": self.model,
                    "input": batch,
                    "input_type": input_type
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Voyage API error: {response.status_code} - {response.text}")
            
            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a search query (optimized for retrieval)"""
        return self.embed_batch([query], input_type="query")[0]
    
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Embed documents for indexing"""
        return self.embed_batch(documents, input_type="document")
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension for voyage-3-large"""
        return 1024  # voyage-3-large outputs 1024-dim vectors by default
    
    def close(self):
        """Close HTTP client"""
        self.client.close()
