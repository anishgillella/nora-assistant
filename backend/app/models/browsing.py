from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class ShoppingIntent(str, Enum):
    """Classification of shopping intent"""
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
    image_url: Optional[str] = None
    description: Optional[str] = None
    availability: Optional[str] = None


class BrowsingHistoryEntry(BaseModel):
    """Browsing history entry with extracted signals"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
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
    last_visit_time: int  # Chrome timestamp (microseconds since 1601)
    visit_count: int
