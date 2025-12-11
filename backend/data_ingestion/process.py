#!/usr/bin/env python3
"""
Nora Process Script

Reads scraped content from scrape/ folder and uses LLM to extract structured data.
All extraction uses LLM with Pydantic models - NO regex or heuristics.

Logic:
- All browsing history pages → extract generalized BrowsingActivity → browsing-memory namespace
- If LLM detects activity_type == "product" → ALSO extract ProductInfo → products namespace
- Shopify products → already structured → products namespace

Usage:
    python process.py               # Process all scraped content
    python process.py --retry       # Only process failed/skipped items from last run
    python process.py --dry-run     # Show what would be processed (no LLM calls)
"""

import sys
import os
import json
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Set
from urllib.parse import urlparse

# Add backend to path to allow 'import app'
# File is in backend/data_ingestion/process.py
# We need to add backend/ to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

# Directories
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
SCRAPE_DIR = os.path.join(SCRIPT_DIR, "scrape")
BROWSER_HISTORY_DIR = os.path.join(SCRAPE_DIR, "browser_history")
ECOMMERCE_DIR = os.path.join(BROWSER_HISTORY_DIR, "ecommerce")
SHOPIFY_STORES_DIR = os.path.join(SCRAPE_DIR, "shopify_stores")

# Tracking file for incremental processing
TRACKING_FILE = os.path.join(SCRAPE_DIR, ".process_tracking.json")


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


def load_tracking() -> Dict:
    """Load tracking data from previous runs."""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, "r") as f:
            return json.load(f)
    return {
        "files": {},  # filepath -> {status, timestamp, error, product_extracted}
        "summary": {
            "total_processed": 0,
            "total_failed": 0,
            "products_extracted": 0,
            "products_failed": 0
        },
        "last_run": None
    }


def save_tracking(tracking: Dict):
    """Save tracking data."""
    tracking["last_run"] = datetime.now().isoformat()
    with open(TRACKING_FILE, "w") as f:
        json.dump(tracking, f, indent=2)


