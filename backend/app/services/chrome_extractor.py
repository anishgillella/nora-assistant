"""
Chrome History Extractor

Extracts browsing history from Chrome/Chromium SQLite database.
Supports: Chrome, Brave, Arc, Comet, and other Chromium browsers.
"""
import sqlite3
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.browsing import ChromeHistoryRaw
from app.utils.config import get_settings


class ChromeHistoryExtractor:
    """Extract browsing history from Chrome/Chromium SQLite database"""
    
    # Possible browser history paths (ordered by preference)
    BROWSER_PATHS = [
        os.path.expanduser("~/Library/Application Support/Comet/Default/History"),
        os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/History"),
        os.path.expanduser("~/Library/Application Support/Google/Chrome/Profile 1/History"),
        os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History"),
        os.path.expanduser("~/Library/Application Support/Arc/User Data/Default/History"),
    ]
    
    # Common e-commerce domains to filter for
    ECOMMERCE_DOMAINS = [
        "amazon.com", "ebay.com", "shopify.com", "etsy.com",
        "nike.com", "adidas.com", "nordstrom.com", "target.com",
        "walmart.com", "bestbuy.com", "allbirds.com", "gymshark.com",
        "warbyparker.com", "bonobos.com", "madewell.com", "zappos.com",
        "asos.com", "urbanoutfitters.com", "anthropologie.com",
    ]
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or self._find_history_file()
        self.settings = get_settings()
    
    @classmethod
    def _find_history_file(cls) -> Optional[str]:
        """Find the most recently modified browser history file"""
        best_path = None
        best_mtime = 0
        
        for path in cls.BROWSER_PATHS:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                if mtime > best_mtime:
                    best_mtime = mtime
                    best_path = path
        
        return best_path
        
    def extract(
        self, 
        days_back: int = 30,
        limit: int = None,
        ecommerce_only: bool = True
    ) -> List[ChromeHistoryRaw]:
        """
        Extract browsing history from Chrome
        
        Args:
            days_back: How many days of history to fetch
            limit: Max number of URLs to return (defaults to settings.max_chrome_urls)
            ecommerce_only: Filter for e-commerce sites only
        
        Returns:
            List of ChromeHistoryRaw entries
        """
        limit = limit or self.settings.max_chrome_urls
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Chrome history not found at {self.db_path}")
        
        # Create a copy to avoid database lock issues
        temp_db = "/tmp/chrome_history_copy.db"
        shutil.copy2(self.db_path, temp_db)
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Chrome timestamp is microseconds since 1601-01-01
        chrome_epoch = datetime(1601, 1, 1)
        cutoff_time = int(
            (datetime.now() - timedelta(days=days_back) - chrome_epoch).total_seconds() * 1_000_000
        )
        
        query = """
        SELECT 
            urls.id,
            urls.url,
            urls.title,
            urls.last_visit_time,
            urls.visit_count
        FROM urls
        WHERE urls.last_visit_time > ?
        ORDER BY urls.last_visit_time DESC
        LIMIT ?
        """
        
        # Get more results than needed to allow for filtering
        cursor.execute(query, (cutoff_time, limit * 10))
        rows = cursor.fetchall()
        conn.close()
        
        # Clean up temp file
        os.remove(temp_db)
        
        results = []
        for row in rows:
            if len(results) >= limit:
                break
                
            entry = ChromeHistoryRaw(
                id=row[0],
                url=row[1],
                title=row[2] or "",
                last_visit_time=row[3],
                visit_count=row[4]
            )
            
            # Filter for e-commerce if requested
            if ecommerce_only:
                if any(domain in entry.url.lower() for domain in self.ECOMMERCE_DOMAINS):
                    results.append(entry)
            else:
                results.append(entry)
        
        return results
    
    @staticmethod
    def chrome_time_to_datetime(chrome_time: int) -> datetime:
        """Convert Chrome timestamp (microseconds since 1601) to Python datetime"""
        chrome_epoch = datetime(1601, 1, 1)
        return chrome_epoch + timedelta(microseconds=chrome_time)
    
    def get_all_history(self, days_back: int = 30, limit: int = 100) -> List[ChromeHistoryRaw]:
        """Get all browsing history without e-commerce filter"""
        return self.extract(days_back=days_back, limit=limit, ecommerce_only=False)
