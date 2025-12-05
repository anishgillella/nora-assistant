"""
Firecrawl Content Scraper

Scrapes web content using Firecrawl API for clean markdown extraction.
Limited usage to reduce costs during testing.
"""
import httpx
from typing import Optional, Dict, List
from app.utils.config import get_settings


class FirecrawlScraper:
    """Scrape web content using Firecrawl API"""
    
    BASE_URL = "https://api.firecrawl.dev/v1"
    
    def __init__(self, api_key: str = None):
        settings = get_settings()
        self.api_key = api_key or settings.firecrawl_api_key
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0
        )
    
    def scrape(self, url: str) -> Optional[Dict]:
        """
        Scrape a URL and return structured content
        
        Args:
            url: URL to scrape
        
        Returns:
            Dict with markdown content and metadata, or None on error
        """
        try:
            response = self.client.post(
                f"{self.BASE_URL}/scrape",
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                    "waitFor": 2000  # Wait 2s for JS rendering
                }
            )
            
            if response.status_code != 200:
                print(f"⚠️ Firecrawl status {response.status_code} for {url}")
                return None
            
            data = response.json()
            
            if data.get("success"):
                return {
                    "markdown": data.get("data", {}).get("markdown", ""),
                    "metadata": data.get("data", {}).get("metadata", {}),
                    "success": True
                }
            return None
        except Exception as e:
            print(f"❌ Firecrawl error for {url}: {e}")
            return None
    
    def scrape_batch(self, urls: List[str], max_urls: int = 5) -> Dict[str, Optional[Dict]]:
        """
        Scrape multiple URLs (limited for cost control)
        
        Args:
            urls: List of URLs to scrape
            max_urls: Maximum number of URLs to scrape
        
        Returns:
            Dict mapping URL to scraped content
        """
        results = {}
        urls_to_scrape = urls[:max_urls]  # Limit for cost control
        
        for url in urls_to_scrape:
            print(f"🔍 Scraping: {url[:60]}...")
            results[url] = self.scrape(url)
        
        success_count = sum(1 for r in results.values() if r and r.get("success"))
        print(f"✅ Successfully scraped {success_count}/{len(urls_to_scrape)} URLs")
        
        return results
    
    def close(self):
        """Close HTTP client"""
        self.client.close()
