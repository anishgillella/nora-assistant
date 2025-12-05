"""
Phase 4 Backend API Test Script

Tests all API endpoints:
1. Chat endpoint
2. Chat streaming 
3. Memory ingestion
4. Recommendations
5. Conversations (SQLite)

Run with: python -m tests.test_api
"""
import httpx
from datetime import datetime
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("\n🧪 Testing Health Endpoint...")
    try:
        response = httpx.get(f"{BASE_URL}/api/health", timeout=5.0)
        if response.status_code == 200:
            print(f"   ✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False


def test_chat():
    """Test chat endpoint"""
    print("\n🧪 Testing Chat Endpoint...")
    try:
        response = httpx.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "What products have I looked at?",
                "stream": False
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Chat response received")
            print(f"      Query type: {data.get('query_type')}")
            print(f"      Response: {data.get('response', '')[:100]}...")
            return True
        else:
            print(f"   ❌ Chat failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Chat error: {e}")
        return False


def test_chat_stream():
    """Test chat streaming endpoint"""
    print("\n🧪 Testing Chat Streaming...")
    try:
        with httpx.stream(
            "POST",
            f"{BASE_URL}/api/chat/stream",
            json={"message": "Hello, recommend me some shoes"},
            timeout=30.0
        ) as response:
            if response.status_code == 200:
                chunks = 0
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        chunks += 1
                        if chunks <= 3:
                            data = json.loads(line[6:])
                            print(f"      Chunk: {data.get('type')}")
                
                print(f"   ✅ Received {chunks} streaming chunks")
                return True
            else:
                print(f"   ❌ Stream failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ Stream error: {e}")
        return False


def test_memory_stats():
    """Test memory stats endpoint"""
    print("\n🧪 Testing Memory Stats...")
    try:
        response = httpx.get(f"{BASE_URL}/api/memory/stats", timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Memory stats retrieved")
            print(f"      Total vectors: {data.get('total_vectors')}")
            print(f"      Browsing: {data.get('browsing_count')}")
            print(f"      Products: {data.get('products_count')}")
            return True
        else:
            print(f"   ❌ Memory stats failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Memory stats error: {e}")
        return False


def test_recommendations():
    """Test recommendations endpoint"""
    print("\n🧪 Testing Recommendations...")
    try:
        response = httpx.get(
            f"{BASE_URL}/api/recommendations",
            params={"query": "running shoes", "top_k": 3},
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            recs = data.get("recommendations", [])
            print(f"   ✅ Got {len(recs)} recommendations")
            print(f"      Based on: {data.get('based_on')}")
            for r in recs[:2]:
                print(f"      - {r.get('name')}: ${r.get('price')}")
            return True
        else:
            print(f"   ❌ Recommendations failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Recommendations error: {e}")
        return False


def test_conversations():
    """Test conversations CRUD"""
    print("\n🧪 Testing Conversations (SQLite)...")
    try:
        # Create conversation
        response = httpx.post(
            f"{BASE_URL}/api/conversations",
            json={"title": "Test Conversation"},
            timeout=10.0
        )
        
        if response.status_code != 200:
            print(f"   ❌ Create conversation failed: {response.status_code}")
            return False
        
        conv = response.json()
        conv_id = conv.get("id")
        print(f"   ✅ Created conversation: {conv_id[:8]}...")
        
        # Add message
        response = httpx.post(
            f"{BASE_URL}/api/conversations/{conv_id}/messages",
            json={"role": "user", "content": "Test message"},
            timeout=10.0
        )
        
        if response.status_code == 200:
            print(f"   ✅ Added message to conversation")
        else:
            print(f"   ❌ Add message failed: {response.status_code}")
            return False
        
        # Get conversation
        response = httpx.get(f"{BASE_URL}/api/conversations/{conv_id}", timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Retrieved conversation with {len(data.get('messages', []))} messages")
        else:
            print(f"   ❌ Get conversation failed: {response.status_code}")
            return False
        
        # Delete conversation
        response = httpx.delete(f"{BASE_URL}/api/conversations/{conv_id}", timeout=10.0)
        
        if response.status_code == 200:
            print(f"   ✅ Deleted conversation")
        else:
            print(f"   ❌ Delete failed: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"   ❌ Conversations error: {e}")
        return False


def run_all_tests():
    """Run all Phase 4 API tests"""
    print("=" * 60)
    print("PHASE 4: BACKEND API TESTS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print("=" * 60)
    
    results = {
        "health": test_health(),
        "chat": test_chat(),
        "chat_stream": test_chat_stream(),
        "memory_stats": test_memory_stats(),
        "recommendations": test_recommendations(),
        "conversations": test_conversations(),
    }
    
    print("\n" + "=" * 60)
    print("PHASE 4 TEST RESULTS")
    print("=" * 60)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test.ljust(18)}: {status}")
    
    all_passed = all(results.values())
    print("=" * 60)
    print(f"Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
