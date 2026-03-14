"""
Entry point for Yad2 real estate monitor.
Supports single run (one URL) and scheduler mode: check every 10 min, daily full report, local HTML page.
"""

import asyncio
import logging
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError:
    HTTPServer = SimpleHTTPRequestHandler = None

from config import (
    DEFAULT_SEARCH_URL,
    SEARCH_SOURCES,
    CHECK_INTERVAL_MINUTES,
    FULL_REPORT_INTERVAL_HOURS,
    ACTIVE_HOURS_START,
    ACTIVE_HOURS_END,
)
from local_db import (
    load_db,
    save_db,
    compare_listings,
    listings_dict_from_records,
    get_previous_listings,
    update_source,
    get_all_listings_for_report,
    should_send_full_report,
    set_last_full_report_now,
    set_last_check_now,
)
from notifier import (
    ConsoleNotifier,
    TelegramNotifier,
    WebhookNotifier,
    CompositeNotifier,
)
from report_page import write_report_page
from scraper import Yad2Scraper

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "local_db.json"
REPORT_HTML_PATH = SCRIPT_DIR / "report.html"

# Link to open report in browser (local file)
REPORT_FILE_LINK = f"file://{REPORT_HTML_PATH.resolve()}"

# Default port for --serve (report from phone on same WiFi)
SERVE_PORT = 8765

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _migrate_legacy_db(db: dict) -> dict:
    """If DB has root 'listings' (old schema), migrate to sources.default."""
    if "listings" in db and "sources" not in db:
        db["sources"] = {
            "default": {
                "url": DEFAULT_SEARCH_URL,
                "label": "חיפוש (ברירת מחדל)",
                "listings": db.pop("listings", {}),
                "last_updated": db.get("last_updated", ""),
            }
        }
        db.setdefault("last_full_report_at", "")
        db.setdefault("last_check_at", "")
    return db


async def run_once(
    url: str = DEFAULT_SEARCH_URL,
    db_path: Path = DB_PATH,
    notifier=None,
    headless: bool = True,
) -> None:
    """
    Single run (legacy): one URL, one source. Compare with DB, save, notify.
    """
    if notifier is None:
        notifier = ConsoleNotifier()
    db = load_db(db_path)
    db = _migrate_legacy_db(db)
    previous_listings = db.get("listings", {}) or (db.get("sources", {}).get("default") or {}).get("listings", {})

    scraper = Yad2Scraper(url=url, headless=headless)
    try:
        current_records = await scraper.scrape()
    except Exception as e:
        logger.exception("Scraping failed: %s", e)
        raise

    current_listings = listings_dict_from_records(current_records)
    new_listings, price_changed_listings = compare_listings(current_listings, previous_listings)

    if "sources" not in db:
        db["sources"] = {}
    db["sources"]["default"] = {
        "url": url,
        "label": "חיפוש",
        "listings": current_listings,
        "last_updated": datetime.now(tz=timezone.utc).isoformat(),
    }
    db["last_updated"] = db["last_check_at"] = datetime.now(tz=timezone.utc).isoformat()
    save_db(db_path, db)

    if new_listings or price_changed_listings:
        notifier.send_changes(new_listings, price_changed_listings)
    else:
        logger.info("No new listings or price changes detected.")


