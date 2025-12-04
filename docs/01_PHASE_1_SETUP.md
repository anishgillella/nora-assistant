# Phase 1: Project Setup & Infrastructure

## 🎯 Objectives

1. Set up Python backend with FastAPI
2. Set up React + TypeScript frontend with Vite
3. Configure environment variables and dependencies
4. Verify basic client-server communication
5. Establish development workflow

---

## 📋 Prerequisites

- Python 3.11+ installed
- Node.js 18+ installed
- Git initialized
- API keys ready (.env file)

---

## 🏗 Directory Structure to Create

```
nora-assistant/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── services/
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── health.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── config.py
│   ├── tests/
│   │   └── __init__.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   └── HealthCheck.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── types/
│   │       └── index.ts
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
├── scripts/
├── docs/
├── .env
├── .gitignore
└── README.md
```

---

## 🔧 Backend Setup

### 1. Install Dependencies

**requirements.txt:**
```txt
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-dotenv==1.0.0

# CORS
fastapi-cors==0.0.6

# Database
sqlalchemy==2.0.25
sqlite-utils==3.36

# Data Validation
pydantic==2.5.3
pydantic-settings==2.1.0

# HTTP Client
httpx==0.26.0
requests==2.31.0

# LLM & Embeddings
openai==1.10.0

# Vector Database
pinecone-client==3.0.2

# Web Scraping
playwright==1.41.0
beautifulsoup4==4.12.3
lxml==5.1.0

# Utilities
python-multipart==0.0.6
```

**Install:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration (backend/app/utils/config.py)

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Keys
    openrouter_api_key: str
    openai_api_key: str
    pinecone_api_key: str
    firecrawl_api_key: str
    
    # Pinecone Config
    pinecone_environment: str = "us-east-1-aws"
    pinecone_index_name: str = "nora-browsing-memory"
    
    # Database
    database_url: str = "sqlite:///./nora.db"
    
    # Server
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    
    # Models
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "openai/gpt-4o-mini"
    structuring_model: str = "google/gemini-2.0-flash-exp:free"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 3. Main Application (backend/app/main.py)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.config import get_settings
from app.api import health

settings = get_settings()

app = FastAPI(
    title="Nora Browsing Memory API",
    description="Personal shopping memory with RAG-powered recommendations",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routes
app.include_router(health.router, prefix="/api", tags=["Health"])

@app.on_event("startup")
async def startup_event():
    print("🚀 Nora API starting up...")
    print(f"📍 Frontend URL: {settings.frontend_url}")
    print(f"🔌 Backend Port: {settings.backend_port}")

@app.on_event("shutdown")
async def shutdown_event():
    print("👋 Nora API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True
    )
```

### 4. Health Check Endpoint (backend/app/api/health.py)

```python
from fastapi import APIRouter, Depends
from app.utils.config import Settings, get_settings
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "nora-browsing-memory",
        "version": "1.0.0",
        "config": {
            "pinecone_index": settings.pinecone_index_name,
            "embedding_model": settings.embedding_model,
            "chat_model": settings.chat_model
        }
    }
```

---

## 🎨 Frontend Setup

### 1. Initialize Vite + React + TypeScript

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 2. Install Dependencies

```bash
npm install axios
npm install -D @types/node
```

**Additional (optional for styling):**
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 3. API Service (frontend/src/services/api.ts)

```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health Check
export const checkHealth = async () => {
  const response = await api.get('/api/health');
  return response.data;
};
```

### 4. Health Check Component (frontend/src/components/HealthCheck.tsx)

```typescript
import { useEffect, useState } from 'react';
import { checkHealth } from '../services/api';

interface HealthStatus {
  status: string;
  timestamp: string;
  service: string;
  version: string;
}

export const HealthCheck = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth(data);
      } catch (err) {
        setError('Failed to connect to backend');
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
  }, []);

  if (loading) return <div>Checking backend connection...</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div style={{ padding: '20px', border: '1px solid green' }}>
      <h2>✅ Backend Connected</h2>
      <p><strong>Service:</strong> {health?.service}</p>
      <p><strong>Status:</strong> {health?.status}</p>
      <p><strong>Version:</strong> {health?.version}</p>
      <p><strong>Timestamp:</strong> {health?.timestamp}</p>
    </div>
  );
};
```

### 5. Main App (frontend/src/App.tsx)

```typescript
import { HealthCheck } from './components/HealthCheck';

function App() {
  return (
    <div style={{ padding: '40px', fontFamily: 'system-ui' }}>
      <h1>Nora - Browsing Memory Prototype</h1>
      <p>Phase 1: Project Setup ✅</p>
      <HealthCheck />
    </div>
  );
}

export default App;
```

### 6. Environment Variables (frontend/.env.example)

```bash
VITE_API_URL=http://localhost:8000
```

---

## 🔐 Environment Setup

### Backend .env

```bash
# LLM & Embeddings
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENAI_API_KEY=sk-xxxxx

# Vector Database
PINECONE_API_KEY=xxxxx
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=nora-browsing-memory

# Scraping
FIRECRAWL_API_KEY=xxxxx

# Database
DATABASE_URL=sqlite:///./nora.db

# Server
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
```

### Frontend .env

```bash
VITE_API_URL=http://localhost:8000
```

---

## 🧪 Testing Phase 1

### Test Checklist

- [ ] **Backend starts successfully**
  ```bash
  cd backend
  source venv/bin/activate
  python -m app.main
  ```
  Expected: Server running on http://0.0.0.0:8000

- [ ] **Health endpoint responds**
  ```bash
  curl http://localhost:8000/api/health
  ```
  Expected: JSON with `status: "healthy"`

- [ ] **Frontend starts successfully**
  ```bash
  cd frontend
  npm run dev
  ```
  Expected: Vite server running on http://localhost:5173

- [ ] **Frontend connects to backend**
  - Open http://localhost:5173
  - Expected: Green "Backend Connected" message with service info

- [ ] **CORS is configured correctly**
  - Check browser console for CORS errors
  - Expected: No CORS errors

- [ ] **Environment variables load correctly**
  - Backend prints config on startup
  - Frontend can make API calls
  - Expected: No missing env var errors

---

## ✅ Success Criteria

### Must Have
✅ Backend server starts without errors  
✅ Frontend dev server starts without errors  
✅ `/api/health` endpoint returns 200 OK  
✅ Frontend successfully calls backend  
✅ No CORS errors in browser console  
✅ All environment variables load correctly  

### Nice to Have
✅ Auto-reload works for both frontend and backend  
✅ TypeScript compilation has no errors  
✅ Console logs show clear startup messages  

---

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Kill process on port 8000
   lsof -ti:8000 | xargs kill -9
   ```

2. **Python venv not activated**
   ```bash
   source backend/venv/bin/activate
   ```

3. **CORS errors**
   - Check `FRONTEND_URL` in backend .env
   - Verify CORS middleware in `main.py`

4. **Module not found**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

5. **TypeScript errors**
   ```bash
   # Clear cache and reinstall
   rm -rf node_modules package-lock.json
   npm install
   ```

---

## 📝 Deliverables

- [x] Backend FastAPI application running
- [x] Frontend React + TypeScript application running
- [x] Health check endpoint functional
- [x] Client-server communication verified
- [x] Environment configuration complete

---

## ➡️ Next Phase

Once Phase 1 tests pass, proceed to **[Phase 2: Data Ingestion](./02_PHASE_2_INGESTION.md)**
