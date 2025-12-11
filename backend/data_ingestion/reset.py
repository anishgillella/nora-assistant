#!/usr/bin/env python3
"""
Nora Reset & Scrape Script

Usage:
    python reset.py                   # Wipe ALL data
    python reset.py --scrape          # Scrape with custom scraper + Firecrawl fallback
    python reset.py --scrape --deep   # Scrape + LLM structuring + Pinecone
"""

import sys
import os
import json
import shutil
import asyncio
import argparse
import time
import re
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Add backend to path for imports
# File is in backend/data_ingestion/reset.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

# Directories
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
SCRAPE_DIR = os.path.join(SCRIPT_DIR, "scrape")
BROWSER_HISTORY_DIR = os.path.join(SCRAPE_DIR, "browser_history")
SHOPIFY_STORES_DIR = os.path.join(SCRAPE_DIR, "shopify_stores")
DB_PATH = os.path.join(BACKEND_DIR, "nora.db")

# Scraping budget
GENERAL_PAGES = 30
ECOMMERCE_PAGES = 20
TOTAL_FIRECRAWL_BUDGET = GENERAL_PAGES + ECOMMERCE_PAGES

# Firecrawl rate limiting (only used as fallback)
FIRECRAWL_DELAY_SECONDS = 12

# E-commerce domains
ECOMMERCE_DOMAINS = [
    "amazon.com", "ebay.com", "shopify.com", "etsy.com",
    "nike.com", "adidas.com", "nordstrom.com", "target.com",
    "walmart.com", "bestbuy.com", "allbirds.com", "gymshark.com",
    "warbyparker.com", "bonobos.com", "madewell.com", "zappos.com",
    "rei.com", "patagonia.com", "lululemon.com", "gap.com",
    "samsung.com", "youngla.com", "puma.com",
]

# Curated e-commerce URLs (20 total)
CURATED_ECOMMERCE_URLS = [
    ("samsung_monitor", "https://www.samsung.com/us/monitors/smart/32-inch-smart-monitor-m90f-4k-oled-vision-ai-monitor-sku-ls32fm902snxza/"),
    ("samsung_ring", "https://www.samsung.com/us/rings/galaxy-ring/buy/galaxy-ring-size-10-titanium-silver-sm-q500nzsaxar/"),
    ("amazon_ps5", "https://www.amazon.com/PlayStation-5-Pro-Console/dp/B0DGY63Z2H/"),
    ("amazon_beats", "https://www.amazon.com/Beats-Studio-Pro-Personalized-Compatibility/dp/B0C8PWSW7T/"),
    ("nike_vomero", "https://www.nike.com/t/vomero-plus-mens-road-running-shoes-5npsVBwT/IM6011-060"),
    ("nike_airforce", "https://www.nike.com/t/air-force-1-07-mens-shoes-jBrhbr/CT2302-100"),
    ("adidas_ultraboost", "https://www.adidas.com/us/ultraboost-5x-shoes/JH7244.html"),
    ("adidas_pants", "https://www.adidas.com/us/essentials-3-stripes-fleece-pants/JD1861.html"),
    ("gymshark_joggers", "https://www.gymshark.com/products/gymshark-crest-joggers-black-ss22"),
    ("gymshark_tank", "https://www.gymshark.com/products/gymshark-geo-seamless-tank-black-charcoal-grey-ss24"),
    ("lululemon_shorts", "https://shop.lululemon.com/p/men-shorts/Zeroed-In-Linerless-Short-7/_/prod11680028?color=33068"),
    ("lululemon_jogger", "https://shop.lululemon.com/p/men-joggers/Abc-Jogger/_/prod8530240?color=26865"),
    ("patagonia_book1", "https://www.patagonia.com/product/training-for-the-uphill-athlete-a-manual-for-mountain-runners-and-ski-mountaineers-paperback-book/BK800.html"),
    ("patagonia_book2", "https://www.patagonia.com/product/simple-fly-fishing-revised-second-edition-techniques-for-tenkara-and-rod-and-reel-book/BK709.html"),
    ("youngla_product1", "https://www.youngla.com/products/8002"),
    ("youngla_product2", "https://www.youngla.com/products/249-1"),
    ("puma_shoes", "https://us.puma.com/us/en/pd/magmax-nitro-2-mens-road-running-shoes/312125?swatch=04"),
    ("puma_jacket", "https://us.puma.com/us/en/pd/polar-fleece-mens-hooded-fleece-jacket/943330?swatch=01"),
    ("walmart_tv", "https://www.walmart.com/ip/Philips-55-Class-4K-UHD-2160p-Google-Gaming-TV/17233061084"),
    ("walmart_treadmill", "https://www.walmart.com/ip/Under-Desk-Treadmill-Walking-Pad-with-Incline-for-Home-and-Office-Fitness-Workout-265-Lbs-Capacity/15428315908"),
]

