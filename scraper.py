"""
Yad2 real estate scraper using Playwright with stealth.
Modular, class-based design for easy extension (e.g. Telegram notifications).
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

from config import (
    DEFAULT_SEARCH_URL,
    MIN_ROOMS,
    get_random_delay,
    get_random_user_agent,
    SELECTORS,
)

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Raised when scraping fails (block, structure change, timeout)."""
    pass


def _parse_shekel(text: Optional[str]) -> Optional[int]:
    """Parse price string like '5,500 ₪' or '5500' to int."""
    if not text or not isinstance(text, str):
        return None
    try:
        cleaned = text.replace(",", "").replace("₪", "").replace(" ", "").strip()
        return int(cleaned) if cleaned else None
    except ValueError:
        return None


def _filter_min_rooms(listings: List[Dict[str, Any]], min_rooms: int) -> List[Dict[str, Any]]:
    """Keep only listings with rooms >= min_rooms. If rooms is missing or unparseable, keep."""
    out: List[Dict[str, Any]] = []
    for item in listings:
        r = item.get("rooms")
        if not r:
            out.append(item)
            continue
        m = re.match(r"^(\d+)", str(r).strip())
        if not m:
            out.append(item)
            continue
        if int(m.group(1)) >= min_rooms:
            out.append(item)
    return out


