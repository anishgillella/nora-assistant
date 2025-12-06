
import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv("backend/.env")

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.gemini_structurer import GeminiStructurer

def test_rich_extraction():
    structurer = GeminiStructurer()
    
    # Mock product page content
    url = "https://example.com/boots"
    title = "Rugged Leather Hiking Boots"
    content = """
    The TrailMaster 3000 is designed for the serious outdoorsman. 
    Crafted from premium full-grain leather with a waterproof GORE-TEX lining.
    Perfect for heavy hiking in muddy or snowy conditions. 
    Features a minimalist, earth-tone design that looks great on the trail or in the cabin.
    Sustainably sourced and fair-trade certified.
    Targeted at men who demand durability.
    """
    
    print(f"🧪 Testing extraction for: {title}")
    result = structurer.extract_product_from_page(url, title, content)
    
    if result:
        print("\n✅ Extraction Success!")
        print(f"Name: {result.name}")
        print(f"Description: {result.description[:100]}...")  
        print(f"Category: {result.category}")
        print(f"Materials: {result.materials}")
        print(f"Visual Style: {result.visual_characteristics}")
        print(f"Occasion: {result.occasion}")
        print(f"Sustainability: {result.sustainability}")
        print(f"Gender: {result.gender_target}")
        
        # Verify strict checks
        assert "Leather" in result.materials or "GORE-TEX" in result.materials
        assert "Hiking" in result.occasion or "Outdoor" in result.occasion  
        # Note: 'Outdoor' might not be in the prompt list explicitly, checking for Hiking/Cabin implies Outdoor context
        
    else:
        print("❌ Extraction Failed")

if __name__ == "__main__":
    test_rich_extraction()
