"""
Gemini Data Structurer

Uses Gemini 2.5 Flash via OpenRouter to extract structured data from raw content.
"""
from openai import OpenAI
from app.utils.config import get_settings
from app.utils.token_utils import get_tracker, TokenTracker
from app.models.browsing import ProductInfo, ShoppingIntent
from typing import Optional
import json


class GeminiStructurer:
    """Use Gemini 2.5 Flash via OpenRouter to structure raw data"""
    
    def __init__(self, tracker: TokenTracker = None):
        settings = get_settings()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key
        )
        self.model = settings.structuring_model
        self.tracker = tracker or get_tracker()
    
    def extract_product_from_page(
        self, 
        url: str,
        title: str, 
        content: str
    ) -> Optional[ProductInfo]:
        """
        Extract product information from page content using Gemini
        
        Args:
            url: Page URL
            title: Page title
            content: Page content (markdown or text)
        
        Returns:
            ProductInfo if extraction successful, None otherwise
        """
        # Limit content to reduce tokens/cost
        content_trimmed = content[:1500] if content else ""
        
        prompt = f"""Extract product information from this e-commerce page.
Return ONLY valid JSON matching this exact schema (no markdown, no explanation):
{{
  "name": "product name",
  "price": 99.99,
  "currency": "USD",
  "category": "shoes|clothing|accessories|fitness|outdoor|eyewear|home|electronics|other",
  "brand": "brand name or null",
  "image_url": "url or null",
  "description": "brief description (50 words max)",
  "availability": "in_stock|out_of_stock|null"
}}

If this is not a product page, return: {{"name": null}}

URL: {url}
Title: {title}

Content:
{content_trimmed}

JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
            self.tracker.add_from_response(response)
            
            json_str = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1])
            
            data = json.loads(json_str)
            
            # Check if extraction was successful
            if data.get("name") is None:
                return None
            
            return ProductInfo(
                name=data.get("name", "Unknown"),
                price=data.get("price"),
                currency=data.get("currency", "USD"),
                category=data.get("category"),
                brand=data.get("brand"),
                image_url=data.get("image_url"),
                description=data.get("description"),
                availability=data.get("availability")
            )
        except Exception as e:
            print(f"❌ Gemini extraction error: {e}")
            return None
    
    def classify_intent(self, url: str, title: str, content: str = "") -> ShoppingIntent:
        """
        Classify user's shopping intent for a page visit
        
        Args:
            url: Page URL
            title: Page title
            content: Optional page content
        
        Returns:
            ShoppingIntent enum value
        """
        content_trimmed = content[:500] if content else ""
        
        prompt = f"""Classify the shopping intent for this page visit.
Return ONLY one of these words: browsing, purchasing, researching, comparing

URL: {url}
Title: {title}
Content: {content_trimmed}

Intent:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            self.tracker.add_from_response(response)
            
            intent = response.choices[0].message.content.strip().lower()
            
            # Map to enum, default to browsing
            intent_map = {
                "browsing": ShoppingIntent.BROWSING,
                "purchasing": ShoppingIntent.PURCHASING,
                "researching": ShoppingIntent.RESEARCHING,
                "comparing": ShoppingIntent.COMPARING
            }
            
            return intent_map.get(intent, ShoppingIntent.BROWSING)
        except Exception as e:
            print(f"❌ Intent classification error: {e}")
            return ShoppingIntent.BROWSING
    
    def summarize_shopping_history(self, products: list[dict]) -> str:
        """
        Generate a brief summary of shopping history
        
        Args:
            products: List of product dicts with name, category, price, brand
        
        Returns:
            Natural language summary
        """
        if not products:
            return "No shopping history available."
        
        # Format products for prompt
        product_list = "\n".join([
            f"- {p.get('name', 'Unknown')} ({p.get('category', 'other')}) - ${p.get('price', 0)}"
            for p in products[:20]  # Limit to 20 for token efficiency
        ])
        
        prompt = f"""Summarize this user's shopping interests based on their browsing history.
Be concise (2-3 sentences). Focus on: categories, brands, price ranges, and patterns.

Products viewed:
{product_list}

Summary:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=100
            )
            self.tracker.add_from_response(response)
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Summary error: {e}")
            return "Unable to generate summary."