class Yad2Scraper:
    """
    Scrapes Yad2 rent listings from a given URL.
    Uses playwright-stealth and random delays to reduce bot detection.
    """

    def __init__(
        self,
        url: str = DEFAULT_SEARCH_URL,
        headless: bool = True,
        timeout_ms: int = 30_000,
    ):
        self.url = url
        self.headless = headless
        self.timeout_ms = timeout_ms

    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Navigate to URL, wait for feed, extract listings.
        Returns list of dicts: item_id, price, address, floor, url.
        Raises on critical failures (e.g. block, structure change).
        """
        stealth = Stealth()
        listings: List[Dict[str, Any]] = []

        async with stealth.use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                context = await browser.new_context(
                    user_agent=get_random_user_agent(),
                    viewport={"width": 1920, "height": 1080},
                    locale="he-IL",
                )
                await stealth.apply_stealth_async(context)
                page = await context.new_page()
                await self._random_delay(1.0, 2.0)

                await page.goto(self.url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                await self._random_delay(2.0, 4.0)

                # If Yad2 redirected to ShieldSquare/hCaptcha, wait for user to solve it (non-headless only)
                current_url = page.url
                if "validate.perfdrive.com" in current_url or "captcha" in current_url.lower():
                    if self.headless:
                        logger.warning("Captcha detected but running headless — cannot solve. Run with --no-headless and solve captcha manually.")
                    else:
                        logger.info("Captcha detected. Please solve it in the browser window (check 'I am not a robot', then Submit). Waiting up to 2 minutes...")
                        try:
                            await page.wait_for_url(
                                lambda u: "yad2.co.il" in u and "validate." not in u,
                                timeout=120_000,
                            )
                            await self._random_delay(2.0, 4.0)
                        except PlaywrightTimeout:
                            logger.warning("Captcha was not solved in time. Proceeding with current page.")
                    current_url = page.url

                # Wait for feed or listing links or "no results"
                try:
                    await page.wait_for_selector(
                        "div.feed_item, [class*='feed_item'], [data-test-id='feed_item'], "
                        "a[href*='/realestate/item/'], "
                        "[class*='no-results'], [class*='emptyState'], .empty-state",
                        timeout=15_000,
                    )
                except PlaywrightTimeout:
                    logger.warning("Timeout waiting for feed or empty state. Proceeding with current DOM.")
                await self._random_delay(0.5, 1.5)

                listings = await self._extract_listings(page)
                if not listings:
                    listings = await self._extract_listings_fallback(page)
                # Exclude listings with fewer than MIN_ROOMS (e.g. 3-room when we want 4+)
                listings = _filter_min_rooms(listings, MIN_ROOMS)
            finally:
                await browser.close()

        return listings

    async def _random_delay(self, min_sec: float, max_sec: float) -> None:
        await asyncio.sleep(get_random_delay(min_sec, max_sec))

    async def _extract_listings(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract listing rows from page.
        Uses configurable selectors; tolerates missing optional fields.
        """
        results: List[Dict[str, Any]] = []
        feed_selector = SELECTORS["feed_item"]
        try:
            items = await page.query_selector_all(feed_selector)
        except Exception as e:
            logger.error("Failed to query feed items (selector may have changed): %s", e)
            raise ScraperError("Feed structure may have changed or request was blocked.") from e

        # Filter out non-listing elements (e.g. empty-state could match a generic class)
        for elem in items:
            tag = await elem.get_attribute("class") or ""
            if "empty" in tag.lower() or "no-results" in tag.lower():
                continue
            item_id = await elem.get_attribute(SELECTORS["item_id"])
            if not item_id:
                continue
            record = await self._parse_feed_item(elem, item_id)
            if record:
                results.append(record)

        return results

    async def _extract_listings_fallback(self, page: Page) -> List[Dict[str, Any]]:
        """
        Fallback: find listing links (a[href*='/realestate/item/']) and extract id, price, address from container.
        Handles current Yad2 structure where item-id may be missing and URLs are /realestate/item/{area}/{slug}.
        """
        results: List[Dict[str, Any]] = []
        seen: set = set()
        try:
            links = await page.query_selector_all(SELECTORS["listing_link"])
        except Exception as e:
            logger.debug("Fallback listing links failed: %s", e)
            return results
        for link in links:
            try:
                href = await link.get_attribute("href") or ""
                if "realestate/item/" not in href or "project/" in href or "newprojects" in href:
                    continue
                # Extract slug: .../realestate/item/area/SLUG or .../item/area/SLUG?...
                parts = href.split("?")[0].rstrip("/").split("/")
                slug = parts[-1] if len(parts) >= 2 else None
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                full_url = href if href.startswith("http") else f"https://www.yad2.co.il{href}"
                # Get container text (card that has address + price)
                try:
                    text = await link.evaluate("""
                        el => {
                            const c = el.closest('article') || el.closest('[class*=\"feed\"]') || el.closest('[class*=\"Feed\"]') || el.parentElement?.parentElement?.parentElement || el.parentElement;
                            return c ? c.innerText || c.textContent || '' : (el.innerText || '');
                        }
                    """)
                except Exception:
                    text = await link.inner_text()
                if not isinstance(text, str):
                    text = str(text or "")
                price = _parse_shekel(text)
                if not price:
                    price_match = re.search(r"₪\s*([\d,]+)", text)
                    if price_match:
                        price = _parse_shekel(price_match.group(0))
                # Rooms: "4 חדרים" or "3-4 חדרים"
                rooms = ""
                rooms_m = re.search(r"(\d+(?:\s*[-–]\s*\d+)?)\s*חדרים?", text)
                if rooms_m:
                    rooms = rooms_m.group(1).strip()
                # Sqm: "90 מ״ר" or "90 מ''ר"
                sqm = ""
                sqm_m = re.search(r"(\d+)\s*מ[\"']?ר", text)
                if sqm_m:
                    sqm = sqm_m.group(1).strip()
                # Floor
                floor = ""
                floor_m = re.search(r"קומה\s*(\d+(?:\s*מתוך\s*\d+)?)", text, re.IGNORECASE)
                if floor_m:
                    floor = floor_m.group(1).strip()
                # Address: find Hebrew text lines that aren't price/rooms/sqm/floor
                address = ""
                addr_parts = []
                for line in text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if re.search(r"₪|/חודש|/month", line):
                        continue
                    if re.search(r"^\d[\d,]*$", line):
                        continue
                    if re.search(r"חדרים?|מ[\"׳]?ר|קומה|חניה|ממ[\"׳]?ד|מעלית|הצג|שמור|דיווח|צור קשר", line):
                        continue
                    if re.search(r"[֐-׿]", line) and len(line) > 3:
                        addr_parts.append(line)
                        if len(addr_parts) >= 2:
                            break
                if addr_parts:
                    address = ", ".join(addr_parts[:2])
                elif text:
                    address = text.strip().split("\n")[0][:120]
                # Phone: sometimes in feed as "הצג מספר" or digits; leave empty if not found
                phone = ""
                phone_m = re.search(r"0\d[\d\s\-]{7,}", text)
                if phone_m:
                    phone = re.sub(r"\s+", "", phone_m.group(0))[:14]
                results.append({
                    "item_id": slug,
                    "price": price,
                    "address": address or "—",
                    "floor": floor,
                    "rooms": rooms,
                    "sqm": sqm,
                    "phone": phone,
                    "url": full_url,
                })
            except Exception as e:
                logger.debug("Fallback skip link: %s", e)
                continue
        if results:
            logger.info("Extracted %d listings via fallback (listing links).", len(results))
        return results

    async def _parse_feed_item(self, elem: Any, item_id: str) -> Optional[Dict[str, Any]]:
        """Parse a single feed item element into record dict."""
        try:
            price_el = await elem.query_selector(SELECTORS["item_price"])
            price_text = await price_el.inner_text() if price_el else None
            price = _parse_shekel(price_text)

            rows_el = await elem.query_selector(SELECTORS["item_rows"])
            address = ""
            floor = ""
            if rows_el:
                children = await rows_el.query_selector_all(SELECTORS["row_children"])
                if children:
                    address = (await children[0].inner_text()).strip() if children else ""
                # Try to find floor in remaining text (e.g. "קומה 3" or "קומה 2 מתוך 5")
                full_rows = (await rows_el.inner_text()).strip()
                floor_match = re.search(r"קומה\s*(\d+(?:\s*מתוך\s*\d+)?)", full_rows, re.IGNORECASE)
                if floor_match:
                    floor = floor_match.group(1).strip()

            url = f"https://www.yad2.co.il/item/{item_id}"
            full_rows = await rows_el.inner_text() if rows_el else ""
            rooms = ""
            rooms_m = re.search(r"(\d+(?:\s*[-–]\s*\d+)?)\s*חדרים?", full_rows)
            if rooms_m:
                rooms = rooms_m.group(1).strip()
            sqm = ""
            sqm_m = re.search(r"(\d+)\s*מ[\"']?ר", full_rows)
            if sqm_m:
                sqm = sqm_m.group(1).strip()
            phone = ""

            return {
                "item_id": item_id,
                "price": price,
                "address": address or "",
                "floor": floor,
                "rooms": rooms,
                "sqm": sqm,
                "phone": phone,
                "url": url,
            }
        except Exception as e:
            logger.debug("Skip item %s: %s", item_id, e)
            return None