def parse_markdown_file(filepath: str) -> Dict:
    """Parse a scraped markdown file to extract metadata and content."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    title = ""
    url = ""
    domain = ""
    method = ""
    
    lines = content.split("\n")
    body_start = 0
    
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("**URL:**"):
            url = line.replace("**URL:**", "").strip()
        elif line.startswith("**Domain:**"):
            domain = line.replace("**Domain:**", "").strip()
        elif line.startswith("**Scraped via:**"):
            method = line.replace("**Scraped via:**", "").strip()
        elif line.startswith("---"):
            body_start = i + 1
            break
    
    body = "\n".join(lines[body_start:]).strip()
    
    return {
        "title": title,
        "url": url,
        "domain": domain,
        "method": method,
        "content": body,  # Full content (Gemini has large context)
        "filepath": filepath
    }


# OpenRouter rate limiting - 5 concurrent requests (conservative for paid models)
CONCURRENT_REQUESTS = 5


async def process_single_file(
    filepath: Path,
    index: int,
    total: int,
    structurer,
    semaphore: asyncio.Semaphore,
) -> Dict:
    """Process a single file with semaphore for rate limiting."""
    async with semaphore:
        filepath_str = str(filepath)
        data = parse_markdown_file(filepath_str)
        result = {
            "filepath": filepath_str,
            "data": data,
            "entry": None,
            "product": None,
            "status": "failed",
            "error": None,
            "activity_type": [],
            "is_product": False,
            "product_extracted": False,
            "product_error": None
        }
        
        print(f"\n   [{index+1}/{total}] {data['title'][:50]}...")
        
        try:
            activity = await structurer.extract_activity(
                url=data["url"],
                title=data["title"],
                content=data["content"]
            )
            
            if activity:
                entry = {
                    "id": f"browsing_{index}",
                    "url": data["url"],
                    "title": data["title"],
                    "domain": data["domain"],
                    "visit_time": datetime.now().isoformat(),
                    "visit_timestamp": int(datetime.now().timestamp()),
                    "scrape_method": data["method"],
                    "activity_type": activity.get("activity_type", ["content"]),
                    "category": activity.get("category", []),
                    "topics": activity.get("topics", []),
                    "context": activity.get("context", []),
                    "vibe": activity.get("vibe", []),
                    "inferred_needs": activity.get("inferred_needs", []),
                    "semantic_summary": activity.get("semantic_summary", ""),
                    "price": activity.get("price"),
                    "brand": activity.get("brand"),
                    "materials": activity.get("materials"),
                    "occasion": activity.get("occasion"),
                    "visual_characteristics": activity.get("visual_characteristics"),
                }
                result["entry"] = entry
                result["status"] = "success"
                
                activity_type = activity.get('activity_type', ['content'])
                if isinstance(activity_type, str):
                    activity_type = [activity_type]
                result["activity_type"] = activity_type
                
                category = activity.get('category', [])
                if isinstance(category, str):
                    category = [category]
                
                print(f"   ✅ {activity_type} | {category}")
                
                # Extract product if activity_type contains "product"
                is_product = "product" in activity_type
                result["is_product"] = is_product
                
                if is_product:
                    print(f"      🛒 Extracting ProductInfo...")
                    try:
                        product_info = await structurer.extract_product_from_page(
                            url=data["url"],
                            title=data["title"],
                            content=data["content"]
                        )
                        
                        if product_info and product_info.name:
                            product = {
                                "id": f"browsing_product_{index}",
                                "source": "browsing_history",
                                "product_url": data["url"],
                                "store_name": data["domain"],
                                "scrape_method": data["method"],
                                # Keep None values for JSON (null) - Pinecone sanitizes separately
                                "name": product_info.name,
                                "price": product_info.price,  # null if not found
                                "currency": product_info.currency,
                                "category": product_info.category,
                                "brand": product_info.brand,
                                "image_url": product_info.image_url,
                                "description": product_info.description,
                                "availability": product_info.availability,
                                "visual_characteristics": product_info.visual_characteristics,
                                "materials": product_info.materials,
                                "occasion": product_info.occasion,
                                "gender_target": product_info.gender_target,
                                "season": product_info.season,
                                "sustainability": product_info.sustainability,
                                "color_family": product_info.color_family,
                            }
                            result["product"] = product
                            result["product_extracted"] = True
                            print(f"      ✅ Product: {product_info.name} - ${product_info.price or 'N/A'}")
                        else:
                            result["product_error"] = "No product info extracted"
                            print(f"      ⚠️ No product info extracted")
                    except Exception as e:
                        result["product_error"] = str(e)
                        print(f"      ⚠️ Product error: {e}")
            else:
                result["error"] = "LLM returned None"
                print(f"   ⚠️ LLM returned None")
                
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Error: {e}")
        
        return result


async def process_all_browsing_history(
    structurer,
    dry_run: bool = False,
    retry_only: bool = False,
    tracking: Dict = None
) -> tuple[List[Dict], List[Dict], Dict]:
    """
    Process ALL browsing history with parallel LLM requests.
    Uses asyncio.Semaphore for rate limiting (5 concurrent).
    """
    print("\n📖 Processing Browsing History...")
    print(f"   • Parallel processing ({CONCURRENT_REQUESTS} concurrent requests)")
    print("   • Product extraction if LLM detects activity_type=product")
    
    browsing_entries = []
    detected_products = []
    
    if tracking is None:
        tracking = load_tracking()
    
    files_dict = tracking.get("files", {})
    summary = tracking.get("summary", {"total_processed": 0, "total_failed": 0, "products_extracted": 0, "products_failed": 0})
    
    # Collect ALL markdown files
    all_md_files = []
    general_files = list(Path(BROWSER_HISTORY_DIR).glob("*.md"))
    all_md_files.extend(general_files)
    
    if os.path.exists(ECOMMERCE_DIR):
        ecommerce_files = list(Path(ECOMMERCE_DIR).glob("*.md"))
        all_md_files.extend(ecommerce_files)
    
    # Filter based on retry mode
    if retry_only:
        files_to_process = [
            f for f in all_md_files 
            if str(f) not in files_dict or files_dict[str(f)].get("status") == "failed"
        ]
        print(f"\n   🔄 RETRY MODE: {len(files_to_process)} files to retry")
        print(f"   (Skipping {len(all_md_files) - len(files_to_process)} already processed)")
    else:
        files_to_process = all_md_files
        print(f"\n   Found {len(files_to_process)} total files")
    
    # Dry run - just show status
    if dry_run:
        for i, filepath in enumerate(files_to_process):
            filepath_str = str(filepath)
            data = parse_markdown_file(filepath_str)
            file_status = files_dict.get(filepath_str, {}).get("status", "new")
            status_icon = "✅" if file_status == "success" else "❌" if file_status == "failed" else "📝"
            print(f"   [{i+1}/{len(files_to_process)}] {status_icon} {data['title'][:50]}...")
        return browsing_entries, detected_products, tracking
    
    # Parallel processing with semaphore
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    total = len(files_to_process)
    
    tasks = [
        process_single_file(filepath, i, total, structurer, semaphore)
        for i, filepath in enumerate(files_to_process)
    ]
    
    print(f"\n   � Starting parallel processing...")
    results = await asyncio.gather(*tasks)
    
    # Aggregate results
    for result in results:
        filepath_str = result["filepath"]
        
        if result["status"] == "success":
            browsing_entries.append(result["entry"])
            summary["total_processed"] = summary.get("total_processed", 0) + 1
            
            if result["product"]:
                detected_products.append(result["product"])
                summary["products_extracted"] = summary.get("products_extracted", 0) + 1
            elif result["is_product"]:
                summary["products_failed"] = summary.get("products_failed", 0) + 1
            
            files_dict[filepath_str] = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "activity_type": result["activity_type"],
                "is_product": result["is_product"],
                "product_extracted": result["product_extracted"],
                "product_error": result["product_error"]
            }
        else:
            summary["total_failed"] = summary.get("total_failed", 0) + 1
            files_dict[filepath_str] = {
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
                "error": result["error"]
            }
    
    # Update tracking
    tracking["files"] = files_dict
    tracking["summary"] = summary
    
    return browsing_entries, detected_products, tracking


def load_shopify_products() -> List[Dict]:
    """Load all Shopify products from JSON files (already structured)."""
    print("\n🛍️ Loading Shopify Products...")
    
    products = []
    
    if not os.path.exists(SHOPIFY_STORES_DIR):
        print("   ⚠️ No shopify folder found")
        return products
    
    json_files = list(Path(SHOPIFY_STORES_DIR).glob("*.json"))
    print(f"   Found {len(json_files)} store files")
    
    for filepath in json_files:
        try:
            with open(filepath, "r") as f:
                store_products = json.load(f)
            
            for p in store_products:
                p["source"] = "shopify"
            
            products.extend(store_products)
            print(f"   📦 {filepath.stem}: {len(store_products)} products")
            
        except Exception as e:
            print(f"   ❌ Error loading {filepath.name}: {e}")
    
    return products


def load_existing_data() -> tuple[List[Dict], List[Dict]]:
    """Load existing processed data to merge with new results."""
    browsing = []
    products = []
    
    browsing_path = os.path.join(DATA_DIR, "browsing_history.json")
    products_path = os.path.join(DATA_DIR, "products.json")
    
    if os.path.exists(browsing_path):
        with open(browsing_path, "r") as f:
            browsing = json.load(f)
    
    if os.path.exists(products_path):
        with open(products_path, "r") as f:
            products = json.load(f)
    
    return browsing, products


async def populate_databases(browsing_entries: List[Dict], all_products: List[Dict], dry_run: bool = False):
    """Populate Pinecone namespaces and save JSON for Data Explorer."""
    
    if dry_run:
        print("\n📊 DRY RUN - Would populate:")
        print(f"   • Browsing History: {len(browsing_entries)} entries → Pinecone")
        print(f"   • Products: {len(all_products)} products → Pinecone")
        return
    
    print("\n📊 Populating Databases...")
    
    from app.services.vector_store import PineconeStore
    
    store = PineconeStore()
    
    if browsing_entries:
        print(f"\n   📝 Upserting {len(browsing_entries)} browsing entries...")
        count = store.upsert_browsing_memory(browsing_entries)
        print(f"   ✅ Upserted {count} entries to Pinecone")
        
        browsing_json_path = os.path.join(DATA_DIR, "browsing_history.json")
        with open(browsing_json_path, "w") as f:
            json.dump(browsing_entries, f, indent=2, default=str)
        print(f"   💾 Saved to {browsing_json_path}")
    
    if all_products:
        print(f"\n   🛒 Upserting {len(all_products)} products...")
        count = store.upsert_products(all_products)
        print(f"   ✅ Upserted {count} products to Pinecone")
        
        products_json_path = os.path.join(DATA_DIR, "products.json")
        with open(products_json_path, "w") as f:
            json.dump(all_products, f, indent=2, default=str)
        print(f"   💾 Saved to {products_json_path}")
    
    store.close()


async def main(dry_run: bool = False, retry_only: bool = False):
    """Main processing pipeline."""
    print("\n🚀 === NORA PROCESS PIPELINE ===")
    print("   All extraction uses LLM (Gemini via OpenRouter)")
    print("   Structured output via Pydantic models\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE\n")
    if retry_only:
        print("🔄 RETRY MODE - Only processing failed/new items\n")
    
    os.chdir(BACKEND_DIR)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    from app.services.gemini_structurer import GeminiStructurer
    from app.utils.token_utils import get_tracker
    
    structurer = GeminiStructurer()
    tracker = get_tracker()
    tracking = load_tracking()
    
    # Load existing data for retry mode
    existing_browsing, existing_products = [], []
    if retry_only:
        existing_browsing, existing_products = load_existing_data()
        print(f"   📂 Loaded {len(existing_browsing)} existing browsing entries")
        print(f"   📂 Loaded {len(existing_products)} existing products")
    
    # Process browsing history
    new_browsing, browsing_products, tracking = await process_all_browsing_history(
        structurer, dry_run, retry_only, tracking
    )
    
    # NOTE: Shopify products disabled - focusing only on browsing history products
    # shopify_products = load_shopify_products()
    shopify_products = []  # Empty - only use products from browsing history
    
    # Merge data
    if retry_only:
        # Merge new with existing (deduplicate by URL)
        existing_urls = {e.get("url") for e in existing_browsing}
        for entry in new_browsing:
            if entry.get("url") not in existing_urls:
                existing_browsing.append(entry)
        all_browsing = existing_browsing
        
        # Merge products
        existing_product_urls = {p.get("product_url") for p in existing_products}
        for p in browsing_products:
            if p.get("product_url") not in existing_product_urls:
                existing_products.append(p)
        all_products = existing_products + shopify_products
    else:
        all_browsing = new_browsing
        all_products = browsing_products + shopify_products
    
    # Save tracking
    if not dry_run:
        save_tracking(tracking)
    
    # Populate databases
    await populate_databases(all_browsing, all_products, dry_run)
    
    # Summary
    print("\n" + "=" * 60)
    print("✨ PROCESSING COMPLETE!")
    print("=" * 60)
    print(f"\n📊 Browsing History: {len(all_browsing)} entries")
    
    if all_browsing:
        activity_counts = {}
        for e in all_browsing:
            t = e.get("activity_type", ["unknown"])
            if isinstance(t, list):
                for activity in t:
                    activity_counts[activity] = activity_counts.get(activity, 0) + 1
            else:
                activity_counts[t] = activity_counts.get(t, 0) + 1
        for activity_type, count in sorted(activity_counts.items()):
            print(f"   • [{activity_type}]: {count}")
    
    print(f"\n📊 Products (from browsing history only):")
    print(f"   • Total: {len(all_products)}")
    
    print(f"\n📊 Tracking:")
    print(f"   • Processed: {len(tracking.get('processed', []))}")
    print(f"   • Failed: {len(tracking.get('failed', []))}")
    
    if not dry_run and tracker.total_tokens > 0:
        print(f"\n💰 LLM Token Usage:")
        print(tracker.summary())
    
    print(f"\n📁 Output files:")
    print(f"   {os.path.join(DATA_DIR, 'browsing_history.json')}")
    print(f"   {os.path.join(DATA_DIR, 'products.json')}")
    print(f"   {TRACKING_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process scraped content with LLM")
    parser.add_argument("--dry-run", action="store_true", help="Preview without LLM calls")
    parser.add_argument("--retry", action="store_true", help="Only process failed/new items")
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run, retry_only=args.retry))