# Domains to skip (never scrape)
SKIP_DOMAINS = [
    "google.com", "mail.google.com", "docs.google.com", 
    "drive.google.com", "calendar.google.com",
    "localhost", "127.0.0.1", "chrome://", "edge://",
    "accounts.google.com", "login.", "auth.", "signin.",
    "perplexity.ai",  # Skip perplexity
]


# ========== CUSTOM SCRAPER ==========

class CustomScraper:
    """Simple httpx + BeautifulSoup scraper (no JS rendering)."""
    
    def __init__(self):
        self.client = httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
    
    def scrape(self, url: str) -> dict:
        """
        Scrape URL and return markdown content.
        Returns: {"success": bool, "markdown": str, "title": str}
        """
        try:
            response = self.client.get(url)
            
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract title
            title = ""
            if soup.title:
                title = soup.title.string or ""
            
            # Remove script, style, nav, footer, header elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                tag.decompose()
            
            # Try to find main content
            main_content = soup.find("main") or soup.find("article") or soup.find("body")
            
            if main_content:
                # Convert to markdown
                markdown = md(str(main_content), heading_style="ATX", strip=["img"])
                # Clean up excessive whitespace
                markdown = re.sub(r'\n{3,}', '\n\n', markdown)
                markdown = markdown.strip()
                
                if len(markdown) > 200:  # Minimum viable content
                    return {"success": True, "markdown": markdown, "title": title}
            
            return {"success": False, "error": "No main content found"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def close(self):
        self.client.close()


# ========== UTILITY FUNCTIONS ==========

def reset_all():
    """Wipe ALL data."""
    print("\n🗑️  === FULL DATABASE RESET ===\n")
    
    confirm = input("⚠️  This will DELETE ALL DATA. Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        print("❌ Aborted.")
        return
    
    # Clear Pinecone
    print("\n📦 Clearing Pinecone...")
    try:
        from app.services.vector_store import PineconeStore
        store = PineconeStore()
        store.delete_namespace("browsing-memory")
        print("   ✅ Cleared browsing-memory namespace")
        store.delete_namespace("products")
        print("   ✅ Cleared products namespace")
        store.close()
    except Exception as e:
        print(f"   ❌ Pinecone error: {e}")
    
    # Delete SQLite
    print("\n🗄️  Deleting SQLite database...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"   ✅ Deleted {DB_PATH}")
    else:
        print("   ⚠️  No database file found")
    
    # Clear JSON files
    print("\n📁 Clearing JSON data files...")
    for filename in ["browsing_history.json", "products.json"]:
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"   ✅ Deleted {filename}")
    
    # Clear scrape directory
    if os.path.exists(SCRAPE_DIR):
        shutil.rmtree(SCRAPE_DIR)
        print(f"   ✅ Deleted scrape/ directory")
    
    print("\n✨ All databases wiped clean!\n")


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


def is_ecommerce(url: str) -> bool:
    """Check if URL is from an e-commerce domain."""
    domain = get_domain(url)
    return any(ec in domain for ec in ECOMMERCE_DOMAINS)


def should_skip(url: str) -> bool:
    """Check if URL should be skipped."""
    domain = get_domain(url)
    url_lower = url.lower()
    return any(skip in domain or skip in url_lower for skip in SKIP_DOMAINS)


def sanitize_filename(url: str) -> str:
    """Create a safe filename from URL."""
    domain = get_domain(url)
    path = urlparse(url).path.strip("/").replace("/", "_")[:50]
    return f"{domain}_{path}".replace(".", "_").replace(" ", "_")[:80] + ".md"


def smart_sample_urls(entries: list) -> tuple[list, list]:
    """
    Smart sampling strategy:
    - E-commerce sites: Get ALL pages (no limit)
    - Non-e-commerce sites: Get max 3 pages per domain
    
    Returns: (ecommerce_entries, general_entries)
    """
    ecommerce_entries = []
    general_by_domain = defaultdict(list)
    
    for entry in entries:
        if should_skip(entry.url):
            continue
        
        if is_ecommerce(entry.url):
            # Keep ALL e-commerce pages
            ecommerce_entries.append(entry)
        else:
            # Group non-e-commerce by domain
            domain = get_domain(entry.url)
            general_by_domain[domain].append(entry)
    
    # Sample max 3 pages per non-e-commerce domain
    general_entries = []
    for domain, domain_entries in general_by_domain.items():
        # Take first 3 entries per domain (most recent since history is usually sorted)
        general_entries.extend(domain_entries[:3])
    
    print(f"   📊 E-commerce pages: {len(ecommerce_entries)} (all kept)")
    print(f"   📊 Non-e-commerce: {len(general_entries)} from {len(general_by_domain)} domains (max 3 per domain)")
    
    return ecommerce_entries, general_entries


def scrape_url_with_fallback(url: str, custom_scraper, firecrawl_scraper) -> dict:
    """
    Try custom scraper first, fall back to Firecrawl if it fails.
    Returns: {"success": bool, "markdown": str, "title": str, "method": str}
    """
    # Try custom scraper first (free)
    result = custom_scraper.scrape(url)
    if result.get("success"):
        return {**result, "method": "custom"}
    
    # Fallback to Firecrawl (costs credits)
    if firecrawl_scraper:
        print(f"      ↪ Custom failed, trying Firecrawl...")
        fc_result = firecrawl_scraper.scrape(url)
        if fc_result and fc_result.get("success"):
            return {
                "success": True,
                "markdown": fc_result.get("markdown", ""),
                "title": fc_result.get("metadata", {}).get("title", ""),
                "method": "firecrawl"
            }
        time.sleep(FIRECRAWL_DELAY_SECONDS)  # Rate limit for Firecrawl
    
    return {"success": False, "error": result.get("error", "Unknown"), "method": "none"}


async def scrape_only():
    """Scrape with custom scraper + Firecrawl fallback."""
    print("\n🚀 === SCRAPE MODE ===\n")
    print("📝 Primary: Custom scraper (httpx + BeautifulSoup)")
    print("🔄 Fallback: Firecrawl (only when custom fails)")
    
    # Create directories
    os.makedirs(BROWSER_HISTORY_DIR, exist_ok=True)
    os.makedirs(SHOPIFY_STORES_DIR, exist_ok=True)
    
    from app.services.chrome_extractor import ChromeHistoryExtractor
    from app.services.shopify_scraper import ShopifyScraper
    from app.services.firecrawl_scraper import FirecrawlScraper
    
    custom_scraper = CustomScraper()
    firecrawl_scraper = FirecrawlScraper()
    
    scrape_count = 0
    custom_count = 0
    firecrawl_count = 0
    failed_count = 0
    
    # ========== BROWSER HISTORY (Smart Sampling) ==========
    print("\n🌐 Scraping Browser History...")
    print("   📋 Strategy: ALL e-commerce pages, max 3 per non-e-commerce domain")
    try:
        extractor = ChromeHistoryExtractor()
        raw_entries = extractor.get_all_history(days_back=450, limit=1000)
        
        if raw_entries:
            print(f"   📥 Found {len(raw_entries)} history entries")
            
            # Smart sampling: all e-commerce, max 3 per non-e-commerce domain
            ecommerce_entries, general_entries = smart_sample_urls(raw_entries)
            all_entries = ecommerce_entries + general_entries
            
            print(f"   📊 Total to scrape: {len(all_entries)} pages")
            
            for i, entry in enumerate(all_entries):
                is_ecom = entry in ecommerce_entries
                tag = "🛒" if is_ecom else "📄"
                print(f"\n   {tag} [{i+1}/{len(all_entries)}] {entry.url[:60]}...")
                
                result = scrape_url_with_fallback(entry.url, custom_scraper, firecrawl_scraper)
                
                if result.get("success"):
                    markdown = result.get("markdown", "")
                    title = result.get("title", entry.title)
                    method = result.get("method", "unknown")
                    
                    # Save e-commerce to ecommerce subfolder, general to main folder
                    if is_ecom:
                        save_dir = os.path.join(BROWSER_HISTORY_DIR, "ecommerce")
                        os.makedirs(save_dir, exist_ok=True)
                    else:
                        save_dir = BROWSER_HISTORY_DIR
                    
                    filename = sanitize_filename(entry.url)
                    filepath = os.path.join(save_dir, filename)
                    
                    with open(filepath, "w") as f:
                        f.write(f"# {title}\n\n")
                        f.write(f"**URL:** {entry.url}\n\n")
                        f.write(f"**Domain:** {get_domain(entry.url)}\n\n")
                        f.write(f"**Type:** {'e-commerce' if is_ecom else 'general'}\n\n")
                        f.write(f"**Scraped via:** {method}\n\n")
                        f.write("---\n\n")
                        f.write(markdown[:10000])  # Limit file size
                    
                    scrape_count += 1
                    if method == "custom":
                        custom_count += 1
                        print(f"   ✅ Saved (custom): {filename[:50]}")
                    else:
                        firecrawl_count += 1
                        print(f"   ✅ Saved (firecrawl): {filename[:50]}")
                else:
                    failed_count += 1
                    print(f"   ❌ Failed: {result.get('error', 'Unknown')}")
                
        else:
            print("   ⚠️  No browser history found")
            
    except FileNotFoundError:
        print("   ⚠️  Chrome history file not found")
    except Exception as e:
        print(f"   ❌ Browser history error: {e}")
    
    # ========== CURATED E-COMMERCE (Additional pages) ==========
    print(f"\n🛒 Scraping {len(CURATED_ECOMMERCE_URLS)} Curated E-commerce URLs...")
    
    ecommerce_dir = os.path.join(BROWSER_HISTORY_DIR, "ecommerce")
    os.makedirs(ecommerce_dir, exist_ok=True)
    
    for i, (name, url) in enumerate(CURATED_ECOMMERCE_URLS):
        print(f"\n   [{i+1}/{len(CURATED_ECOMMERCE_URLS)}] {name}...")
        
        result = scrape_url_with_fallback(url, custom_scraper, firecrawl_scraper)
        
        if result.get("success"):
            markdown = result.get("markdown", "")
            title = result.get("title", name)
            method = result.get("method", "unknown")
            
            filepath = os.path.join(ecommerce_dir, f"{name}.md")
            
            with open(filepath, "w") as f:
                f.write(f"# {title}\n\n")
                f.write(f"**URL:** {url}\n\n")
                f.write(f"**Domain:** {get_domain(url)}\n\n")
                f.write(f"**Scraped via:** {method}\n\n")
                f.write("---\n\n")
                f.write(markdown[:10000])
            
            scrape_count += 1
            if method == "custom":
                custom_count += 1
                print(f"   ✅ Saved (custom): {name}")
            else:
                firecrawl_count += 1
                print(f"   ✅ Saved (firecrawl): {name}")
        else:
            failed_count += 1
            print(f"   ❌ Failed: {result.get('error', 'Unknown')}")
    
    custom_scraper.close()
    firecrawl_scraper.close()
    
    # ========== SHOPIFY STORES (JSON API, no scraping) ==========
    print("\n🛍️  Scraping Shopify Stores (JSON API)...")
    try:
        scraper = ShopifyScraper()
        all_products = await scraper.scrape_and_convert_all()
        
        if all_products:
            by_store = {}
            for product in all_products:
                store_name = product.store_name or "unknown"
                if store_name not in by_store:
                    by_store[store_name] = []
                by_store[store_name].append(product.model_dump())
            
            for store_name, products_list in by_store.items():
                filename = f"{store_name.lower().replace(' ', '_')}.json"
                filepath = os.path.join(SHOPIFY_STORES_DIR, filename)
                with open(filepath, "w") as f:
                    json.dump(products_list, f, indent=2)
                print(f"   💾 {filename}: {len(products_list)} products")
        
        await scraper.close()
        
    except Exception as e:
        print(f"   ❌ Shopify error: {e}")
    
    print("\n" + "=" * 60)
    print("✨ SCRAPING COMPLETE!")
    print("=" * 60)
    print(f"📊 Total scraped: {scrape_count}")
    print(f"   • Custom scraper: {custom_count}")
    print(f"   • Firecrawl fallback: {firecrawl_count}")
    print(f"   • Failed: {failed_count}")
    print(f"📁 Browser history: {BROWSER_HISTORY_DIR}")
    print(f"📁 E-commerce:      {os.path.join(BROWSER_HISTORY_DIR, 'ecommerce')}")
    print(f"📁 Shopify stores:  {SHOPIFY_STORES_DIR}")


async def scrape_and_process():
    """Scrape + LLM structuring + Pinecone."""
    print("\n🚀 === SCRAPE + LLM PROCESSING ===\n")
    await scrape_only()
    print("\n⚠️  LLM processing to be implemented separately")


def main():
    parser = argparse.ArgumentParser(
        description="Nora Reset & Scrape Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reset.py                   # Wipe ALL data
  python reset.py --scrape          # Scrape (custom + Firecrawl fallback)
  python reset.py --scrape --deep   # Scrape + LLM + Pinecone
        """
    )
    parser.add_argument("--scrape", action="store_true", help="Scrape pages")
    parser.add_argument("--deep", action="store_true", help="Add LLM structuring + Pinecone")
    
    args = parser.parse_args()
    
    os.chdir(BACKEND_DIR)
    
    if args.scrape:
        if args.deep:
            asyncio.run(scrape_and_process())
        else:
            asyncio.run(scrape_only())
    else:
        reset_all()


if __name__ == "__main__":
    main()
