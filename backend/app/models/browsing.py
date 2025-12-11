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
    category: List[str] = Field(default_factory=list, description="Product categories e.g. shoes, clothing, fitness")
    brand: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    availability: Optional[str] = None
    
    # Rich Attributes
    visual_characteristics: List[str] = Field(default_factory=list, description="e.g. Minimalist, Rugged, Retro")
    materials: List[str] = Field(default_factory=list, description="e.g. Leather, Wool, Polyester")
    occasion: List[str] = Field(default_factory=list, description="e.g. Office, Gym, Casual")
    gender_target: Optional[str] = Field(default=None, description="Men, Women, Unisex, Kids")
    season: List[str] = Field(default_factory=list, description="e.g. Summer, Winter, All-Season")
    sustainability: List[str] = Field(default_factory=list, description="e.g. Recycled, Organic, Fair Trade")
    color_family: List[str] = Field(default_factory=list, description="e.g. Earth Tones, Pastels, Neon")


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


class ActivityType(str, Enum):
    """Type of browsing activity for universal extraction"""
    PRODUCT = "product"      # E-commerce product pages
    CONTENT = "content"      # YouTube, Blogs, News
    SOCIAL = "social"        # LinkedIn, Twitter, Facebook
    SEARCH = "search"        # Google, Bing search results
    UTILITY = "utility"      # Email, Calendar, Banking


class BrowsingActivity(BaseModel):
    """Universal browsing activity with rich behavioral extraction.
    
    Supports any website type (e-commerce, content, social, etc.)
    and extracts signals for product recommendation.
    """
    # Core fields
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    title: str
    domain: str
    visit_time: str  # ISO format for display
    visit_timestamp: int  # Epoch for Pinecone filtering
    activity_type: ActivityType = ActivityType.CONTENT
    
    # Universal extraction (filled for all activity types)
    category: str = ""  # "Shoes" or "Running" or "Jobs"
    topics: List[str] = Field(default_factory=list, description="Main themes: Marathon Training, AI, Travel")
    context: List[str] = Field(default_factory=list, description="Life signals: Job Hunting, Moving, Vacation Planning")
    vibe: List[str] = Field(default_factory=list, description="Mood/aesthetic: Professional, Adventurous, Minimalist")
    inferred_needs: List[str] = Field(default_factory=list, description="Product categories user likely needs")
    semantic_summary: str = ""  # Embedding-optimized text for vector search
    
    # Product-specific (nullable, only filled for product activity_type)
    price: Optional[float] = None
    brand: Optional[str] = None
    materials: Optional[List[str]] = None
    occasion: Optional[List[str]] = None
    visual_characteristics: Optional[List[str]] = None
    
    class Config:
        use_enum_values = True

