"""
Phase 3 RAG Pipeline Test Script

Tests:
1. Voyage AI embeddings
2. Pinecone vector store (upsert + search)
3. RAG engine (query classification + retrieval + generation)

Run with: python -m tests.test_rag
"""
from datetime import datetime


def test_embeddings():
    """Test Voyage AI embedding generation"""
    print("\n🧪 Testing Voyage AI Embeddings...")
    try:
        from app.services.embeddings import VoyageEmbeddings
        from app.utils.config import get_settings
        
        settings = get_settings()
        if not settings.voyage_api_key:
            print("   ⚠️ VOYAGE_API_KEY not set, skipping")
            return True
        
        embeddings = VoyageEmbeddings()
        
        # Test single embedding
        text = "Nike Air Max running shoes for men"
        vector = embeddings.embed(text)
        
        print(f"   ✅ Generated embedding with {len(vector)} dimensions")
        print(f"      Sample values: [{vector[0]:.4f}, {vector[1]:.4f}, ...]")
        
        # Test batch embedding
        texts = ["Adidas sneakers", "Allbirds wool runners", "Patagonia jacket"]
        vectors = embeddings.embed_documents(texts)
        
        print(f"   ✅ Batch embedded {len(vectors)} texts")
        
        embeddings.close()
        return True
    except Exception as e:
        print(f"   ❌ Embeddings error: {e}")
        return False


def test_vector_store():
    """Test Pinecone vector store operations"""
    print("\n🧪 Testing Pinecone Vector Store...")
    try:
        from app.services.vector_store import PineconeStore
        from app.utils.config import get_settings
        
        settings = get_settings()
        if not settings.pinecone_api_key:
            print("   ⚠️ PINECONE_API_KEY not set, skipping")
            return True
        
        store = PineconeStore()
        
        # Get stats
        stats = store.get_stats()
        print(f"   ✅ Connected to Pinecone index")
        print(f"      Total vectors: {stats['total_vectors']}")
        print(f"      Namespaces: {stats['namespaces']}")
        
        # Test upserting mock browsing data
        from app.utils.mock_data import MockDataGenerator
        history = MockDataGenerator.generate_browsing_history(num_entries=3)
        
        entries = [
            {
                "id": e.id,
                "url": e.url,
                "title": e.title,
                "domain": e.domain,
                "visit_time": str(e.visit_time),
                "product": {
                    "name": e.product.name,
                    "price": e.product.price,
                    "category": e.product.category,
                    "brand": e.product.brand
                }
            }
            for e in history
        ]
        
        count = store.upsert_browsing_memory(entries)
        print(f"   ✅ Upserted {count} browsing entries")
        
        # Test upserting mock products
        products = MockDataGenerator.generate_products(num_products=3)
        product_dicts = [
            {
                "id": p.id,
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
            for p in products
        ]
        
        count = store.upsert_products(product_dicts)
        print(f"   ✅ Upserted {count} products")
        
        # Test search
        import time
        time.sleep(1)  # Wait for index to update
        
        results = store.search_products("running shoes", top_k=2)
        print(f"   ✅ Product search returned {len(results)} results")
        for r in results[:2]:
            print(f"      - {r.get('name', 'Unknown')} (score: {r.get('score', 0):.3f})")
        
        store.close()
        return True
    except Exception as e:
        print(f"   ❌ Vector store error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_engine():
    """Test RAG engine query classification and response"""
    print("\n🧪 Testing RAG Engine...")
    try:
        from app.services.rag_engine import RAGEngine, QueryType
        from app.utils.config import get_settings
        
        settings = get_settings()
        if not settings.openrouter_api_key or not settings.pinecone_api_key:
            print("   ⚠️ Required API keys not set, skipping")
            return True
        
        rag = RAGEngine()
        
        # Test query classification
        test_queries = [
            ("What shoes did I look at last week?", QueryType.MEMORY_RECALL),
            ("Find me some running shoes", QueryType.PRODUCT_SEARCH),
            ("Recommend products based on my style", QueryType.RECOMMENDATION),
            ("Hello, how are you?", QueryType.GENERAL_CHAT),
        ]
        
        print("   Testing query classification:")
        for query, expected in test_queries:
            result = rag.classify_query(query)
            status = "✅" if result == expected else "⚠️"
            print(f"      {status} '{query[:35]}...' -> {result.value}")
        
        # Test full chat
        print("\n   Testing full RAG chat:")
        response = rag.chat("What products have I been looking at?")
        print(f"      Query type: {response['query_type']}")
        print(f"      Response: {response['response'][:100]}...")
        print(f"      Sources: {len(response['sources']['browsing'])} browsing, {len(response['sources']['products'])} products")
        
        rag.close()
        return True
    except Exception as e:
        print(f"   ❌ RAG engine error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 3 tests"""
    print("=" * 60)
    print("PHASE 3: RAG PIPELINE TESTS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {
        "embeddings": test_embeddings(),
        "vector_store": test_vector_store(),
        "rag_engine": test_rag_engine(),
    }
    
    print("\n" + "=" * 60)
    print("PHASE 3 TEST RESULTS")
    print("=" * 60)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test.ljust(15)}: {status}")
    
    all_passed = all(results.values())
    print("=" * 60)
    print(f"Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("=" * 60)
    
    # Print token usage
    try:
        from app.utils.token_utils import get_tracker
        tracker = get_tracker()
        if tracker.total_tokens > 0:
            print(tracker.summary())
    except Exception:
        pass
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
