import os
import json
import time
import logging
from typing import Dict, Optional, Union, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Path to the cache file
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'price_cache.json')
# Create the data directory if it doesn't exist
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

class PriceCache:
    """Service for caching stock prices to avoid unnecessary API calls"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.load_cache()
    
    def load_cache(self):
        """Load cached prices from the JSON file"""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    self.cache = json.load(f)
                    logger.info(f"Loaded price cache with {len(self.cache)} symbols")
            else:
                logger.info("No cache file found, creating a new one")
                self.cache = {}
                self.save_cache()
        except Exception as e:
            logger.error(f"Error loading price cache: {str(e)}")
            self.cache = {}
    
    def save_cache(self):
        """Save current cache to the JSON file"""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Saved price cache with {len(self.cache)} symbols")
        except Exception as e:
            logger.error(f"Error saving price cache: {str(e)}")
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get a price from the cache if it exists"""
        symbol = symbol.upper()
        if symbol in self.cache:
            cached_data = self.cache[symbol]
            # Include the timestamp in the return for debugging/display
            return cached_data.get('price')
        return None
    
    def get_price_with_timestamp(self, symbol: str) -> Dict[str, Any]:
        """Get a price and its timestamp from the cache"""
        symbol = symbol.upper()
        if symbol in self.cache:
            return self.cache[symbol]
        return {"price": None, "timestamp": None, "source": None}
    
    def set_price(self, symbol: str, price: float, source: str = "unknown"):
        """Add or update a price in the cache"""
        symbol = symbol.upper()
        self.cache[symbol] = {
            "price": price,
            "timestamp": time.time(),
            "timestamp_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source
        }
        # Save immediately to ensure we don't lose data
        self.save_cache()
    
    def clear_cache(self):
        """Clear all cached prices"""
        self.cache = {}
        self.save_cache()
    
    def is_cache_stale(self, symbol: str, max_age_hours: int = 24) -> bool:
        """Check if cached data for a symbol is older than max_age_hours"""
        symbol = symbol.upper()
        if symbol not in self.cache:
            return True
            
        cached_time = self.cache[symbol].get('timestamp')
        if cached_time is None:
            return True
            
        # Check if the cache is older than max_age_hours
        current_time = time.time()
        cache_age_seconds = current_time - cached_time
        return cache_age_seconds > (max_age_hours * 3600)
    
    def get_all_cached_prices(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached prices"""
        return self.cache

# Create a singleton instance
price_cache = PriceCache() 