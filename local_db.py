"""
Local JSON database for storing and comparing Yad2 listings.
Supports multiple search sources; handles load, save, diff, and full-report data.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Schema: sources by key; each source: url, listings {id -> {price, address, floor, url}}, last_updated
# Plus last_full_report_at, last_check_at
DB_SCHEMA = {
    "sources": {},
    "last_full_report_at": "",
    "last_check_at": "",
}


def _ensure_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    if "sources" not in data:
        data["sources"] = {}
    if "last_full_report_at" not in data:
        data["last_full_report_at"] = ""
    if "last_check_at" not in data:
        data["last_check_at"] = ""
    for sid, src in data.get("sources", {}).items():
        if "listings" not in src:
            src["listings"] = {}
        if "last_updated" not in src:
            src["last_updated"] = ""
    return data


def load_db(path: Path) -> Dict[str, Any]:
    """Load local_db.json. Returns schema-compliant dict; creates empty schema if missing."""
    if not path.exists():
        logger.info("Local DB file not found, using empty schema.")
        return _ensure_schema(dict(DB_SCHEMA))
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _ensure_schema(data)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load local_db.json: %s. Using empty schema.", e)
        return _ensure_schema(dict(DB_SCHEMA))


def save_db(path: Path, data: Dict[str, Any]) -> None:
    """Write DB to path with UTF-8 and pretty indent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compare_listings(
    current: Dict[str, Dict[str, Any]], previous: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Compare current scraped listings with previous DB state.
    Returns (new_listings, price_changed_listings).
    Each item: { "item_id", "price", "address", "floor", "url", "previous_price" (only for price change) }
    """
    new_listings: List[Dict[str, Any]] = []
    price_changed: List[Dict[str, Any]] = []

    for item_id, record in current.items():
        prev = previous.get(item_id)
        entry = {
            "item_id": item_id,
            "price": record.get("price"),
            "address": record.get("address", ""),
            "floor": record.get("floor", ""),
            "url": record.get("url", ""),
        }
        if prev is None:
            new_listings.append(entry)
        else:
            prev_price = prev.get("price")
            if prev_price is not None and record.get("price") != prev_price:
                entry["previous_price"] = prev_price
                price_changed.append(entry)

    return new_listings, price_changed


def listings_dict_from_records(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Convert list of records (with item_id) to dict keyed by item_id for DB storage."""
    return {r["item_id"]: {k: v for k, v in r.items() if k != "item_id"} for r in records}


def get_previous_listings(db: Dict[str, Any], source_key: str) -> Dict[str, Dict[str, Any]]:
    """Get listings dict for a source from DB."""
    src = (db.get("sources") or {}).get(source_key) or {}
    return src.get("listings") or {}


def update_source(
    db: Dict[str, Any],
    source_key: str,
    url: str,
    label: str,
    listings: Dict[str, Dict[str, Any]],
    now_iso: str,
) -> None:
    """Update one source in DB (in-place)."""
    if "sources" not in db:
        db["sources"] = {}
    db["sources"][source_key] = {
        "url": url,
        "label": label,
        "listings": listings,
        "last_updated": now_iso,
    }


def get_all_listings_for_report(db: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns list of { "source_key", "label", "url", "listings": [ { item_id, price, address, floor, url } ] }
    for generating daily report and local HTML page.
    """
    out: List[Dict[str, Any]] = []
    for sid, src in (db.get("sources") or {}).items():
        listings_dict = src.get("listings") or {}
        records = [
            {"item_id": k, **v}
            for k, v in listings_dict.items()
        ]
        out.append({
            "source_key": sid,
            "label": src.get("label", sid),
            "url": src.get("url", ""),
            "listings": records,
        })
    return out


def should_send_full_report(db: Dict[str, Any], interval_hours: float = 24) -> bool:
    """True if last_full_report_at is missing or older than interval."""
    last = db.get("last_full_report_at") or ""
    if not last:
        return True
    try:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() >= interval_hours * 3600
    except Exception:
        return True


def set_last_full_report_now(db: Dict[str, Any], now_iso: str) -> None:
    """Set last_full_report_at in DB (in-place)."""
    db["last_full_report_at"] = now_iso


def set_last_check_now(db: Dict[str, Any], now_iso: str) -> None:
    """Set last_check_at in DB (in-place)."""
    db["last_check_at"] = now_iso
