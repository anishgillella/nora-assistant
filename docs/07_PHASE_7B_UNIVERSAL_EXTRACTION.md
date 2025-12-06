# Phase 7B: Universal Activity Extraction

## 🎯 Objective

Expand data ingestion beyond e-commerce to capture **all browsing behavior** (YouTube, LinkedIn, News, Travel, etc.) and extract rich behavioral attributes for smarter recommendations.

---

## 🧠 Key Insight

Your browsing history tells a story:
- Reading about "marathon training" → Likely needs running shoes
- Viewing LinkedIn jobs at Stripe → May want office equipment
- Researching Zillow listings → Probably needs furniture

This phase bridges **content consumption** to **product recommendations**.

---

## 📊 Unified Schema

### Activity Types
| Type | Examples |
|------|----------|
| `product` | Amazon, Nike, Shopify stores |
| `content` | YouTube, Medium, News sites |
| `social` | LinkedIn, Twitter, Facebook |
| `search` | Google, Bing search results |
| `utility` | Email, Calendar (low signal) |

### BrowsingActivity Model
```python
class ActivityType(str, Enum):
    PRODUCT = "product"
    CONTENT = "content"
    SOCIAL = "social"
    SEARCH = "search"
    UTILITY = "utility"

class BrowsingActivity(BaseModel):
    # Core fields
    id: str
    url: str
    title: str
    domain: str
    visit_time: str                    # ISO format for display
    visit_timestamp: int               # Epoch for filtering
    activity_type: ActivityType
    
    # Universal extraction
    category: str                      # "Shoes" or "Running" or "Jobs"
    topics: List[str]                  # ["Marathon Training", "Fitness"]
    context: List[str]                 # Life signals: ["Job Hunting", "Moving"]
    vibe: List[str]                    # ["Professional", "Aspirational"]
    inferred_needs: List[str]          # ["Running Shoes", "Laptop Stand"]
    semantic_summary: str              # Embedding-optimized text
    
    # Product-specific (nullable)
    price: Optional[float] = None
    brand: Optional[str] = None
    materials: Optional[List[str]] = None
    occasion: Optional[List[str]] = None
```

---

## 🔍 Embedding Strategy

We embed the **`semantic_summary`** field, which is LLM-generated to be search-optimized:

```
"Job hunter researching senior software engineer roles at Stripe. 
Professional mindset, ambitious, preparing for career change. 
Inferred product needs: laptop stand, ergonomic chair, interview prep."
```

This single dense string connects behavior to products.

---

## ⏱ Time-Based Filtering

### Storage
```json
{
  "visit_time": "2024-12-05T10:30:00",
  "visit_timestamp": 1733414400
}
```

### Query
```python
# "Show me my browsing from the last month"
one_month_ago = int(time.time()) - (30 * 24 * 60 * 60)
filter = {"visit_timestamp": {"$gte": one_month_ago}}
```

Pinecone supports numeric filtering with `$gt`, `$gte`, `$lt`, `$lte`.

---

## 🖥 Frontend Table (Unified View)

| Column | Products | Content | Social |
|--------|----------|---------|--------|
| **Type** | 🛒 | 📺 | 💼 |
| **Title** | "Air Jordan 1" | "Marathon Guide" | "SWE at Stripe" |
| **Source** | nike.com | youtube.com | linkedin.com |
| **Category** | Shoes | Fitness | Engineering |
| **Context** | Casual | Training | Job Hunting |
| **Vibe** | Vintage | Inspirational | Ambitious |
| **Price** | $180 | — | — |

---

## 🔧 Implementation Checklist

- [ ] Update `BrowsingActivity` Pydantic model
- [ ] Add `extract_activity()` to GeminiStructurer
- [ ] Store `visit_timestamp` in Pinecone metadata
- [ ] Add time filter to `search_browsing()`
- [ ] Create 50+ diverse seed entries
- [ ] Update DataExplorer table columns
- [ ] Parse time phrases in RAG Engine

---

## 🧪 Testing

### Manual Tests
1. Ingest real Chrome history (with e-commerce filter disabled)
2. Verify YouTube and LinkedIn entries appear in Data Explorer
3. Query "What was I researching last week?" → Should filter by time
4. Query "Recommend products for my marathon training" → Should connect content to products

### Seed Data Categories
- 🛒 E-commerce: Nike, Apple, Patagonia
- 📺 Content: YouTube tutorials, Medium articles
- 💼 Social: LinkedIn jobs, Twitter posts
- ✈️ Travel: Airbnb, Google Flights
- 📚 Learning: Udemy, Coursera
