"""
Memory API Router

Handles memory ingestion and retrieval from browsing history.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from app.services.chrome_extractor import ChromeHistoryExtractor
from app.services.vector_store import PineconeStore
from app.services.gemini_structurer import GeminiStructurer
from app.services.firecrawl_scraper import FirecrawlScraper
from app.utils.config import get_settings

router = APIRouter(prefix="/api/memory", tags=["memory"])

# Lazy-loaded singletons
_vector_store: Optional[PineconeStore] = None


def get_vector_store() -> PineconeStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = PineconeStore()
    return _vector_store


class IngestRequest(BaseModel):
    days_back: int = 30
    max_urls: int = 20
    ecommerce_only: bool = True
    enrich_with_firecrawl: bool = False  # Optional: scrape page content


class IngestResponse(BaseModel):
    status: str
    entries_processed: int
    entries_indexed: int
    message: str


class MemoryStats(BaseModel):
    total_vectors: int
    browsing_count: int
    products_count: int
    last_ingest: Optional[str] = None


@router.post("/ingest", response_model=IngestResponse)
async def ingest_browsing_history(request: IngestRequest):
    """
    Ingest browsing history from Chrome into Pinecone (Parallel).
    
    Extracts e-commerce URLs from Chrome history, and uses Gemini
    in PARALLEL to extract structured data.
    """
    try:
        settings = get_settings()
        
        # Extract Chrome history
        extractor = ChromeHistoryExtractor()
        raw_entries = extractor.extract(
            days_back=request.days_back,
            limit=request.max_urls,
            ecommerce_only=request.ecommerce_only
        )
        
        if not raw_entries:
            return IngestResponse(
                status="success",
                entries_processed=0,
                entries_indexed=0,
                message="No browsing history found matching criteria"
            )
        
        # Prepare entries for indexing
        structurer = GeminiStructurer()
        # Firecrawl parallel support is complex, skipping for now in parallel mode or strictly limiting
        # For max speed, we focus on Gemini parallelization
        firecrawl = None 
        
        print(f"🚀 Starting parallel extraction for {len(raw_entries)} URLs...")
        
        # Shared progress counter
        total_items = len(raw_entries)
        processed_count = 0
        
        async def process_entry(entry):
            """Helper to process a single entry"""
            nonlocal processed_count
            try:
                # Extract product info with Gemini (Async)
                product_info = await structurer.extract_product_from_page(
                    url=entry.url,
                    title=entry.title,
                    content=entry.title # Use title as content for speed if no scrape
                )
                
                # Increment progress
                processed_count += 1
                domain = entry.url.split("/")[2] if "/" in entry.url else "unknown"
                
                if not product_info:
                    print(f"   [{processed_count}/{total_items}] ❌ Failed {domain}: {entry.title[:30]}...")
                    return None
                
                print(f"   [{processed_count}/{total_items}] ✅ Processed {domain}: {entry.title[:30]}...")
                    
                return {
                    "id": f"browse_{entry.id}_{int(datetime.now().timestamp())}",
                    "url": entry.url,
                    "title": entry.title,
                    "domain": domain,
                    "visit_time": ChromeHistoryExtractor.chrome_time_to_datetime(
                        entry.last_visit_time
                    ).isoformat(),
                    "visit_count": entry.visit_count,
                    "product": {
                        "name": product_info.name,
                        "price": product_info.price or 0,
                        "category": product_info.category or "other",
                        "brand": product_info.brand or "",
                        "description": product_info.description or "",
                        # Rich attributes
                        "materials": product_info.materials,
                        "occasion": product_info.occasion,
                        "visual_characteristics": product_info.visual_characteristics,
                        "gender_target": product_info.gender_target,
                        "season": product_info.season,
                        "sustainability": product_info.sustainability,
                        "color_family": product_info.color_family
                    }
                }
            except Exception as e:
                # Only increment if not already incremented in try block?
                # Actually simpler to not increment in except if we assume it failed before incrementing
                # But here failure was likely IN the print. 
                # Let's just catch the specific print error or simplify.
                # If we error'd before increment, we want to increment.
                # If we error'd after increment, we don't.
                # Easiest is to move increment to finally? No, specific success handling.
                # Let's just print error. If count is off by 1 in worst case error it's fine, 
                # but let's avoid the double count from the bug we just fixed.
                print(f"❌ Error processing {entry.url}: {e}")
                return None

        # Run all extractions in parallel
        tasks = [process_entry(entry) for entry in raw_entries]
        results = await asyncio.gather(*tasks)
        
        # Filter out failed extractions
        entries_to_index = [r for r in results if r is not None]
        
        # Index in Pinecone (browsing namespace)
        store = get_vector_store()
        indexed_count = store.upsert_browsing_memory(entries_to_index)
        
        # ALSO sync products from browsing history to products namespace
        products_to_sync = []
        for entry in entries_to_index:
            product = entry.get("product", {})
            if product.get("name"): 
                products_to_sync.append({
                    "id": f"browse_product_{hash(product.get('name', ''))}",
                    "name": product.get("name", ""),
                    "brand": product.get("brand", ""),
                    "category": product.get("category", "other"),
                    "price": product.get("price", 0),
                    "description": product.get("description", ""),
                    "image_url": "",  
                    "product_url": entry.get("url", ""),
                    "source": "browsing_history",
                    # Pass rich attributes to product sync
                    "materials": product.get("materials", []),
                    "occasion": product.get("occasion", []),
                    "visual_characteristics": product.get("visual_characteristics", []),
                    "gender_target": product.get("gender_target"),
                    "season": product.get("season", []),
                    "sustainability": product.get("sustainability", []),
                    "color_family": product.get("color_family", [])
                })
        
        products_synced = 0
        if products_to_sync:
            products_synced = store.upsert_products(products_to_sync)
        
        return IngestResponse(
            status="success",
            entries_processed=len(raw_entries),
            entries_indexed=indexed_count,
            message=f"Indexed {indexed_count} browsing entries (Parallel), synced {products_synced} products"
        )
        
    except FileNotFoundError:
        return IngestResponse(
            status="warning",
            entries_processed=0,
            entries_indexed=0,
            message="Chrome history file not found"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStats)
async def get_memory_stats():
    """Get statistics about stored memory"""
    try:
        store = get_vector_store()
        stats = store.get_stats()
        
        return MemoryStats(
            total_vectors=stats.get("total_vectors", 0),
            browsing_count=stats.get("namespaces", {}).get("browsing-memory", 0),
            products_count=stats.get("namespaces", {}).get("products", 0),
            last_ingest=None  # Could track this in SQLite
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_memory(query: str, top_k: int = 5):
    """Search browsing memory for relevant entries"""
    try:
        store = get_vector_store()
        results = store.search_browsing(query, top_k=top_k)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_memory():
    """Clear all browsing memory (use with caution!)"""
    try:
        store = get_vector_store()
        store.delete_namespace("browsing-memory")
        return {"status": "success", "message": "Browsing memory cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed")
async def seed_memory():
    """Seed browsing memory with 50+ diverse entries (Products, Content, Social, Travel)."""
    import time
    
    try:
        # Timestamps for time-based filtering tests
        now = int(time.time())
        day = 86400
        
        # Helper for varied timestamps
        def ts(days_ago: int) -> int:
            return now - (days_ago * day)
        
        # ═══════════════════════════════════════════════════════════
        products = [
            {"url": "https://www.apple.com/shop/buy-mac/macbook-air", "title": "MacBook Air M3", "activity_type": "product", "category": "Electronics", "topics": ["Laptops", "Apple"], "context": ["Work Setup"], "vibe": ["Minimalist", "Premium"], "inferred_needs": ["Laptop Stand", "USB Hub"], "semantic_summary": "The MacBook Air M3 is Apple's thinnest and lightest laptop, featuring the powerful M3 chip with 8-core CPU and 10-core GPU. It offers up to 18 hours of battery life, a stunning 13.6-inch Liquid Retina display with 500 nits brightness, and weighs just 2.7 pounds. Ideal for creative professionals, students, and anyone needing portable power for video editing, coding, and design work.", "price": 1099, "brand": "Apple", "visit_timestamp": ts(1)},
            {"url": "https://www.nike.com/t/air-jordan-1-retro-high-og-mens-shoes-X5Vj9n", "title": "Air Jordan 1 High", "activity_type": "product", "category": "Shoes", "topics": ["Sneakers"], "context": ["Streetwear"], "vibe": ["Bold", "Vintage"], "inferred_needs": ["Sneaker Cleaner"], "semantic_summary": "The Air Jordan 1 Retro High OG is a legendary basketball sneaker originally released in 1985, featuring premium leather construction, Nike Air cushioning, and the iconic Wings logo. This colorway combines bold contrasting panels with a classic high-top silhouette. Perfect for sneaker collectors, streetwear enthusiasts, and anyone seeking a timeless style statement.", "price": 180, "brand": "Jordan", "visit_timestamp": ts(2)},
            {"url": "https://www.patagonia.com/product/mens-nano-puff-jacket/84212.html", "title": "Nano Puff Jacket", "activity_type": "product", "category": "Clothing", "topics": ["Outdoor Gear"], "context": ["Hiking"], "vibe": ["Rugged"], "inferred_needs": ["Hiking Boots"], "semantic_summary": "The Patagonia Nano Puff Jacket is an award-winning insulated layer made with 60g PrimaLoft Gold Insulation Eco for warmth even when wet. It features a 100% recycled polyester ripstop shell, weighs just 10.1 oz, and packs into its own pocket. Windproof and water-resistant, it's designed for alpine climbing, backcountry skiing, and everyday cold-weather use.", "price": 239, "brand": "Patagonia", "visit_timestamp": ts(3)},
            {"url": "https://www.hermanmiller.com/products/seating/office-chairs/aeron-chairs/", "title": "Aeron Chair", "activity_type": "product", "category": "Furniture", "topics": ["Home Office"], "context": ["Remote Work"], "vibe": ["Professional"], "inferred_needs": ["Standing Desk"], "semantic_summary": "The Herman Miller Aeron Chair is an iconic ergonomic office chair with patented PostureFit SL support and 8Z Pellicle suspension material. It features adjustable arms, tilt tension, and three size options for personalized comfort. Designed for 12+ hours of daily use, it meets BIFMA sustainability standards and comes with a 12-year warranty.", "price": 1275, "brand": "Herman Miller", "visit_timestamp": ts(5)},
            {"url": "https://www.hoka.com/en/us/mens-road/clifton-9/1127895.html", "title": "Hoka Clifton 9", "activity_type": "product", "category": "Shoes", "topics": ["Running"], "context": ["Marathon Training"], "vibe": ["Athletic"], "inferred_needs": ["Running Watch"], "semantic_summary": "The Hoka Clifton 9 is a lightweight daily trainer featuring a new compression-molded EVA midsole foam for responsive cushioning. It weighs 8.9 oz with a 5mm heel-toe drop and breathable engineered mesh upper. Updated with improved durability and early-stage Meta-Rocker geometry for smooth transitions. Ideal for daily training runs and first-time marathoners.", "price": 145, "brand": "Hoka", "visit_timestamp": ts(7)},
            {"url": "https://electronics.sony.com/audio/headphones/headband/p/wh1000xm5-s", "title": "Sony WH-1000XM5", "activity_type": "product", "category": "Electronics", "topics": ["Headphones"], "context": ["Focus Work"], "vibe": ["Minimalist"], "inferred_needs": ["Headphone Stand"], "semantic_summary": "The Sony WH-1000XM5 wireless headphones feature industry-leading noise cancellation with eight microphones and two processors. They offer 30 hours of battery life, LDAC Hi-Res Audio, Multipoint connection for two devices, and weigh just 250g. The soft-fit leather ear pads and silent rotating hinges make them perfect for travel, work, and audiophile listening.", "price": 399, "brand": "Sony", "visit_timestamp": ts(10)},
            # Additional products to reach 30
            {"url": "https://www.amazon.com/dp/B0BSHF7T5S", "title": "LG C3 65\" OLED TV", "activity_type": "product", "category": "Electronics", "topics": ["TVs", "Home Theater"], "context": ["Living Room Upgrade"], "vibe": ["Cinematic", "Premium"], "inferred_needs": ["Soundbar", "TV Mount"], "semantic_summary": "The LG C3 65-inch OLED TV features self-lit pixels delivering perfect blacks and infinite contrast. With Dolby Vision, Dolby Atmos, and 120Hz refresh rate, it's ideal for movies, gaming, and sports. The α9 AI Processor Gen6 upscales content to near-4K quality. Includes 4 HDMI 2.1 ports for next-gen gaming consoles.", "price": 1499, "brand": "LG", "visit_timestamp": ts(11)},
            {"url": "https://www.allbirds.com/products/mens-tree-runners", "title": "Allbirds Tree Runners", "activity_type": "product", "category": "Shoes", "topics": ["Sustainable Fashion"], "context": ["Everyday Wear"], "vibe": ["Eco-Friendly", "Casual"], "inferred_needs": ["Wool Socks"], "semantic_summary": "The Allbirds Tree Runners are lightweight everyday sneakers made from FSC-certified eucalyptus tree fiber. They feature a carbon-negative sole made with sugarcane-based SweetFoam, breathable mesh upper, and removable merino wool insole. Machine washable and designed for all-day comfort with a minimal environmental footprint.", "price": 98, "brand": "Allbirds", "visit_timestamp": ts(12)},
            {"url": "https://www.dyson.com/vacuum-cleaners/cordless/v15/detect", "title": "Dyson V15 Detect", "activity_type": "product", "category": "Electronics", "topics": ["Home Appliances"], "context": ["Home Cleaning"], "vibe": ["High-Tech", "Premium"], "inferred_needs": ["Extra Filters"], "semantic_summary": "The Dyson V15 Detect cordless vacuum features a laser that reveals hidden dust on hard floors. It has an LCD screen showing real-time particle counts, automatically adjusts suction power based on debris, and offers up to 60 minutes of runtime. The HEPA filtration captures 99.99% of particles for allergy-friendly cleaning.", "price": 749, "brand": "Dyson", "visit_timestamp": ts(13)},
            {"url": "https://www.arcteryx.com/us/en/shop/mens/beta-ar-jacket", "title": "Arc'teryx Beta AR Jacket", "activity_type": "product", "category": "Clothing", "topics": ["Outdoor Gear", "Rain Gear"], "context": ["Backcountry"], "vibe": ["Technical", "Adventure"], "inferred_needs": ["Hiking Pants"], "semantic_summary": "The Arc'teryx Beta AR Jacket is a versatile all-round shell using GORE-TEX Pro for maximum waterproof breathability. It features articulated patterning for mobility, helmet-compatible StormHood, and WaterTight zippers. At 16 oz, it handles everything from alpine climbing to urban commuting in wet conditions.", "price": 625, "brand": "Arc'teryx", "visit_timestamp": ts(14)},
            {"url": "https://www.apple.com/shop/product/MQD83AM/A/airpods-pro", "title": "AirPods Pro 2nd Gen", "activity_type": "product", "category": "Electronics", "topics": ["Earbuds", "Apple"], "context": ["Commute"], "vibe": ["Seamless", "Premium"], "inferred_needs": ["AirPods Case"], "semantic_summary": "The AirPods Pro 2nd Generation feature the H2 chip with 2x more active noise cancellation and Adaptive Transparency. They offer personalized Spatial Audio with head tracking, touch controls for volume, and up to 6 hours of listening time. The MagSafe charging case provides 30 hours total with Find My and precision finding built in.", "price": 249, "brand": "Apple", "visit_timestamp": ts(15)},
            {"url": "https://www.samsung.com/us/smartphones/galaxy-s24-ultra/", "title": "Samsung Galaxy S24 Ultra", "activity_type": "product", "category": "Electronics", "topics": ["Smartphones"], "context": ["Upgrade"], "vibe": ["Cutting-Edge", "Productive"], "inferred_needs": ["Phone Case"], "semantic_summary": "The Samsung Galaxy S24 Ultra features a 6.8-inch QHD+ Dynamic AMOLED display with 2600 nits brightness and titanium frame. It includes a 200MP main camera, 100x Space Zoom, built-in S Pen, and Galaxy AI features for real-time translation and photo editing. The Snapdragon 8 Gen 3 chip delivers flagship performance.", "price": 1299, "brand": "Samsung", "visit_timestamp": ts(16)},
            {"url": "https://www.brooklinen.com/products/luxe-core-sheet-set", "title": "Brooklinen Luxe Sheet Set", "activity_type": "product", "category": "Home", "topics": ["Bedding"], "context": ["Bedroom Upgrade"], "vibe": ["Cozy", "Luxurious"], "inferred_needs": ["Duvet Cover"], "semantic_summary": "The Brooklinen Luxe Sheet Set is made from 480 thread count long-staple cotton sateen for a silky, buttery feel. It includes a flat sheet, fitted sheet with deep pockets for thick mattresses, and two pillowcases. OEKO-TEX certified and available in 20+ colors, these sheets get softer with every wash.", "price": 179, "brand": "Brooklinen", "visit_timestamp": ts(17)},
            {"url": "https://www.yeti.com/coolers/hard-coolers/tundra/tundra-45.html", "title": "YETI Tundra 45 Cooler", "activity_type": "product", "category": "Outdoor", "topics": ["Camping Gear"], "context": ["Camping Trip"], "vibe": ["Rugged", "Adventure"], "inferred_needs": ["Ice Packs"], "semantic_summary": "The YETI Tundra 45 is a rotomolded hard cooler with PermaFrost Insulation that keeps ice for days. It features T-Rex Lid Latches, tie-down slots for securing to your truck bed, and is certified bear-resistant. Holds 26 cans with ice and is built to withstand extreme conditions for camping, fishing, and tailgating.", "price": 325, "brand": "YETI", "visit_timestamp": ts(18)},
            {"url": "https://www.peloton.com/shop/bike/bike-package", "title": "Peloton Bike", "activity_type": "product", "category": "Fitness", "topics": ["Home Gym", "Cycling"], "context": ["Fitness Goals"], "vibe": ["Motivating", "Premium"], "inferred_needs": ["Cycling Shoes"], "semantic_summary": "The Peloton Bike features a 22-inch HD touchscreen, near-silent belt drive, and magnetic resistance for smooth, quiet rides. Access thousands of on-demand and live classes led by world-class instructors. Track your progress with real-time metrics, compete on leaderboards, and stream content from Netflix and Spotify during workouts.", "price": 1445, "brand": "Peloton", "visit_timestamp": ts(19)},
            {"url": "https://www.sonos.com/en-us/shop/arc", "title": "Sonos Arc Soundbar", "activity_type": "product", "category": "Electronics", "topics": ["Home Audio"], "context": ["Home Theater"], "vibe": ["Immersive", "Premium"], "inferred_needs": ["Subwoofer"], "semantic_summary": "The Sonos Arc is a premium smart soundbar with 11 high-performance drivers including Dolby Atmos upward-firing speakers for 3D sound. Features speech enhancement, night mode, and TruePlay tuning that adapts to your room. Works with Alexa, Google Assistant, and AirPlay 2 for music streaming and voice control.", "price": 899, "brand": "Sonos", "visit_timestamp": ts(20)},
            {"url": "https://www.lululemon.com/en-us/p/abc-pant-classic/LM5AFTS.html", "title": "Lululemon ABC Pants", "activity_type": "product", "category": "Clothing", "topics": ["Athleisure"], "context": ["Office Casual"], "vibe": ["Versatile", "Comfortable"], "inferred_needs": ["Polo Shirt"], "semantic_summary": "The Lululemon ABC (Anti-Ball Crushing) Pants feature Warpstreme fabric that's sweat-wicking, quick-drying, and four-way stretch. The ergonomic gusset provides freedom of movement while the classic fit works for office or gym. Available in 28-37 inch inseams with hidden zip pocket for commuters.", "price": 138, "brand": "Lululemon", "visit_timestamp": ts(21)},
            {"url": "https://www.amazon.com/Kindle-Paperwhite-16-GB-Signature/dp/B08N36XNTT", "title": "Kindle Paperwhite Signature", "activity_type": "product", "category": "Electronics", "topics": ["E-Readers"], "context": ["Reading"], "vibe": ["Literary", "Relaxed"], "inferred_needs": ["Kindle Case"], "semantic_summary": "The Kindle Paperwhite Signature Edition features a 6.8-inch 300 ppi glare-free display with adjustable warm light. It's waterproof (IPX8), offers 32GB storage for thousands of books, and includes wireless charging and auto-adjusting front light. Up to 10 weeks of battery life makes it perfect for avid readers.", "price": 189, "brand": "Amazon", "visit_timestamp": ts(22)},
            {"url": "https://www.away.com/suitcases/the-bigger-carry-on", "title": "Away Bigger Carry-On", "activity_type": "product", "category": "Luggage", "topics": ["Travel Gear"], "context": ["Travel"], "vibe": ["Stylish", "Practical"], "inferred_needs": ["Packing Cubes"], "semantic_summary": "The Away Bigger Carry-On is a hard-shell suitcase made from durable polycarbonate with an ejectable battery for phone charging. It features 360° spinner wheels, TSA-approved lock, interior compression system, and removable laundry bag. Sized to fit in most overhead bins with 47.9L capacity for extended trips.", "price": 295, "brand": "Away", "visit_timestamp": ts(23)},
            {"url": "https://www.levistrauss.com/shop/jeans/501-original-fit-jeans", "title": "Levi's 501 Original", "activity_type": "product", "category": "Clothing", "topics": ["Denim"], "context": ["Casual Wear"], "vibe": ["Classic", "Timeless"], "inferred_needs": ["Belt"], "semantic_summary": "The Levi's 501 Original Fit Jeans are the iconic button-fly denim that defined American style since 1873. Made from 100% cotton with the signature straight leg and relaxed seat. These jeans break in uniquely over time, developing personal fades and character. Available in 35+ washes from rigid to distressed.", "price": 79, "brand": "Levi's", "visit_timestamp": ts(24)},
            {"url": "https://www.oura.com/product/oura-ring-gen3", "title": "Oura Ring Gen 3", "activity_type": "product", "category": "Electronics", "topics": ["Wearables", "Health"], "context": ["Health Tracking"], "vibe": ["Minimal", "Wellness"], "inferred_needs": ["Ring Sizing Kit"], "semantic_summary": "The Oura Ring Gen 3 is a titanium smart ring that tracks sleep, activity, and recovery without a bulky wristband. It measures heart rate, HRV, body temperature, and blood oxygen. The app provides readiness scores, sleep insights, and personalized recommendations. 7-day battery life and waterproof to 100m depth.", "price": 299, "brand": "Oura", "visit_timestamp": ts(25)},
            {"url": "https://www.breville.com/us/en/products/espresso/bes870.html", "title": "Breville Barista Express", "activity_type": "product", "category": "Electronics", "topics": ["Coffee", "Kitchen"], "context": ["Coffee Enthusiast"], "vibe": ["Artisanal", "Premium"], "inferred_needs": ["Coffee Beans"], "semantic_summary": "The Breville Barista Express is an all-in-one espresso machine with integrated conical burr grinder. Features 15-bar Italian pump, PID temperature control, steam wand for microfoam milk, and dose-control grinding. The 54mm portafilter and precise extraction deliver café-quality espresso at home without the learning curve.", "price": 749, "brand": "Breville", "visit_timestamp": ts(26)},
            {"url": "https://www.nintendo.com/us/switch/oled-model/", "title": "Nintendo Switch OLED", "activity_type": "product", "category": "Electronics", "topics": ["Gaming"], "context": ["Entertainment"], "vibe": ["Fun", "Portable"], "inferred_needs": ["Switch Games"], "semantic_summary": "The Nintendo Switch OLED Model features a vibrant 7-inch OLED screen with vivid colors and sharp contrast. It includes a wide adjustable kickstand, 64GB internal storage, enhanced audio, and wired LAN port in the dock. Play the same great games at home on your TV or on the go in handheld mode.", "price": 349, "brand": "Nintendo", "visit_timestamp": ts(27)},
            {"url": "https://www.rei.com/product/171020/osprey-atmos-ag-65-pack-mens", "title": "Osprey Atmos AG 65", "activity_type": "product", "category": "Outdoor", "topics": ["Backpacking"], "context": ["Hiking Trip"], "vibe": ["Adventure", "Durable"], "inferred_needs": ["Trekking Poles"], "semantic_summary": "The Osprey Atmos AG 65 is a 65-liter backpacking pack with Anti-Gravity suspension that molds to your body. Features include Fit-on-the-Fly hipbelt and harness adjustments, integrated raincover, and Stow-on-the-Go trekking pole attachments. At 4.5 lbs, it balances load-carrying comfort with lightweight design for multi-day treks.", "price": 320, "brand": "Osprey", "visit_timestamp": ts(28)},
            {"url": "https://www.garmin.com/en-US/p/775412", "title": "Garmin Fenix 7X", "activity_type": "product", "category": "Electronics", "topics": ["Smartwatches", "Fitness"], "context": ["Outdoor Sports"], "vibe": ["Rugged", "Performance"], "inferred_needs": ["Extra Bands"], "semantic_summary": "The Garmin Fenix 7X is a rugged multisport GPS watch with a 1.4-inch sunlight-readable display with flashlight and solar charging extending battery to 37 days. Features include topo maps, ski resort maps, golf course maps, and advanced training metrics like VO2 max, training load, and recovery advisor for serious athletes.", "price": 899, "brand": "Garmin", "visit_timestamp": ts(29)},
            {"url": "https://www.tesla.com/shop/product/wall-connector", "title": "Tesla Wall Connector", "activity_type": "product", "category": "Electronics", "topics": ["EV Charging"], "context": ["Home EV"], "vibe": ["Sustainable", "Modern"], "inferred_needs": ["Installation Service"], "semantic_summary": "The Tesla Wall Connector is a home charging station delivering up to 44 miles of range per hour with 11.5kW power. It features a 24-foot cable, WiFi connectivity for over-the-air updates, and power-sharing for multiple connectors. Compatible with all Tesla vehicles and adapts to various outlet types for flexible installation.", "price": 475, "brand": "Tesla", "visit_timestamp": ts(30)},
            {"url": "https://www.aesop.com/us/p/skin/hand-and-body/resurrection-aromatique-hand-balm/", "title": "Aesop Resurrection Hand Balm", "activity_type": "product", "category": "Beauty", "topics": ["Skincare"], "context": ["Self-Care"], "vibe": ["Luxurious", "Botanical"], "inferred_needs": ["Lip Balm"], "semantic_summary": "Aesop Resurrection Aromatique Hand Balm is a rich, intensely hydrating formula with Mandarin Rind, Rosemary Leaf, and Cedar Atlas essential oils. It absorbs quickly without greasy residue, softening rough skin and cuticles. The signature citrus-woody scent and minimal amber packaging make it a staple for hand care enthusiasts.", "price": 29, "brand": "Aesop", "visit_timestamp": ts(31)},
            {"url": "https://www.bose.com/en_us/products/headphones/noise_cancelling_headphones/quietcomfort-ultra-headphones.html", "title": "Bose QuietComfort Ultra", "activity_type": "product", "category": "Electronics", "topics": ["Headphones"], "context": ["Travel"], "vibe": ["Comfortable", "Immersive"], "inferred_needs": ["Travel Case"], "semantic_summary": "The Bose QuietComfort Ultra Headphones feature Immersive Audio for spatial sound experiences and CustomTune technology that optimizes noise cancellation for your ears. With up to 24 hours of battery life, luxurious protein leather cushions, and Aware mode for transparency, they're designed for premium comfort on long flights and work sessions.", "price": 429, "brand": "Bose", "visit_timestamp": ts(32)},
            {"url": "https://www.warbyparker.com/eyeglasses/men/durand", "title": "Warby Parker Durand", "activity_type": "product", "category": "Accessories", "topics": ["Eyewear"], "context": ["Vision"], "vibe": ["Stylish", "Affordable"], "inferred_needs": ["Glasses Case"], "semantic_summary": "The Warby Parker Durand is a classic round frame handcrafted from plant-based cellulose acetate. It includes premium optical lenses with anti-reflective, scratch-resistant, and UV-blocking coatings. Home Try-On lets you test 5 frames free, and every purchase includes a pair donated through the Buy a Pair, Give a Pair program.", "price": 145, "brand": "Warby Parker", "visit_timestamp": ts(33)},
            {"url": "https://www.molecule.com/products/molecule-1-mattress", "title": "Molecule 1 Mattress", "activity_type": "product", "category": "Home", "topics": ["Sleep", "Mattress"], "context": ["Bedroom Upgrade"], "vibe": ["Supportive", "Athletic"], "inferred_needs": ["Pillows"], "semantic_summary": "The Molecule 1 Mattress uses Air-Engineered foam with microperforations for 8x better airflow than traditional memory foam. It features MolecularFlo adaptive support that responds to pressure points and recovers quickly. Developed for athletes, it's CertiPUR-US certified and comes with a 100-night trial and 5-year warranty.", "price": 899, "brand": "Molecule", "visit_timestamp": ts(34)},
        ]
        
        # ═══════════════════════════════════════════════════════════
        # 📺 CONTENT (YouTube, News - 10 entries)
        # ═══════════════════════════════════════════════════════════
        content = [
            {"url": "https://www.youtube.com/watch?v=9L7Vv3yI4M8", "title": "Marathon Training for Beginners", "activity_type": "content", "category": "Fitness", "topics": ["Running", "Marathon"], "context": ["New Runner"], "vibe": ["Inspirational"], "inferred_needs": ["Running Shoes", "GPS Watch"], "semantic_summary": "This comprehensive YouTube tutorial covers essential marathon training principles for first-time runners. Topics include building a training schedule, proper pacing strategies, nutrition and hydration during long runs, injury prevention techniques, and race day preparation. The video breaks down a 16-week training plan with weekly mileage targets and recovery protocols.", "visit_timestamp": ts(1)},
            {"url": "https://www.youtube.com/watch?v=dB7IFYIQIu8", "title": "Ultimate Home Office Setup", "activity_type": "content", "category": "Productivity", "topics": ["Home Office", "Remote Work"], "context": ["New Job"], "vibe": ["Professional"], "inferred_needs": ["Standing Desk", "Monitor"], "semantic_summary": "A detailed YouTube guide to building the ultimate home office setup for productivity and ergonomics. This video covers desk selection, monitor positioning, cable management, lighting optimization, and acoustic treatment. Includes product recommendations at various price points from budget-friendly IKEA setups to premium Herman Miller configurations.", "visit_timestamp": ts(2)},
            {"url": "https://medium.com/swlh", "title": "How I Built a SaaS Company", "activity_type": "content", "category": "Business", "topics": ["Startups", "Entrepreneurship"], "context": ["Side Project"], "vibe": ["Ambitious"], "inferred_needs": ["Business Books"], "semantic_summary": "This Medium article chronicles the journey of building a SaaS company from idea to $10M ARR. Covers topics including product-market fit discovery, early customer acquisition strategies, pricing experiments, technology stack choices, and team scaling challenges. Includes specific metrics and timelines for each growth stage.", "visit_timestamp": ts(5)},
            {"url": "https://www.nytimes.com/section/travel", "title": "36 Hours in Tokyo", "activity_type": "content", "category": "Travel", "topics": ["Japan", "Tokyo"], "context": ["Vacation Planning"], "vibe": ["Adventurous"], "inferred_needs": ["Luggage", "Travel Adapter"], "semantic_summary": "The NY Times '36 Hours in Tokyo' travel guide covers must-see attractions, local food spots, and hidden gems in Japan's capital. Includes recommendations for neighborhoods like Shibuya, Shinjuku, and Asakusa, plus practical tips on transportation, cultural etiquette, and the best times to visit popular spots like Tsukiji Outer Market.", "visit_timestamp": ts(8)},
            {"url": "https://www.youtube.com/watch?v=bJzb-RuUcMU", "title": "Cooking for Beginners", "activity_type": "content", "category": "Cooking", "topics": ["Cooking"], "context": ["Learning"], "vibe": ["Practical"], "inferred_needs": ["Knife Set", "Cookware"], "semantic_summary": "This beginner cooking tutorial teaches fundamental kitchen skills including knife techniques, basic sauce preparation, and essential cooking methods like sautéing, roasting, and braising. The video demonstrates how to properly season food, control heat levels, and time multiple dishes to serve together. Great foundation for building culinary confidence.", "visit_timestamp": ts(4)},
            {"url": "https://techcrunch.com/category/artificial-intelligence/", "title": "The Future of AI in 2024", "activity_type": "content", "category": "Technology", "topics": ["AI", "Tech Trends"], "context": ["Industry Research"], "vibe": ["Curious"], "inferred_needs": ["AI Books", "Online Courses"], "semantic_summary": "TechCrunch's coverage of the latest developments in artificial intelligence, including new model releases, startup funding rounds, and industry analysis. Articles cover topics from large language models and generative AI to robotics, autonomous vehicles, and AI regulation. Essential reading for staying current on AI technology trends.", "visit_timestamp": ts(11)},
        ]
        
        # ═══════════════════════════════════════════════════════════
        # 💼 SOCIAL (LinkedIn - 6 entries)
        # ═══════════════════════════════════════════════════════════
        social = [
            {"url": "https://www.linkedin.com/jobs/search/?keywords=software%20engineer%20stripe", "title": "Senior SWE at Stripe", "activity_type": "social", "category": "Jobs", "topics": ["Software Engineering"], "context": ["Job Hunting"], "vibe": ["Ambitious"], "inferred_needs": ["Interview Prep", "Laptop"], "semantic_summary": "LinkedIn job search results for Senior Software Engineer roles at Stripe, a leading fintech company processing billions in payments. Listings show requirements typically including 5+ years experience, expertise in distributed systems, and compensation packages ranging from $200K-$400K. Stripe is known for its engineering culture, remote-friendly policies, and equity grants.", "visit_timestamp": ts(1)},
            {"url": "https://www.linkedin.com/learning/", "title": "Python for Data Science", "activity_type": "social", "category": "Learning", "topics": ["Python", "Data Science"], "context": ["Career Pivot"], "vibe": ["Growth-Minded"], "inferred_needs": ["Python Books", "Monitor"], "semantic_summary": "LinkedIn Learning course on Python for Data Science covering pandas, NumPy, matplotlib, and scikit-learn fundamentals. This self-paced course includes hands-on projects analyzing real datasets, building visualizations, and creating machine learning models. Certificate included upon completion, typically takes 20-30 hours.", "visit_timestamp": ts(3)},
            {"url": "https://www.linkedin.com/jobs/search/?keywords=product%20manager%20google", "title": "Product Manager at Google", "activity_type": "social", "category": "Jobs", "topics": ["Product Management"], "context": ["Job Hunting"], "vibe": ["Strategic"], "inferred_needs": ["PM Books"], "semantic_summary": "LinkedIn job listings for Product Manager positions at Google, one of the most competitive PM roles in tech. Requirements typically include 3-5 years PM experience, technical background preferred, and strong analytical skills. Total compensation ranges from $250K-$450K with benefits including equity, 401k matching, and wellness programs.", "visit_timestamp": ts(10)},
        ]
        
        # ═══════════════════════════════════════════════════════════
        # ✈️ TRAVEL (4 entries)
        # ═══════════════════════════════════════════════════════════
        travel = [
            {"url": "https://www.airbnb.com/s/Tokyo--Japan/homes", "title": "Cozy Shibuya Apartment", "activity_type": "content", "category": "Travel", "topics": ["Japan", "Tokyo"], "context": ["Vacation Planning"], "vibe": ["Adventurous"], "inferred_needs": ["Luggage", "Packing Cubes"], "semantic_summary": "Airbnb listings for apartments in Tokyo's Shibuya district, one of the city's most vibrant neighborhoods known for its fashion, nightlife, and the famous Shibuya Crossing. Listings range from modern studio apartments to traditional Japanese-style rooms, with prices from $80-$250/night. Most include WiFi, kitchen facilities, and proximity to public transit.", "visit_timestamp": ts(4)},
            {"url": "https://www.zillow.com/austin-tx/", "title": "Homes for Sale in Austin", "activity_type": "content", "category": "Real Estate", "topics": ["Home Buying", "Moving"], "context": ["Moving"], "vibe": ["Decisive"], "inferred_needs": ["Moving Boxes", "Furniture"], "semantic_summary": "Zillow real estate listings for homes in Austin, Texas, one of America's fastest-growing cities known for its tech industry, live music scene, and outdoor recreation. Current listings range from $400K condos to $1.5M+ single-family homes. The market features neighborhoods like East Austin, South Congress, and the Domain area with varying price points and amenities.", "visit_timestamp": ts(2)},
        ]
        
        # Combine all entries from all activity types
        all_entries = products + content + social + travel
        
        # Prepare for Pinecone with BrowsingActivity schema
        entries_to_index = []
        products_to_sync = []
        
        for i, entry in enumerate(all_entries):
            # Build unified BrowsingActivity structure
            entry_data = {
                "id": f"seed_{i}_{now}",
                "url": entry["url"],
                "title": entry["title"],
                "domain": entry["url"].split("/")[2] if "/" in entry["url"] else "unknown",
                "visit_time": datetime.fromtimestamp(entry["visit_timestamp"]).isoformat(),
                "visit_timestamp": entry["visit_timestamp"],
                "activity_type": entry.get("activity_type", "content"),
                "category": entry.get("category", ""),
                "topics": entry.get("topics", []),
                "context": entry.get("context", []),
                "vibe": entry.get("vibe", []),
                "inferred_needs": entry.get("inferred_needs", []),
                "semantic_summary": entry.get("semantic_summary", ""),
                "price": entry.get("price"),
                "brand": entry.get("brand"),
            }
            entries_to_index.append(entry_data)
            
            # Sync product-type entries to products namespace
            if entry.get("activity_type") == "product" and entry.get("brand"):
                cat = entry.get("category", "product").lower()
                keyword = "product"
                if "shoe" in cat: keyword = "sneakers"
                elif "cloth" in cat: keyword = "fashion"
                elif "electronic" in cat: keyword = "tech"
                elif "furniture" in cat: keyword = "furniture"
                
                products_to_sync.append({
                    "id": f"seed_product_{i}_{now}",
                    "name": entry["title"],
                    "brand": entry.get("brand", ""),
                    "category": cat,
                    "price": entry.get("price", 0),
                    "description": entry.get("semantic_summary", ""),
                    "image_url": f"https://placehold.co/400x300/e2e8f0/64748b?text={entry['title'].replace(' ', '+')}",
                    "product_url": entry["url"],
                    "source": "seed_data",
                    "materials": [],
                    "occasion": entry.get("context", []),
                    "visual_characteristics": entry.get("vibe", []),
                })
        
        # Index in Pinecone (browsing namespace)
        store = get_vector_store()
        indexed_count = store.upsert_browsing_memory(entries_to_index)
        
        # Sync products
        products_synced = 0
        if products_to_sync:
            products_synced = store.upsert_products(products_to_sync)
        
        return {
            "status": "success", 
            "message": f"Seeded {len(all_entries)} diverse entries ({len(products)} products, {len(content)} content, {len(social)} social, {len(travel)} travel)",
            "entries_indexed": indexed_count,
            "products_synced": products_synced,
            "activity_breakdown": {
                "products": len(products),
                "content": len(content),
                "social": len(social),
                "travel": len(travel)
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



