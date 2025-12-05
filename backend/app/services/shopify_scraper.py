"""
Shopify Product Scraper

Scrapes products from Shopify stores via their /products.json endpoint.
Limited to testing quantities to reduce costs.
"""
import httpx
from typing import List, Optional, Dict
from app.models.product import ShopifyProductRaw, Product, ProductCategory
from app.utils.config import get_settings
from bs4 import BeautifulSoup


class ShopifyScraper:
    """Scrape products from Shopify stores using /products.json endpoint"""
    
    # Store configurations with domains and categories - Target: ~100 products
    SHOPIFY_STORES = [
        # Shoes
        {"domain": "allbirds.com", "category": ProductCategory.SHOES, "name": "Allbirds"},
        {"domain": "greats.com", "category": ProductCategory.SHOES, "name": "Greats"},
        {"domain": "koio.co", "category": ProductCategory.SHOES, "name": "Koio"},
        # Fitness
        {"domain": "gymshark.com", "category": ProductCategory.FITNESS, "name": "Gymshark"},
        {"domain": "outdoorvoices.com", "category": ProductCategory.FITNESS, "name": "Outdoor Voices"},
        {"domain": "girlfriend.com", "category": ProductCategory.FITNESS, "name": "Girlfriend Collective"},
        # Clothing
        {"domain": "tentree.com", "category": ProductCategory.CLOTHING, "name": "Tentree"},
        {"domain": "everlane.com", "category": ProductCategory.CLOTHING, "name": "Everlane"},
        {"domain": "marinelayer.com", "category": ProductCategory.CLOTHING, "name": "Marine Layer"},
        # Outdoor
        {"domain": "cotopaxi.com", "category": ProductCategory.OUTDOOR, "name": "Cotopaxi"},
        {"domain": "rumpl.com", "category": ProductCategory.OUTDOOR, "name": "Rumpl"},
        # Accessories
        {"domain": "mvmt.com", "category": ProductCategory.ACCESSORIES, "name": "MVMT"},
        {"domain": "away.com", "category": ProductCategory.ACCESSORIES, "name": "Away"},
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.Client(
            timeout=20.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            }
        )
    
    def scrape_store(
        self, 
        domain: str, 
        max_products: int = None
    ) -> List[ShopifyProductRaw]:
        """
        Scrape products from a single Shopify store
        
        Args:
            domain: Store domain (e.g., "allbirds.com")
            max_products: Maximum products to fetch (defaults to settings limit)
        
        Returns:
            List of raw Shopify products
        """
        max_products = max_products or self.settings.max_shopify_products_per_store
        products = []
        page = 1
        
        while len(products) < max_products:
            try:
                url = f"https://{domain}/products.json?page={page}&limit=50"
                response = self.client.get(url)
                
                if response.status_code != 200:
                    print(f"⚠️ Got status {response.status_code} from {domain}")
                    break
                
                data = response.json()
                page_products = data.get("products", [])
                
                if not page_products:
                    break
                
                for p in page_products:
                    if len(products) >= max_products:
                        break
                    try:
                        raw = ShopifyProductRaw(
                            id=p["id"],
                            title=p["title"],
                            body_html=p.get("body_html"),
                            vendor=p.get("vendor", "Unknown"),
                            product_type=p.get("product_type"),
                            handle=p.get("handle"),
                            tags=p.get("tags"),
                            variants=p.get("variants", []),
                            images=p.get("images", [])
                        )
                        products.append(raw)
                    except Exception as e:
                        print(f"⚠️ Error parsing product: {e}")
                        continue
                
                page += 1
            except Exception as e:
                print(f"❌ Error scraping {domain}: {e}")
                break
        
        return products
    
    def scrape_all_stores(
        self, 
        max_stores: int = None,
        products_per_store: int = None
    ) -> Dict[str, List[ShopifyProductRaw]]:
        """
        Scrape products from all configured stores
        
        Args:
            max_stores: Maximum number of stores to scrape
            products_per_store: Products per store
        
        Returns:
            Dict mapping store name to list of products
        """
        max_stores = max_stores or self.settings.max_shopify_stores
        products_per_store = products_per_store or self.settings.max_shopify_products_per_store
        
        results = {}
        stores_to_scrape = self.SHOPIFY_STORES[:max_stores]
        
        for store in stores_to_scrape:
            domain = store["domain"]
            name = store["name"]
            print(f"🛒 Scraping {name} ({domain})...")
            
            products = self.scrape_store(domain, products_per_store)
            results[name] = products
            print(f"   ✅ Got {len(products)} products from {name}")
        
        return results
    
    def convert_to_product(
        self, 
        raw: ShopifyProductRaw, 
        store_name: str,
        store_domain: str,
        default_category: ProductCategory
    ) -> Optional[Product]:
        """Convert raw Shopify product to structured Product model"""
        try:
            # Get price from first variant
            price = 0.0
            if raw.variants:
                price_str = raw.variants[0].get("price", "0")
                price = float(price_str) if price_str else 0.0
            
            # Get image URL
            image_url = None
            if raw.images:
                image_url = raw.images[0].get("src")
            
            # Clean description
            description = ""
            if raw.body_html:
                soup = BeautifulSoup(raw.body_html, "html.parser")
                description = soup.get_text(separator=" ", strip=True)[:500]
            
            # Build product URL
            product_url = f"https://{store_domain}/products/{raw.handle}" if raw.handle else f"https://{store_domain}"
            
            # Parse tags - already a list from Shopify
            tags = []
            if raw.tags:
                tags = [t.strip() for t in raw.tags if isinstance(t, str) and t.strip()]
            
            # Get variants
            variants = []
            for v in raw.variants[:5]:  # Limit variants
                title = v.get("title", "")
                if title and title != "Default Title":
                    variants.append(title)
            
            return Product(
                name=raw.title,
                price=price,
                category=default_category,
                brand=raw.vendor,
                description=description or f"Product from {store_name}",
                image_url=image_url,
                product_url=product_url,
                store_name=store_name,
                tags=tags[:10],  # Limit tags
                variants=variants,
                metadata={"shopify_id": raw.id, "product_type": raw.product_type}
            )
        except Exception as e:
            print(f"❌ Error converting product: {e}")
            return None
    
    def scrape_and_convert_all(self) -> List[Product]:
        """Scrape all stores and convert to structured Product models"""
        all_products = []
        raw_results = self.scrape_all_stores()
        
        for store in self.SHOPIFY_STORES[:self.settings.max_shopify_stores]:
            name = store["name"]
            domain = store["domain"]
            category = store["category"]
            
            if name in raw_results:
                for raw in raw_results[name]:
                    product = self.convert_to_product(raw, name, domain, category)
                    if product:
                        all_products.append(product)
        
        print(f"\n📦 Total products scraped: {len(all_products)}")
        return all_products
    
    def close(self):
        """Close HTTP client"""
        self.client.close()
