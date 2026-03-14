"""
Configuration for Yad2 real estate monitor.
Centralized selectors and settings for easy maintenance when site structure changes.
"""

import random
from typing import List

# Target search URL (legacy single-URL mode)
DEFAULT_SEARCH_URL = (
    "https://www.yad2.co.il/realestate/rent"
    "?city=6600&neighborhood=267&rooms=4-6&price=0-10000&parking=1&shelter=1"
)

# Multiple search sources: run both and merge results
SEARCH_SOURCES = [
    {
        "key": "tel-aviv-area",
        "label": "אגרובנק חולון",
        "url": "https://www.yad2.co.il/realestate/rent/tel-aviv-area?maxPrice=15000&minRooms=4&parking=1&shelter=1&area=11&city=6600&neighborhood=793",
    },
    {
        "key": "center-and-sharon",
        "label": "מזרח ראשון לציון",
        "url": "https://www.yad2.co.il/realestate/rent/center-and-sharon?maxPrice=10000&minRooms=4&parking=1&shelter=1&multiNeighborhood=470%2C991420%2C991421",
    },
]

# Minimum rooms to keep (listings with fewer are excluded from report)
MIN_ROOMS = 4

# Scheduler
CHECK_INTERVAL_MINUTES = 10
FULL_REPORT_INTERVAL_HOURS = 24
# Active window: only run scrape between these hours (local time). 6 AM - midnight.
ACTIVE_HOURS_START = 6   # 06:00
ACTIVE_HOURS_END = 24    # 24:00 (midnight); use 24 to include full day until midnight

# CSS selectors - update these if Yad2 changes DOM structure
SELECTORS = {
    "feed_item": "div.feed_item, [class*='feed_item'], [data-test-id='feed_item']",
    "item_id": "item-id",  # attribute on feed_item container
    "item_price": "[data-test-id='item_price'], .item_price, [class*='price']",
    "item_rows": ".rows",  # contains address/floor info
    "row_children": ".rows > *",  # first child often address
    # Fallback: listing links (current Yad2 URL format)
    "listing_link": "a[href*='/realestate/item/']",
}

# Random User-Agent pool (real browser strings)
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_random_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> float:
    return random.uniform(min_sec, max_sec)