async def run_cycle(
    db_path: Path = DB_PATH,
    report_path: Path = REPORT_HTML_PATH,
    notifier=None,
    headless: bool = True,
) -> None:
    """
    Run all SEARCH_SOURCES: scrape each URL, diff per source, update DB, notify changes, write report.html.
    """
    if notifier is None:
        notifier = ConsoleNotifier()
    db = load_db(db_path)
    db = _migrate_legacy_db(db)
    now_iso = datetime.now(tz=timezone.utc).isoformat()

    for src in SEARCH_SOURCES:
        source_key = src["key"]
        url = src["url"]
        label = src["label"]
        previous = get_previous_listings(db, source_key)

        scraper = Yad2Scraper(url=url, headless=headless)
        try:
            current_records = await scraper.scrape()
        except Exception as e:
            logger.exception("Scraping failed for %s: %s", source_key, e)
            continue

        current_listings = listings_dict_from_records(current_records)
        update_source(db, source_key, url, label, current_listings, now_iso)

        new_listings, price_changed_listings = compare_listings(current_listings, previous)
        # Do not spam "new" when previous was empty (first run or after failed commits) — treat as initial sync
        is_initial_sync = not previous and bool(current_listings)
        if is_initial_sync:
            logger.info("[%s] Initial sync: %d listings saved. Next runs will notify only new/price changes.", source_key, len(current_listings))
        elif new_listings or price_changed_listings:
            logger.info("[%s] %d new, %d price changes — sending immediate update", source_key, len(new_listings), len(price_changed_listings))
            notifier.send_changes(new_listings, price_changed_listings)
        else:
            logger.info("[%s] No changes.", source_key)

    set_last_check_now(db, now_iso)
    save_db(db_path, db)

    sources_for_report = get_all_listings_for_report(db)
    write_report_page(report_path, sources_for_report, now_iso)
    # Log total results per search so user sees that everything ran
    counts = [(b.get("label") or b.get("source_key"), len(b.get("listings") or [])) for b in sources_for_report]
    total = sum(n for _, n in counts)
    logger.info("Cycle complete: %s — total %d listings", ", ".join("%s %d" % (l, n) for l, n in counts), total)


def _build_notifiers_for_report():
    """Console + Telegram (if env) + WhatsApp webhook (if env)."""
    notifiers: list = [ConsoleNotifier()]
    t = TelegramNotifier.from_env()
    if t:
        notifiers.append(t)
    w = WebhookNotifier.from_env_whatsapp()
    if w:
        notifiers.append(w)
    return CompositeNotifier(notifiers)


def run_daily_full_report(
    db_path: Path = DB_PATH,
    report_path: Path = REPORT_HTML_PATH,
    notifier=None,
) -> None:
    """If 24h passed since last full report, send full listing summary and update last_full_report_at."""
    if notifier is None:
        notifier = _build_notifiers_for_report()
    db = load_db(db_path)
    db = _migrate_legacy_db(db)
    if not should_send_full_report(db, FULL_REPORT_INTERVAL_HOURS):
        return
    sources_for_report = get_all_listings_for_report(db)
    notifier.send_full_report(sources_for_report)
    set_last_full_report_now(db, datetime.now(tz=timezone.utc).isoformat())
    save_db(db_path, db)
    write_report_page(report_path, sources_for_report, db.get("last_check_at", "") or datetime.now(tz=timezone.utc).isoformat())


def send_full_report_now(
    db_path: Path = DB_PATH,
    report_path: Path = REPORT_HTML_PATH,
) -> None:
    """Load DB, send full report to Console + Telegram + WhatsApp (if configured), update last_full_report_at."""
    notifier = _build_notifiers_for_report()
    db = load_db(db_path)
    db = _migrate_legacy_db(db)
    sources_for_report = get_all_listings_for_report(db)
    notifier.send_full_report(sources_for_report)
    set_last_full_report_now(db, datetime.now(tz=timezone.utc).isoformat())
    save_db(db_path, db)
    write_report_page(report_path, sources_for_report, datetime.now(tz=timezone.utc).isoformat())
    logger.info("Full report sent to all configured channels.")


def _in_active_hours() -> bool:
    """True if current local hour is in [ACTIVE_HOURS_START, ACTIVE_HOURS_END)."""
    hour = datetime.now().hour
    if ACTIVE_HOURS_END == 24:
        return ACTIVE_HOURS_START <= hour < 24
    return ACTIVE_HOURS_START <= hour < ACTIVE_HOURS_END


async def run_scheduler(
    db_path: Path = DB_PATH,
    report_path: Path = REPORT_HTML_PATH,
    notifier=None,
    headless: bool = True,
) -> None:
    """
    Loop: every CHECK_INTERVAL_MINUTES run cycle during active hours (6:00–24:00).
    Sends immediate notification (Telegram + console) on new listing or price change.
    """
    if notifier is None:
        notifier = _build_notifiers_for_report()
    interval_sec = CHECK_INTERVAL_MINUTES * 60
    logger.info(
        "Scheduler started: check every %s min (active %s:00–%s:00), full report every %s h. Report: %s",
        CHECK_INTERVAL_MINUTES,
        ACTIVE_HOURS_START,
        ACTIVE_HOURS_END,
        FULL_REPORT_INTERVAL_HOURS,
        report_path,
    )

    while True:
        try:
            if _in_active_hours():
                await run_cycle(db_path=db_path, report_path=report_path, notifier=notifier, headless=headless)
                run_daily_full_report(db_path=db_path, report_path=report_path, notifier=notifier)
            else:
                logger.debug("Outside active hours (%s:00–%s:00), skipping cycle.", ACTIVE_HOURS_START, ACTIVE_HOURS_END)
        except Exception as e:
            logger.exception("Cycle failed: %s", e)
        await asyncio.sleep(interval_sec)


