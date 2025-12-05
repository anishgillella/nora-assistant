"""
Phase 2 Ingestion Test Script

Tests all data ingestion services:
1. Chrome history extraction
2. Shopify product scraping  
3. Firecrawl content scraping
4. Gemini data structuring
5. Mock data generation

Run with: python -m tests.test_ingestion
"""
import asyncio
from datetime import datetime


def test_mock_data():
    """Test mock data generation (no API calls)"""
    print("\n🧪 Testing Mock Data Generation...")
    try:
        from app.utils.mock_data import MockDataGenerator
        
        # Generate browsing history
        history = MockDataGenerator.generate_browsing_history(
            pattern="sneaker_enthusiast",
            num_entries=5
        )
        print(f"   ✅ Generated {len(history)} browsing history entries")
        for entry in history[:2]:
            print(f"      - {entry.product.name}: ${entry.product.price}")
        
        # Generate products
        products = MockDataGenerator.generate_products(num_products=10)
        print(f"   ✅ Generated {len(products)} products")
        for p in products[:2]:
            print(f"      - {p.name}: ${p.price} ({p.category})")
        
        return True
    except Exception as e:
        print(f"   ❌ Mock data error: {e}")
        return False


def test_chrome_extraction():
    """Test Chrome history extraction"""
    print("\n🧪 Testing Chrome History Extraction...")
    try:
        from app.services.chrome_extractor import ChromeHistoryExtractor
        
        extractor = ChromeHistoryExtractor()
        entries = extractor.extract(days_back=7, limit=3, ecommerce_only=False)
        
        if entries:
            print(f"   ✅ Extracted {len(entries)} entries from Chrome")
            for e in entries[:2]:
                print(f"      - {e.title[:50]}...")
            return True
        else:
            print("   ⚠️ No entries found (this may be normal if no recent history)")
            return True  # Not a failure, just no data
    except FileNotFoundError:
        print("   ⚠️ Chrome history file not found (expected on some systems)")
        return True  # Not a failure, just missing file
    except Exception as e:
        print(f"   ❌ Chrome extraction error: {e}")
        return False


def test_shopify_scraper():
    """Test Shopify product scraping (makes real HTTP requests)"""
    print("\n🧪 Testing Shopify Scraper...")
    try:
        from app.services.shopify_scraper import ShopifyScraper
        
        scraper = ShopifyScraper()
        
        # Just test one store with 2 products to minimize requests
        products = scraper.scrape_store("allbirds.com", max_products=2)
        
        if products:
            print(f"   ✅ Scraped {len(products)} products from Allbirds")
            for p in products:
                print(f"      - {p.title}: ${p.variants[0].get('price') if p.variants else 'N/A'}")
            scraper.close()
            return True
        else:
            print("   ❌ No products returned from Shopify")
            scraper.close()
            return False
    except Exception as e:
        print(f"   ❌ Shopify scraper error: {e}")
        return False


def test_gemini_structurer():
    """Test Gemini data structuring (makes OpenRouter API call)"""
    print("\n🧪 Testing Gemini Structurer...")
    try:
        from app.services.gemini_structurer import GeminiStructurer
        from app.utils.config import get_settings
        
        settings = get_settings()
        if not settings.openrouter_api_key:
            print("   ⚠️ OPENROUTER_API_KEY not set, skipping")
            return True
        
        structurer = GeminiStructurer()
        
        # Test with sample content
        sample_content = """
        Nike Air Max 270
        $150.00 USD
        Men's Running Shoes
        Available in Black, White, and Blue
        The Nike Air Max 270 features the tallest Air unit yet for a super-soft ride.
        """
        
        product = structurer.extract_product_from_page(
            url="https://nike.com/air-max-270",
            title="Nike Air Max 270 - Men's Running Shoes",
            content=sample_content
        )
        
        if product:
            print(f"   ✅ Extracted product: {product.name}")
            print(f"      Price: ${product.price}")
            print(f"      Category: {product.category}")
            return True
        else:
            print("   ❌ Failed to extract product info")
            return False
    except Exception as e:
        print(f"   ❌ Gemini structurer error: {e}")
        return False


def test_firecrawl_scraper():
    """Test Firecrawl content scraping (makes Firecrawl API call)"""
    print("\n🧪 Testing Firecrawl Scraper...")
    try:
        from app.services.firecrawl_scraper import FirecrawlScraper
        from app.utils.config import get_settings
        
        settings = get_settings()
        if not settings.firecrawl_api_key:
            print("   ⚠️ FIRECRAWL_API_KEY not set, skipping")
            return True
        
        scraper = FirecrawlScraper()
        result = scraper.scrape("https://allbirds.com")
        
        if result and result.get("success"):
            markdown = result.get("markdown", "")
            print(f"   ✅ Scraped {len(markdown)} chars of content")
            print(f"      Preview: {markdown[:100]}...")
            scraper.close()
            return True
        else:
            print("   ❌ Firecrawl returned no data")
            scraper.close()
            return False
    except Exception as e:
        print(f"   ❌ Firecrawl error: {e}")
        return False


def run_all_tests():
    """Run all Phase 2 tests"""
    print("=" * 60)
    print("PHASE 2: DATA INGESTION TESTS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {
        "mock_data": test_mock_data(),
        "chrome": test_chrome_extraction(),
        "shopify": test_shopify_scraper(),
        "gemini": test_gemini_structurer(),
        "firecrawl": test_firecrawl_scraper(),
    }
    
    print("\n" + "=" * 60)
    print("PHASE 2 TEST RESULTS")
    print("=" * 60)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test.ljust(15)}: {status}")
    
    all_passed = all(results.values())
    print("=" * 60)
    print(f"Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("=" * 60)
    
    # Print token usage summary
    try:
        from app.utils.token_utils import get_tracker
        tracker = get_tracker()
        if tracker.total_tokens > 0:
            print(tracker.summary())
    except Exception:
        pass
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()

