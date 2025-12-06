
from pydantic import BaseModel, Field
from typing import List, Optional

class UserProfile(BaseModel):
    """Structured user taste profile extracted from natural language"""
    visual_style: List[str] = Field(default_factory=list, description="Visual style preferences (e.g., minimalist, vintage, streetwear)")
    brand_affinity: List[str] = Field(default_factory=list, description="Brands the user explicitly likes or shows affinity for")
    dislikes: List[str] = Field(default_factory=list, description="Things the user explicitly dislikes (colors, materials, brands)")
    price_sensitivity: str = Field(default="medium", description="Budget level: low, medium, high, luxury")
    context: List[str] = Field(default_factory=list, description="Life context (e.g., student, office worker, hiker)")
    colors: List[str] = Field(default_factory=list, description="Preferred colors")
