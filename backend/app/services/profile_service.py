
import json
import logging
from typing import Optional
from openai import OpenAI
from app.utils.config import get_settings
from app.models.profile import UserProfile
from app.utils.token_utils import get_tracker

logger = logging.getLogger(__name__)

class ProfileService:
    """Service to extract user profiles from text using LLM"""
    
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key
        )
        self.model = settings.chat_model
        self.tracker = get_tracker()
        
    def extract_profile(self, text: str, current_profile: Optional[UserProfile] = None) -> UserProfile:
        """
        Extract structured profile attributes from free-form text.
        Merges with current profile if provided.
        """
        system_prompt = """You are an expert personal shopper. Your goal is to build a structured 'Taste Profile' for a user based on their self-description.
        
        You MUST respond with valid JSON perfectly matching this schema:
        {
            "visual_style": ["list", "of", "styles"],
            "brand_affinity": ["list", "of", "brands"],
            "dislikes": ["list", "of", "dislikes"],
            "price_sensitivity": "low" | "medium" | "high" | "luxury",
            "context": ["list", "of", "contexts"],
            "colors": ["list", "of", "colors"]
        }
        
        Rules:
        1. Extract specific keywords from the user text.
        2. Infer price_sensitivity from context (e.g. "student" -> low/medium, "luxury" -> luxury).
        3. If a field is not mentioned, return an empty list [].
        4. "visual_style" examples: minimalist, vintage, streetwear, formal, rugged.
        5. "context" examples: hiking, office, gym, travel.
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if current_profile:
            messages.append({
                "role": "system", 
                "content": f"Current Profile (Merge with this): {current_profile.model_dump_json()}"
            })
            
        messages.append({"role": "user", "content": f"User Input: {text}"})
        
        try:
            logger.info(f"🧠 Extracting profile from text: '{text}'")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1, 
                max_tokens=500
            )
            self.tracker.add_from_response(response)
            
            content = response.choices[0].message.content
            logger.info(f"📝 Raw LLM Response: {content}")
            
            # Clean markdown if present
            if "```" in content:
                content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            
            # Convert to Pydantic model
            profile = UserProfile(**data)
            logger.info(f"✅ Extracted profile: {profile.model_dump_json()}")
            return profile
            
        except Exception as e:
            logger.error(f"❌ Profile extraction failed: {e}")
            # Return empty or current profile on failure
            return current_profile or UserProfile()
