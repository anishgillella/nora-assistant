# Nora Browsing Memory Prototype - Technical Overview

## 🎯 Project Goal

Build a conversational AI system that transforms raw browsing history into a searchable memory layer and provides personalized product recommendations.

---

## 🏗 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         React + TypeScript Frontend (Port 5173)             │
│  - Chat Interface (streaming responses)                     │
│  - Product Recommendations                                  │
│  - Browsing History Timeline                                │
│  - Shopping Stats Dashboard                                 │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/SSE
                        ↓
┌─────────────────────────────────────────────────────────────┐
│         Python + FastAPI Backend (Port 8000)                │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         LLM Agent Orchestrator                      │    │
│  │  - Query classification                             │    │
│  │  - Context building                                 │    │
│  │  - OpenRouter + GPT-4o-mini                        │    │
│  │  - Streaming responses                              │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐              ┌──────────────┐            │
│  │ Browsing     │              │ Product      │            │
│  │ Memory RAG   │              │ Recommender  │            │
│  │ (Retrieval)  │              │ RAG          │            │
│  └──────────────┘              └──────────────┘            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         SQLite Database                              │   │
│  │  - Conversation history                              │   │
│  │  - User profiles                                     │   │
│  │  - Cached metadata                                   │   │
│  └─────────────────────────────────────────────────────┘   │
└───────┬──────────────────────────────────┬──────────────────┘
        │                                  │
        ↓                                  ↓
┌──────────────────────┐        ┌──────────────────────┐
│  PINECONE (Cloud)    │        │  OpenAI Embeddings   │
│  Namespace:          │        │  text-embedding-3-   │
│  - browsing-memory   │        │  small               │
│  - products          │        │                      │
└──────────────────────┘        └──────────────────────┘
        ↑
        │
┌──────────────────────────────────────────────────────────┐
│              Data Ingestion Pipelines                    │
│                                                           │
│  1. Chrome History → Firecrawl → Gemini → Embeddings    │
│  2. Shopify /products.json → Gemini → Embeddings        │
│  3. Mock Data Generator (for testing)                    │
└──────────────────────────────────────────────────────────┘
```

---

## 🔧 Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI (async web framework)
- **LLM Provider:** OpenRouter (GPT-4o-mini)
- **Embeddings:** OpenAI text-embedding-3-small
- **Vector DB:** Pinecone (cloud-hosted)
- **Database:** SQLite (conversation persistence)
- **Scraping:** Firecrawl API
- **Data Validation:** Pydantic v2

### Frontend
- **Language:** TypeScript
- **Framework:** React 18
- **Build Tool:** Vite
- **HTTP Client:** Axios
- **State Management:** React Context/Hooks
- **Styling:** Tailwind CSS (optional) or CSS modules

### Data Processing
- **Chrome History:** SQLite3 (direct DB access)
- **Content Scraping:** Firecrawl API
- **Data Structuring:** Gemini 2.5 Flash (via OpenRouter)
- **Embeddings:** OpenAI API

---

## 📊 Data Models

### Browsing History
```typescript
{
  id: string;
  url: string;
  title: string;
  visitTime: Date;
  product?: {
    name: string;
    price: number;
    category: string;
    brand?: string;
    imageUrl?: string;
  };
  intent: "browsing" | "purchasing" | "researching";
  embedding: number[];
  metadata: Record<string, any>;
}
```

### Product
```typescript
{
  id: string;
  name: string;
  price: number;
  category: string;
  brand: string;
  description: string;
  imageUrl: string;
  url: string;
  store: string;
  tags: string[];
  embedding: number[];
}
```

### Conversation
```typescript
{
  id: string;
  userId: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  timestamp: Date;
}
```

---

## 🎯 Core Features

### 1. Shopping Memory Chat
- **Query Types:**
  - Preference: "What shoes do I like?"
  - Factual: "What is the price of Nike Air Max?"
  - Summary: "Summarize my shopping habits"
  
- **Retrieval Strategy:**
  - Semantic search via embeddings
  - Metadata filtering (date, category, price)
  - Context aggregation for LLM

### 2. Product Recommendations
- **Query Types:**
  - General: "Recommend items based on my browsing"
  - Specific: "Find alternatives to [product]"
  
- **Ranking Algorithm:**
  1. Vector similarity (user preference vs. products)
  2. Category alignment
  3. Price range compatibility
  4. Recency weighting

### 3. Streaming Responses
- Server-Sent Events (SSE) for real-time LLM responses
- Token-by-token streaming in chat UI
- Graceful error handling

---

## 🔐 Environment Variables

```bash
# LLM & Embeddings
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...

# Vector Database
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=nora-browsing-memory

# Scraping
FIRECRAWL_API_KEY=...

# Database
DATABASE_URL=sqlite:///./nora.db

# Server
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
```

---

## 📁 Project Structure

```
nora-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/          # Pydantic models
│   │   ├── services/        # Business logic
│   │   ├── api/             # API routes
│   │   └── utils/           # Helpers
│   ├── tests/
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── types/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   ├── ingest_history.py
│   ├── ingest_products.py
│   └── create_mock_data.py
├── docs/
│   ├── 00_OVERVIEW.md
│   ├── 01_PHASE_1_SETUP.md
│   ├── 02_PHASE_2_INGESTION.md
│   ├── 03_PHASE_3_RAG.md
│   ├── 04_PHASE_4_BACKEND.md
│   ├── 05_PHASE_5_FRONTEND.md
│   └── 06_PHASE_6_TESTING.md
└── README.md
```

---

## 🧪 Testing Strategy

### Phase-by-Phase Testing
Each phase must pass its test criteria before moving to the next:

1. **Phase 1:** Server starts, basic endpoint responds
2. **Phase 2:** Data ingestion completes, structured data validated
3. **Phase 3:** Vector search returns relevant results
4. **Phase 4:** API endpoints return correct responses
5. **Phase 5:** Frontend displays data, chat works
6. **Phase 6:** End-to-end user flows work

### Test Types
- **Unit Tests:** Individual functions/methods
- **Integration Tests:** Service interactions
- **E2E Tests:** Complete user workflows
- **Manual Testing:** UI/UX validation

---

## 🎯 Success Metrics

### Functionality
- ✅ Chat answers questions accurately using browsing history
- ✅ Recommendations are relevant and diverse
- ✅ Streaming responses work smoothly
- ✅ Data ingestion handles errors gracefully

### Performance
- ✅ Query response time < 3 seconds
- ✅ Embedding generation < 1 second per batch
- ✅ UI feels responsive (streaming updates)

### Quality
- ✅ Clean, readable code
- ✅ Comprehensive documentation
- ✅ No critical bugs in happy path
- ✅ Loom walkthrough is clear and concise

---

## 📚 Key Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [OpenRouter API](https://openrouter.ai/docs)
- [Pinecone Docs](https://docs.pinecone.io/)
- [Firecrawl API](https://docs.firecrawl.dev/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [React TypeScript](https://react-typescript-cheatsheet.netlify.app/)

---

## ⏱ Implementation Timeline

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 1 | 1 hour | Working dev environment |
| 2 | 2 hours | Ingested data in Pinecone |
| 3 | 1.5 hours | RAG queries return results |
| 4 | 1 hour | API endpoints functional |
| 5 | 1.5 hours | Interactive chat UI |
| 6 | 1 hour | Tests pass, docs complete |

**Total:** ~8 hours (with buffer)

---

## 🚀 Next Steps

1. Review this overview document
2. Proceed to Phase 1 design document
3. Begin implementation phase-by-phase
4. Test after each phase
5. Iterate as needed
