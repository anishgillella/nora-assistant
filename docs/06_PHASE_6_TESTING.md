# Phase 6: Integration & Testing

## 🎯 Objectives

1. End-to-End System Testing
2. Performance Optimization
3. Documentation Finalization
4. Loom Walkthrough Recording

---

## 🧪 End-to-End Test Plan

### 1. Data Ingestion Flow
- **Action:** Click "Ingest History"
- **Verify:**
  - Backend logs show Chrome extraction
  - Firecrawl scrapes content
  - Pinecone index count increases
  - Frontend stats update

### 2. Chat Flow (Memory)
- **Action:** Ask "What shoes did I look at yesterday?"
- **Verify:**
  - RAG retrieves correct history items
  - LLM response cites specific products
  - Sources are displayed in UI

### 3. Chat Flow (Recommendations)
- **Action:** Ask "Recommend me some running shoes based on my history"
- **Verify:**
  - RAG retrieves products from "products" namespace
  - LLM explains reasoning
  - Product cards appear in chat

---

## 🚀 Performance Tuning

- **Latency:** Ensure chat response starts < 1s
- **Caching:** Cache repeated queries or embeddings
- **Error Handling:** Graceful fallbacks if Firecrawl/OpenRouter fails

---

## 📝 Documentation Checklist

- [ ] **README.md:**
  - Setup instructions (env vars, install steps)
  - Architecture diagram
  - Tech stack justification
- [ ] **Code Comments:** Ensure complex logic is explained

---

## 🎥 Loom Walkthrough Script

1. **Intro (1 min):** Who I am, what this is (Nora take-home).
2. **Demo - Ingestion (2 min):** Show "Ingest" button, explain Chrome extraction + Firecrawl.
3. **Demo - Chat (3 min):**
   - Ask about history ("What did I browse?")
   - Ask for recommendation ("Find alternatives")
   - Show streaming & sources.
4. **Code Walkthrough (3 min):**
   - Show RAG pipeline (Pinecone + Embeddings)
   - Show Gemini structuring logic
   - Show React components.
5. **Closing (1 min):** Future improvements, thanks.
