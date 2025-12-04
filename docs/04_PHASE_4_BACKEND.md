# Phase 4: Backend API

## 🎯 Objectives

1. Implement FastAPI endpoints
2. Create chat endpoints with streaming response
3. Implement memory management endpoints
4. Set up SQLite persistence for conversations
5. Integrate RAG engine with API

---

## 🔌 API Endpoints

### Chat Router (`api/chat.py`)

```python
POST /api/chat/message
Request:
{
    "message": "Find me shoes like the ones I looked at yesterday",
    "conversation_id": "optional-uuid"
}

Response (Streaming SSE):
event: token
data: "Here"

event: token
data: " are"
...
event: sources
data: [{"title": "Nike Air Max", "url": "..."}]
```

### Memory Router (`api/memory.py`)

```python
POST /api/memory/ingest
# Triggers Chrome history ingestion
Response: {"status": "success", "items_processed": 50}

GET /api/memory/stats
Response: {
    "total_items": 150,
    "top_categories": ["shoes", "electronics"],
    "recent_visits": [...]
}
```

### Recommendations Router (`api/recommendations.py`)

```python
GET /api/recommendations
Query Params: ?category=shoes&price_max=200
Response: {
    "recommendations": [
        {
            "product": {...},
            "reasoning": "Matches your interest in running shoes"
        }
    ]
}
```

---

## 💾 Database Schema (SQLite)

### Conversations Table
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title TEXT
);
```

### Messages Table
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    role TEXT, -- 'user' or 'assistant'
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);
```

---

## 🔧 Implementation Details

### Streaming Response
Use `StreamingResponse` from FastAPI:

```python
async def stream_generator(response_stream):
    for chunk in response_stream:
        if chunk.content:
            yield f"data: {json.dumps({'token': chunk.content})}\n\n"
```

### Context Injection
1. Receive user message
2. Classify intent
3. Retrieve relevant docs from Pinecone
4. Format context string
5. Send to OpenRouter (GPT-4o-mini) with system prompt

---

## 🧪 Testing

Run `backend/tests/test_api.py`:
1. Test `/health`
2. Test `/chat/message` (mocked LLM)
3. Test `/memory/ingest`
4. Verify DB persistence
