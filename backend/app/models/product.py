from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import uuid


class ProductCategory(str, Enum):
    """Product category classification"""
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
    image_url: Optional[str] = None
    product_url: str
    store_name: str
    
    # Additional fields
    tags: List[str] = Field(default_factory=list)
    variants: List[str] = Field(default_factory=list)
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
    handle: Optional[str] = None
    tags: Optional[List[str]] = None  # Can be list from some Shopify stores
    variants: List[dict] = Field(default_factory=list)
    images: List[dict] = Field(default_factory=list)