def _local_ip() -> str:
    """Best-effort local IP for same-network access (e.g. from phone)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_serve(port: int = SERVE_PORT, directory: Path = SCRIPT_DIR) -> None:
    """Run HTTP server so report is reachable from phone on same WiFi."""
    if HTTPServer is None or SimpleHTTPRequestHandler is None:
        logger.error("http.server not available; cannot run --serve.")
        sys.exit(1)
    os.chdir(directory)
    handler = SimpleHTTPRequestHandler
    server = HTTPServer(("0.0.0.0", port), handler)
    local = _local_ip()
    print("")
    print("  Report (this machine):  http://127.0.0.1:%s/report.html" % port)
    print("  Report (from phone):   http://%s:%s/report.html" % (local, port))
    print("")
    print("  Keep this terminal open. Same WiFi only. Ctrl+C to stop.")
    print("")
    logger.info("Serving %s on 0.0.0.0:%s", directory, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")
        server.shutdown()


def main() -> None:
    import argparse
    try:
        from dotenv import load_dotenv
        load_dotenv(SCRIPT_DIR / ".env")
    except ImportError:
        pass
    parser = argparse.ArgumentParser(description="Yad2 real estate rent monitor")
    parser.add_argument("--url", default=None, help="Single URL to scrape (legacy single run)")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Path to local_db.json")
    parser.add_argument("--report", type=Path, default=REPORT_HTML_PATH, help="Path to report.html")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")
    parser.add_argument("--schedule", action="store_true", help="Run scheduler: check every 10 min, daily full report")
    parser.add_argument("--send-now", action="store_true", help="Send full report now to Telegram + WhatsApp (env) and console; update report.html")
    parser.add_argument("--test", action="store_true", help="Send a test message to all configured channels (Telegram, WhatsApp, console)")
    parser.add_argument("--serve", action="store_true", help="Run HTTP server to view report from phone (same WiFi)")
    parser.add_argument("--serve-port", type=int, default=SERVE_PORT, help="Port for --serve (default %s)" % SERVE_PORT)
    parser.add_argument("--skip-if-inactive", action="store_true", help="Exit 0 without running if outside active hours (for CI)")
    args = parser.parse_args()

    report_link = f"file://{args.report.resolve()}"

    if args.serve:
        run_serve(port=args.serve_port, directory=SCRIPT_DIR)
        return

    if args.test:
        # In CI, require Telegram so the workflow fails clearly if secrets are missing
        if not (os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() and os.environ.get("TELEGRAM_CHAT_ID", "").strip()):
            logger.error(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not set. "
                "Add them in GitHub: Settings → Secrets and variables → Actions."
            )
            sys.exit(1)
        notifier = _build_notifiers_for_report()
        notifier.send_test()
        logger.info("Test message sent to all configured channels.")
        return

    if args.send_now:
        print("Link to view results:", report_link)
        send_full_report_now(db_path=args.db, report_path=args.report)
        return

    if args.schedule:
        logger.info("Report page (open in browser): %s", report_link)
        asyncio.run(run_scheduler(
            db_path=args.db,
            report_path=args.report,
            notifier=_build_notifiers_for_report(),
            headless=not args.no_headless,
        ))
        return

    url = args.url or DEFAULT_SEARCH_URL
    if not args.url and SEARCH_SOURCES:
        # Default: run one cycle with all sources and exit (no scheduler)
        if args.skip_if_inactive and not _in_active_hours():
            logger.info("Outside active hours, skipping (--skip-if-inactive).")
            return
        asyncio.run(run_cycle(db_path=args.db, report_path=args.report, headless=not args.no_headless))
        run_daily_full_report(db_path=args.db, report_path=args.report)
        return

    asyncio.run(run_once(url=url, db_path=args.db, headless=not args.no_headless))


if __name__ == "__main__":
    main()
