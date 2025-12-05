"""
Mock Data Generator

Generates realistic mock shopping data for testing without API calls.
Useful for development and testing the RAG pipeline.
"""
from datetime import datetime, timedelta
import random
from typing import List
import uuid

from app.models.browsing import BrowsingHistoryEntry, ProductInfo, ShoppingIntent
from app.models.product import Product, ProductCategory


class MockDataGenerator:
    """Generate realistic mock shopping data"""
    
    # Shopping personas with different patterns
    SHOPPING_PATTERNS = {
        "sneaker_enthusiast": {
            "categories": [ProductCategory.SHOES],
            "brands": ["Nike", "Adidas", "New Balance", "Allbirds", "Vans"],
            "price_range": (80, 220),
            "stores": ["nike.com", "allbirds.com", "finishline.com"]
        },
        "fashion_conscious": {
            "categories": [ProductCategory.CLOTHING, ProductCategory.ACCESSORIES],
            "brands": ["Everlane", "Madewell", "Bonobos", "Reformation"],
            "price_range": (40, 180),
            "stores": ["everlane.com", "madewell.com", "nordstrom.com"]
        },
        "fitness_focused": {
            "categories": [ProductCategory.FITNESS, ProductCategory.SHOES],
            "brands": ["Gymshark", "Lululemon", "Nike", "Under Armour"],
            "price_range": (30, 120),
            "stores": ["gymshark.com", "lululemon.com", "nike.com"]
        },
        "outdoor_adventurer": {
            "categories": [ProductCategory.OUTDOOR, ProductCategory.SHOES],
            "brands": ["Patagonia", "The North Face", "REI", "Arc'teryx"],
            "price_range": (60, 350),
            "stores": ["patagonia.com", "rei.com", "backcountry.com"]
        }
    }
    
    PRODUCT_NAMES = {
        ProductCategory.SHOES: [
            "Runner Pro", "Trail Master", "Classic Slip-On", "Boost Ultra",
            "Air Max Cloud", "Everyday Walker", "Performance Runner"
        ],
        ProductCategory.CLOTHING: [
            "Essential Tee", "Slim Fit Chinos", "Oxford Shirt", "Cashmere Sweater",
            "Denim Jacket", "Linen Shorts", "Performance Polo"
        ],
        ProductCategory.FITNESS: [
            "Training Shorts", "Flex Leggings", "Performance Tank",
            "Compression Tights", "Mesh Running Top", "Gym Hoodie"
        ],
        ProductCategory.ACCESSORIES: [
            "Canvas Backpack", "Leather Belt", "Classic Watch",
            "Sunglasses Pro", "Beanie Hat", "Travel Wallet"
        ],
        ProductCategory.OUTDOOR: [
            "Hiking Jacket", "Trail Pack", "Camping Tent", "Insulated Vest",
            "Rain Shell", "Trekking Poles", "Down Parka"
        ],
        ProductCategory.EYEWEAR: [
            "Classic Frames", "Blue Light Blockers", "Aviator Sunglasses",
            "Round Readers", "Sport Goggles"
        ]
    }
    
    @classmethod
    def generate_browsing_history(
        cls,
        pattern: str = "sneaker_enthusiast",
        num_entries: int = 15
    ) -> List[BrowsingHistoryEntry]:
        """
        Generate mock browsing history based on shopping pattern
        
        Args:
            pattern: One of the SHOPPING_PATTERNS keys
            num_entries: Number of entries to generate
        
        Returns:
            List of BrowsingHistoryEntry objects
        """
        pattern_data = cls.SHOPPING_PATTERNS.get(pattern)
        if not pattern_data:
            pattern_data = cls.SHOPPING_PATTERNS["sneaker_enthusiast"]
        
        entries = []
        base_time = datetime.now() - timedelta(days=30)
        
        for i in range(num_entries):
            brand = random.choice(pattern_data["brands"])
            category = random.choice(pattern_data["categories"])
            price = round(random.uniform(*pattern_data["price_range"]), 2)
            store = random.choice(pattern_data["stores"])
            
            # Generate product name
            product_names = cls.PRODUCT_NAMES.get(category, ["Product"])
            product_name = f"{brand} {random.choice(product_names)}"
            
            # Random visit time within the past 30 days
            visit_time = base_time + timedelta(
                days=random.randint(0, 29),
                hours=random.randint(8, 22),
                minutes=random.randint(0, 59)
            )
            
            entry = BrowsingHistoryEntry(
                id=str(uuid.uuid4()),
                url=f"https://{store}/products/{product_name.lower().replace(' ', '-')}-{random.randint(100, 999)}",
                title=f"{product_name} | {store.split('.')[0].title()}",
                visit_time=visit_time,
                visit_count=random.randint(1, 4),
                product=ProductInfo(
                    name=product_name,
                    price=price,
                    currency="USD",
                    category=category.value,
                    brand=brand,
                    description=f"Premium {category.value} from {brand}. Perfect for everyday wear.",
                    availability="in_stock"
                ),
                intent=random.choice(list(ShoppingIntent)),
                domain=store,
                is_ecommerce=True
            )
            entries.append(entry)
        
        # Sort by visit time (most recent first)
        entries.sort(key=lambda x: x.visit_time, reverse=True)
        return entries
    
    @classmethod
    def generate_products(cls, num_products: int = 25) -> List[Product]:
        """
        Generate mock product catalog
        
        Args:
            num_products: Number of products to generate
        
        Returns:
            List of Product objects
        """
        products = []
        patterns = list(cls.SHOPPING_PATTERNS.values())
        
        for i in range(num_products):
            pattern = random.choice(patterns)
            brand = random.choice(pattern["brands"])
            category = random.choice(pattern["categories"])
            price = round(random.uniform(*pattern["price_range"]), 2)
            store = random.choice(pattern["stores"])
            
            product_names = cls.PRODUCT_NAMES.get(category, ["Product"])
            product_name = f"{brand} {random.choice(product_names)}"
            
            product = Product(
                id=str(uuid.uuid4()),
                name=product_name,
                price=price,
                currency="USD",
                category=category,
                brand=brand,
                description=f"High-quality {category.value} featuring premium materials and modern design. {brand}'s commitment to excellence.",
                image_url=f"https://picsum.photos/seed/{i}/400/400",
                product_url=f"https://{store}/products/{product_name.lower().replace(' ', '-')}-{random.randint(100, 999)}",
                store_name=store.split(".")[0].title(),
                tags=[category.value, brand.lower(), "premium", "new"],
                variants=["S", "M", "L", "XL"] if category in [ProductCategory.CLOTHING, ProductCategory.FITNESS] else [],
                availability="in_stock"
            )
            products.append(product)
        
        return products
    
    @classmethod
    def generate_mixed_history(cls, num_entries: int = 20) -> List[BrowsingHistoryEntry]:
        """Generate browsing history with mixed shopping patterns"""
        entries = []
        patterns = list(cls.SHOPPING_PATTERNS.keys())
        
        for pattern in patterns:
            count = num_entries // len(patterns)
            entries.extend(cls.generate_browsing_history(pattern, count))
        
        # Sort by time and return
        entries.sort(key=lambda x: x.visit_time, reverse=True)
        return entries[:num_entries]
