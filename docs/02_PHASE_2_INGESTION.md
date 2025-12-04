# Phase 2: Data Ingestion Pipeline

## 🎯 Objectives

1. Extract browsing history from Chrome SQLite database
2. Scrape content from visited URLs using Firecrawl
3. Scrape ~100 products from Shopify stores
4. Use Gemini 2.5 Flash to structure raw data into Pydantic models
5. Generate mock shopping data for testing
6. Validate all ingestion pipelines

---

## 📊 Data Flow

```
Chrome History DB → Raw URLs → Firecrawl → Raw Content → 
  Gemini Structuring → Pydantic Models → Ready for Embedding

Shopify Stores → /products.json → Raw JSON → 
  Gemini Structuring → Pydantic Models → Ready for Embedding

Mock Generator → Realistic Shopping Patterns → Pydantic Models
```

---

## 🏗 Pydantic Models

### File: `backend/app/models/browsing.py`

```python
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid

class ShoppingIntent(str, Enum):
    BROWSING = "browsing"
    PURCHASING = "purchasing"
    RESEARCHING = "researching"
    COMPARING = "comparing"

class ProductInfo(BaseModel):
    """Structured product information extracted from a page"""
    name: str
    price: Optional[float] = None
    currency: str = "USD"
    category: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    description: Optional[str] = None
    availability: Optional[str] = None

class BrowsingHistoryEntry(BaseModel):
    """Browsing history entry with extracted signals"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: HttpUrl
    title: str
    visit_time: datetime
    visit_count: int = 1
    
    # Extracted signals
    product: Optional[ProductInfo] = None
    intent: ShoppingIntent = ShoppingIntent.BROWSING
    page_content: Optional[str] = None  # Markdown from Firecrawl
    
    # Metadata
    domain: str
    is_ecommerce: bool = False
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class ChromeHistoryRaw(BaseModel):
    """Raw data from Chrome SQLite DB"""
    id: int
    url: str
    title: Optional[str] = None
    last_visit_time: int  # Chrome timestamp
    visit_count: int
```

### File: `backend/app/models/product.py`

```python
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from enum import Enum
import uuid

class ProductCategory(str, Enum):
    SHOES = "shoes"
    CLOTHING = "clothing"
    ACCESSORIES = "accessories"
    FITNESS = "fitness"
    OUTDOOR = "outdoor"
    EYEWEAR = "eyewear"
    HOME = "home"
    ELECTRONICS = "electronics"
    OTHER = "other"

class Product(BaseModel):
    """Structured product from Shopify or other sources"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    currency: str = "USD"
    category: ProductCategory
    brand: str
    
    description: str
    image_url: Optional[HttpUrl] = None
    product_url: HttpUrl
    store_name: str
    
    # Additional fields
    tags: List[str] = Field(default_factory=list)
    variants: List[str] = Field(default_factory=list)  # e.g., ["Small", "Medium", "Large"]
    availability: str = "in_stock"
    
    # Metadata
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class ShopifyProductRaw(BaseModel):
    """Raw product data from Shopify API"""
    id: int
    title: str
    body_html: Optional[str] = None
    vendor: str
    product_type: Optional[str] = None
    tags: Optional[str] = None
    variants: List[dict]
    images: List[dict]
```

---

## 🔧 Implementation Strategy

### 1. Chrome History Extractor (`chrome_extractor.py`)
- Locate Chrome SQLite DB at `~/Library/Application Support/Google/Chrome/Default/History`
- Copy to temp location to avoid locks
- Query `urls` table for recent visits
- Filter by e-commerce domains

### 2. Firecrawl Scraper (`firecrawl_scraper.py`)
- Use `https://api.firecrawl.dev/v1/scrape`
- Extract markdown content
- Handle rate limits and errors

### 3. Shopify Scraper (`shopify_scraper.py`)
- Iterate through list of Shopify domains
- Fetch `https://{domain}/products.json`
- Parse raw JSON into `ShopifyProductRaw`
- Convert to structured `Product` model

### 4. Gemini Structurer (`gemini_structurer.py`)
- Use `google/gemini-2.0-flash-exp:free` via OpenRouter
- Prompt to extract JSON from markdown
- Validate against Pydantic models

### 5. Mock Data Generator (`mock_data.py`)
- Create realistic browsing history patterns (e.g., "Sneakerhead", "Fashionista")
- Generate consistent product data

---

## 🧪 Testing

Run `backend/tests/test_ingestion.py` to verify:
1. Chrome history can be read
2. Firecrawl returns content
3. Shopify scraper fetches products
4. Gemini correctly extracts structured data
5. Mock data is generated correctly
