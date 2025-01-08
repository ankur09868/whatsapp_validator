import threading
from cachetools import TTLCache
from threading import Lock
import pandas as pd

class SharedStateManager:
    def __init__(self):
        self.qr_detected_event = threading.Event()
        self.qr_code_cache = TTLCache(maxsize=100, ttl=60)  # Cache with TTL of 60 seconds
        self.lock = Lock()  # Lock to ensure thread-safe access to the cache
        self.data_cache = None  # To store the cached dataset

    def set_qr_detected(self, qr_code_text):
        """Add QR code to memory cache (thread-safe)."""
        with self.lock:  # Ensure only one thread can access at a time
            self.qr_code_cache[qr_code_text] = True  # Add QR code to cache
        self.qr_detected_event.set()

    def clear_qr_detected(self):
        """Clear the QR code cache and event (thread-safe)."""
        with self.lock:  # Ensure only one thread can clear the cache at a time
            self.qr_code_cache.clear()
        self.qr_detected_event.clear()

    def get_all_qr_codes(self):
        """Get all QR codes from the cache (thread-safe)."""
        with self.lock:  # Ensure only one thread can access at a time
            return list(self.qr_code_cache.keys())  # Return all QR codes in cache

    def clear_cache_only(self):
        """Clear only the cache without affecting the event (thread-safe)."""
        with self.lock:
            self.qr_code_cache.clear()

    def cache_data(self, data: pd.DataFrame):
        """Cache the full dataset (thread-safe)."""
        with self.lock:
            self.data_cache = data  # Store the full data

    def get_cached_data(self):
        """Get the cached dataset (thread-safe)."""
        with self.lock:
            return self.data_cache  # Return the cached data

    def clear_data_cache(self):
        """Clear the data cache (thread-safe)."""
        with self.lock:
            self.data_cache = None


# Create a shared instance
shared_state = SharedStateManager()
