"""
Gemini Data Structurer

Uses Gemini 2.5 Flash via OpenRouter to extract structured data from raw content.
"""
from openai import AsyncOpenAI
from app.utils.config import get_settings
from app.utils.token_utils import get_tracker, TokenTracker
from app.models.browsing import ProductInfo, ShoppingIntent
from typing import Optional
import json


class GeminiStructurer:
    """Use Gemini 2.5 Flash via OpenRouter to structure raw data"""
    
    def __init__(self, tracker: TokenTracker = None):
        settings = get_settings()
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key
        )
        self.model = settings.structuring_model
        self.tracker = tracker or get_tracker()
    
    async def extract_product_from_page(
        self, 
        url: str,
        title: str, 
        content: str
    ) -> Optional[ProductInfo]:
        """
        Extract product information from page content using Gemini (Async)
        
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
  "description": "detailed description focusing on materials, style, usage, and key features (optimized for search)",
  "availability": "in_stock|out_of_stock|null",
  "visual_characteristics": ["Minimalist", "Rugged", "Retro", "Industrial"],
  "materials": ["Leather", "Wool", "GORE-TEX", "Cotton"],
  "occasion": ["Office", "Gym", "Hiking", "Date Night", "Casual"],
  "gender_target": "Men|Women|Unisex|Kids|null",
  "season": ["Summer", "Winter", "All-Season"],
  "sustainability": ["Recycled", "Vegan", "Fair Trade"],
  "color_family": ["Earth Tones", "Pastels", "Neon", "Monochrome"]
}}

If this is not a product page, return: {{"name": null}}

URL: {url}
Title: {title}

Content:
{content_trimmed}

JSON:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            self.tracker.add_from_response(response)
            
            # Parse JSON response
            content = response.choices[0].message.content
            if not content:
                print(f"❌ Gemini extraction error: Empty response for {url}")
                return None
            
            import json
            try:
                # Strip markdown code blocks if present
                if "```" in content:
                    content = content.replace("```json", "").replace("```", "").strip()
                
                data = json.loads(content)
                
                # Handle null currency
                if not data.get("currency"):
                    data["currency"] = "USD"
                    
                return ProductInfo(**data)
            except json.JSONDecodeError as e:
                print(f"❌ Gemini extraction error: {e} for {url}. Content start: {content[:50]}")
                return None
            except Exception as e:
                print(f"❌ Validation error: {e} for {url}")
                return None

        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            return None
    
    async def classify_intent(self, url: str, title: str, content: str = "") -> ShoppingIntent:
        """
        Classify user's shopping intent for a page visit (Async)
        
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
            response = await self.client.chat.completions.create(
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
    
    async def summarize_shopping_history(self, products: list[dict]) -> str:
        """
        Generate a brief summary of shopping history (Async)
        
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
            response = await self.client.chat.completions.create(
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

    async def extract_activity(
        self,
        url: str,
        title: str,
        content: str = ""
    ) -> Optional[dict]:
        """
        Extract universal activity data from ANY website type (Async)
        
        Supports: e-commerce, YouTube, LinkedIn, news, travel, etc.
        Returns a dict compatible with BrowsingActivity model.
        """
        from app.models.browsing import ActivityType
        
        content_trimmed = content[:1500] if content else ""
        
        prompt = f"""Analyze this webpage and extract behavioral signals for a recommendation system.
Return ONLY valid JSON matching this schema (no markdown):
{{
  "activity_type": "product|content|social|search|utility",
  "category": "main category (e.g. Shoes, Running, Jobs, Travel, Finance)",
  "topics": ["topic1", "topic2"],
  "context": ["life signals like Job Hunting, Moving, Vacation Planning, Upskilling"],
  "vibe": ["mood/aesthetic: Professional, Adventurous, Minimalist, Aspirational"],
  "inferred_needs": ["product categories user might need based on this activity"],
  "semantic_summary": "A detailed 2-3 sentence description of the product, content, or webpage. Focus on what the item IS - its key features, benefits, specifications, and value proposition. Do NOT analyze the user or their intentions. For products: describe what it is, materials, key features, and ideal use cases. For content: describe what the video/article covers and key takeaways.",
  "price": null,
  "brand": "brand name if product page, or content creator/company name",
  "materials": null,
  "occasion": null,
  "visual_characteristics": null
}}

Activity Type Guide:
- product: E-commerce product pages (Amazon, Nike, Shopify stores)
- content: Videos, articles, blogs (YouTube, Medium, News)
- social: Professional/social networks (LinkedIn, Twitter)
- search: Search results pages (Google, Bing)
- utility: Email, calendar, banking (low signal)

For PRODUCT pages, also fill: price, materials, occasion, visual_characteristics
For CONTENT/SOCIAL pages, focus on: topics, context, vibe, inferred_needs

URL: {url}
Title: {title}

Content:
{content_trimmed}

JSON:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=600
            )
            self.tracker.add_from_response(response)
            
            result = response.choices[0].message.content
            if not result:
                print(f"❌ Activity extraction error: Empty response for {url}")
                return None
            
            try:
                # Strip markdown if present
                if "```" in result:
                    result = result.replace("```json", "").replace("```", "").strip()
                
                data = json.loads(result)
                
                # Ensure required fields have defaults
                data.setdefault("activity_type", "content")
                data.setdefault("category", "")
                data.setdefault("topics", [])
                data.setdefault("context", [])
                data.setdefault("vibe", [])
                data.setdefault("inferred_needs", [])
                data.setdefault("semantic_summary", f"Visited {url}")
                
                return data
            except json.JSONDecodeError as e:
                print(f"❌ Activity extraction JSON error: {e} for {url}")
                return None
            except Exception as e:
                print(f"❌ Activity extraction validation error: {e} for {url}")
                return None
                
        except Exception as e:
            print(f"❌ Activity extraction API error: {e}")
            return None

