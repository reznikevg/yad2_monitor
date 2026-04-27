"""
Notification abstraction for scraped changes.
Console, Telegram (Bot API), and Webhook (e.g. WhatsApp gateway) implementations.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

# Telegram Bot API message length limit
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


class BaseNotifier(ABC):
    """Abstract notifier. Implement send() for Console, Telegram, etc."""

    @abstractmethod
    def send_new_listing(self, listing: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def send_price_change(self, listing: Dict[str, Any]) -> None:
        pass

    def send_changes(
        self,
        new_listings: List[Dict[str, Any]],
        price_changed_listings: List[Dict[str, Any]],
    ) -> None:
        for item in new_listings:
            try:
                self.send_new_listing(item)
            except Exception as e:
                logger.exception("Notifier failed for new listing %s: %s", item.get("item_id"), e)
        for item in price_changed_listings:
            try:
                self.send_price_change(item)
            except Exception as e:
                logger.exception("Notifier failed for price change %s: %s", item.get("item_id"), e)

    def send_full_report(self, sources_with_listings: List[Dict[str, Any]]) -> None:
        """Send once-per-day summary of all current listings (all sources). Default: no-op override in subclasses."""
        pass

    def send_test(self) -> None:
        """Send a short test message to verify the channel works. Default: no-op."""
        pass


class ConsoleNotifier(BaseNotifier):
    """Prints clear summary to console (Hebrew-friendly)."""

    def send_new_listing(self, listing: Dict[str, Any]) -> None:
        addr = listing.get("address") or "לא צוין"
        price = listing.get("price")
        price_str = f"{price:,} ₪" if isinstance(price, int) else str(price)
        floor = listing.get("floor") or ""
        floor_str = f", קומה {floor}" if floor else ""
        print(f"[חדש] נמצאת מודעה חדשה ב{addr}{floor_str} במחיר {price_str}")

    def send_price_change(self, listing: Dict[str, Any]) -> None:
        addr = listing.get("address") or "לא צוין"
        prev = listing.get("previous_price")
        curr = listing.get("price")
        prev_str = f"{prev:,} ₪" if isinstance(prev, int) else str(prev)
        curr_str = f"{curr:,} ₪" if isinstance(curr, int) else str(curr)
        print(f"[שינוי מחיר] מודעה ב{addr}: היה {prev_str} → כעת {curr_str}")

    def send_full_report(self, sources_with_listings: List[Dict[str, Any]]) -> None:
        """Print daily summary of all listings to console."""
        print("\n" + "=" * 60)
        print("[דיווח יומי] סיכום כל המודעות")
        print("=" * 60)
        for block in sources_with_listings:
            label = block.get("label", block.get("source_key", ""))
            listings = block.get("listings") or []
            print(f"\n--- {label} ({len(listings)} מודעות) ---")
            for item in listings:
                addr = item.get("address") or "לא צוין"
                price = item.get("price")
                price_str = f"{price:,} ₪" if isinstance(price, int) else str(price)
                floor = item.get("floor") or ""
                floor_str = f", קומה {floor}" if floor else ""
                rooms = item.get("rooms") or ""
                rooms_str = f", {rooms} חדרים" if rooms else ""
                sqm = item.get("sqm") or ""
                sqm_str = f", {sqm} מ״ר" if sqm else ""
                phone = item.get("phone") or ""
                phone_str = f" | טל׳ {phone}" if phone else ""
                url = item.get("url") or ""
                print(f"  • {addr}{floor_str}{rooms_str}{sqm_str} — {price_str}{phone_str}")
                if url:
                    print(f"    {url}")
        print("=" * 60 + "\n")

    def send_test(self) -> None:
        print("[בדיקה] ערוץ קונסול פעיל – Yad2 Monitor.")


def _format_listing_line(item: Dict[str, Any]) -> str:
    """Single line for one listing (Hebrew) – address, rooms, sqm, floor, price, phone, link."""
    addr = item.get("address") or "לא צוין"
    price = item.get("price")
    price_str = f"{price:,} ₪" if isinstance(price, int) else str(price or "-")
    floor = item.get("floor") or ""
    floor_str = f", קומה {floor}" if floor else ""
    rooms = item.get("rooms") or ""
    rooms_str = f", {rooms} חדרים" if rooms else ""
    sqm = item.get("sqm") or ""
    sqm_str = f", {sqm} מ״ר" if sqm else ""
    phone = item.get("phone") or ""
    phone_str = f" | טל׳ {phone}" if phone else ""
    url = item.get("url") or ""
    line = f"• {addr}{floor_str}{rooms_str}{sqm_str} — {price_str}{phone_str}"
    if url:
        line += f"\n  🔗 {url}"
    return line


def _format_listing_card(item: Dict[str, Any], status: str = "חדש") -> str:
    """Rich card format for new/changed listing notification."""
    from datetime import datetime
    addr = item.get("address") or "לא צוין"
    price = item.get("price")
    price_str = f"₪{price:,}/חודש" if isinstance(price, int) else str(price or "-")
    rooms = item.get("rooms") or ""
    sqm = item.get("sqm") or ""
    floor = item.get("floor") or ""
    url = item.get("url") or ""
    source_label = item.get("_source_label") or ""
    total_in_db = item.get("_total_in_db") or 0

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"🏠 Yad2 Monitor | {ts}", ""]
    if source_label:
        lines.append(f"📍 {source_label}")
    icon = "✅" if status == "חדש" else "💰"
    lines.append(f"{icon} {status}:")
    detail_parts = []
    if rooms:
        detail_parts.append(f"{rooms} חדרים")
    if sqm:
        detail_parts.append(f"{sqm} מ\"ר")
    if floor:
        detail_parts.append(f"קומה {floor}")
    detail_parts.append(price_str)
    lines.append(f"• {addr}")
    if detail_parts:
        lines.append(" | ".join(detail_parts))
    if url:
        lines.append(f"🔗 לצפייה במודעה\n{url}")
    if total_in_db:
        lines.append(f"\n📊 סה\"כ בDB: {total_in_db}")
    return "\n".join(lines)


def _format_full_report_plain(sources_with_listings: List[Dict[str, Any]]) -> str:
    """Plain text body for full report (Telegram/WhatsApp)."""
    lines = ["📋 דיווח מודעות נדל״ן להשכרה – יד2", ""]
    for block in sources_with_listings:
        label = block.get("label", block.get("source_key", ""))
        listings = block.get("listings") or []
        lines.append(f"━━━ {label} ({len(listings)} מודעות) ━━━")
        for item in listings:
            lines.append(_format_listing_line(item))
        lines.append("")
    return "\n".join(lines).strip()


class TelegramNotifier(BaseNotifier):
    """Send notifications via Telegram Bot API. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."""

    def __init__(self, bot_token: str, chat_id: str, verify_ssl: bool = True):
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()
        self.verify_ssl = verify_ssl
        self._base = f"https://api.telegram.org/bot{self.bot_token}"

    def _send(self, text: str) -> None:
        if not text:
            return
        # Telegram limit: split long messages
        for i in range(0, len(text), TELEGRAM_MAX_MESSAGE_LENGTH):
            chunk = text[i : i + TELEGRAM_MAX_MESSAGE_LENGTH]
            r = requests.post(
                f"{self._base}/sendMessage",
                json={"chat_id": self.chat_id, "text": chunk, "disable_web_page_preview": True},
                timeout=15,
                verify=self.verify_ssl,
            )
            r.raise_for_status()

    def send_new_listing(self, listing: Dict[str, Any]) -> None:
        self._send(_format_listing_card(listing, status="חדש ✅"))

    def send_price_change(self, listing: Dict[str, Any]) -> None:
        prev = listing.get("previous_price")
        curr = listing.get("price")
        prev_str = f"{prev:,} ₪" if isinstance(prev, int) else str(prev)
        curr_str = f"{curr:,} ₪" if isinstance(curr, int) else str(curr)
        card = _format_listing_card(listing, status=f"שינוי מחיר: {prev_str} → {curr_str}")
        self._send(card)

    def send_full_report(self, sources_with_listings: List[Dict[str, Any]]) -> None:
        text = _format_full_report_plain(sources_with_listings)
        if not text:
            text = "אין עדיין מודעות שמורות. הרץ גריפה קודם (python main.py)."
        self._send(text)

    def send_test(self) -> None:
        self._send("🔔 בדיקה – Yad2 Monitor פעיל. הערוצים מוגדרים כראוי.")

    @staticmethod
    def from_env() -> "TelegramNotifier | None":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if token and chat_id:
            v = os.environ.get("TELEGRAM_SSL_VERIFY", "true").strip().lower()
            verify_ssl = v not in ("0", "false", "no")
            return TelegramNotifier(token, chat_id, verify_ssl=verify_ssl)
        return None


class WebhookNotifier(BaseNotifier):
    """POST JSON to a URL (e.g. gateway to WhatsApp). Set WHATSAPP_WEBHOOK_URL or similar."""

    def __init__(self, url: str, kind: str = "whatsapp"):
        self.url = url.strip()
        self.kind = kind

    def _post(self, payload: Dict[str, Any]) -> None:
        if not self.url:
            return
        requests.post(self.url, json=payload, timeout=15)

    def send_new_listing(self, listing: Dict[str, Any]) -> None:
        self._post({"type": "new_listing", "listing": listing, "text": _format_listing_line(listing)})

    def send_price_change(self, listing: Dict[str, Any]) -> None:
        self._post({"type": "price_change", "listing": listing})

    def send_full_report(self, sources_with_listings: List[Dict[str, Any]]) -> None:
        text = _format_full_report_plain(sources_with_listings)
        if not text:
            text = "אין עדיין מודעות שמורות."
        self._post({"type": "full_report", "sources": sources_with_listings, "text": text})

    def send_test(self) -> None:
        self._post({"type": "test", "text": "🔔 בדיקה – Yad2 Monitor פעיל."})

    @staticmethod
    def from_env_whatsapp() -> "WebhookNotifier | None":
        url = os.environ.get("WHATSAPP_WEBHOOK_URL", "").strip()
        if url:
            return WebhookNotifier(url, "whatsapp")
        return None


class CompositeNotifier(BaseNotifier):
    """Forwards all notifications to a list of notifiers."""

    def __init__(self, notifiers: List[BaseNotifier]):
        self.notifiers = notifiers

    def send_new_listing(self, listing: Dict[str, Any]) -> None:
        for n in self.notifiers:
            try:
                n.send_new_listing(listing)
            except Exception as e:
                logger.exception("Composite notifier failed: %s", e)

    def send_price_change(self, listing: Dict[str, Any]) -> None:
        for n in self.notifiers:
            try:
                n.send_price_change(listing)
            except Exception as e:
                logger.exception("Composite notifier failed: %s", e)

    def send_full_report(self, sources_with_listings: List[Dict[str, Any]]) -> None:
        for n in self.notifiers:
            try:
                n.send_full_report(sources_with_listings)
            except Exception as e:
                logger.exception("Composite notifier failed: %s", e)

    def send_test(self) -> None:
        for n in self.notifiers:
            try:
                n.send_test()
            except Exception as e:
                logger.exception("Composite notifier test failed: %s", e)
