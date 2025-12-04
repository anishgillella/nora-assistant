# Phase 3: RAG Pipeline & Vector Storage

## 🎯 Objectives

1. Configure Pinecone vector database
2. Implement OpenAI embeddings service
3. Create RAG retrieval engine
4. Implement query classification
5. Build context assembly logic

---

## 🏗 Architecture

```
User Query → Query Classifier (LLM) → 
  IF "Product Search":
    → Generate Query Embedding
    → Search "products" Namespace
    → Filter by Metadata (Price, Category)
  IF "Memory Recall":
    → Generate Query Embedding
    → Search "browsing-memory" Namespace
    → Filter by Time/Intent
  
  → Retrieve Top-K Results
  → Rerank (Optional)
  → Assemble Context
  → Send to Chat LLM
```

---

## 🔧 Implementation

### 1. Pinecone Service (`pinecone_service.py`)

```python
from pinecone import Pinecone, ServerlessSpec
from app.utils.config import get_settings

class PineconeService:
    def __init__(self):
        settings = get_settings()
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        
        # Initialize index if not exists
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=1536, # OpenAI text-embedding-3-small
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=settings.pinecone_environment
                )
            )
        self.index = self.pc.Index(self.index_name)

    async def upsert_browsing_history(self, entries: List[BrowsingHistoryEntry]):
        vectors = []
        for entry in entries:
            # Create rich text representation
            text = f"{entry.title} {entry.product.description if entry.product else ''}"
            embedding = await self.get_embedding(text)
            
            vectors.append({
                "id": entry.id,
                "values": embedding,
                "metadata": {
                    "type": "browsing",
                    "url": str(entry.url),
                    "title": entry.title,
                    "category": entry.product.category if entry.product else None,
                    "intent": entry.intent,
                    "timestamp": entry.visit_time.timestamp()
                }
            })
        
        self.index.upsert(vectors=vectors, namespace="browsing-memory")

    async def upsert_products(self, products: List[Product]):
        vectors = []
        for product in products:
            text = f"{product.name} {product.brand} {product.category} {product.description}"
            embedding = await self.get_embedding(text)
            
            vectors.append({
                "id": product.id,
                "values": embedding,
                "metadata": {
                    "type": "product",
                    "name": product.name,
                    "price": product.price,
                    "category": product.category,
                    "brand": product.brand,
                    "store": product.store_name
                }
            })
            
        self.index.upsert(vectors=vectors, namespace="products")
```

### 2. Embeddings Service (`embeddings.py`)

- Use `openai.embeddings.create`
- Model: `text-embedding-3-small`
- Batch processing for efficiency

### 3. RAG Engine (`rag_engine.py`)

#### Query Classification
Use LLM to classify query into:
- `PREFERENCE`: "What do I like?"
- `FACTUAL`: "How much was X?"
- `RECOMMENDATION`: "Find me something similar to X"
- `SUMMARY`: "Summarize my history"

#### Retrieval
```python
async def retrieve(query: str, filters: dict = None, namespace: str = "browsing-memory"):
    embedding = await get_embedding(query)
    results = index.query(
        namespace=namespace,
        vector=embedding,
        top_k=10,
        include_metadata=True,
        filter=filters
    )
    return results
```

---

## 🧪 Testing

Run `backend/tests/test_rag.py`:
1. Verify index creation
2. Test embedding generation
3. Upsert mock data
4. Perform similarity search
5. Verify metadata filtering
