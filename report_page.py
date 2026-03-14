"""
Generate a local HTML page that displays all scraped listings.
Open the file in a browser to view results (no server required).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Embedded in HTML so the page works as file://
TEMPLATE = """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="120">
  <title>יד2 – מודעות נדל״ן להשכרה</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, sans-serif; margin: 1rem; background: #f5f5f5; }
    h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
    .meta { color: #666; font-size: 0.9rem; margin-bottom: 1rem; }
    section { background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    section h2 { margin-top: 0; font-size: 1.1rem; color: #333; border-bottom: 1px solid #eee; padding-bottom: 0.5rem; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: right; padding: 0.5rem; border-bottom: 1px solid #eee; }
    th { color: #666; font-weight: 600; }
    a { color: #0066cc; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .price { font-weight: 600; }
    .summary { background: #e8f4ea; border: 1px solid #c8e6c9; border-radius: 6px; padding: 0.6rem 1rem; margin-bottom: 1rem; font-weight: 600; }
    .footer { color: #888; font-size: 0.85rem; margin-top: 1.5rem; }
  </style>
</head>
<body>
  <h1>מודעות נדל״ן להשכרה – יד2</h1>
  <p class="meta">תוצאות בפועל מהסריקה האחרונה (מכל הסינונים) &nbsp;|&nbsp; סריקה אחרונה: <span id="lastUpdate">-</span> &nbsp;|&nbsp; הדף מתעדכן כל 2 דקות</p>
  <p class="summary" id="summary">—</p>
  <div id="sources"></div>
  <p class="footer">ניטור אוטומטי כל 10 דקות, 24/7 (מקומי או GitHub Actions)</p>
  <script type="application/json" id="report-data">JSON_PLACEHOLDER</script>
  <script>
    (function() {
      function txt(s) { return (s == null || s === undefined || s === "") ? "-" : String(s); }
      var data = { last_updated: "", sources: [] };
      var el = document.getElementById("report-data");
      if (!el || !el.textContent) {
        document.getElementById("summary").textContent = "אין נתונים. הרץ: python main.py --send-now";
        document.getElementById("lastUpdate").textContent = "-";
        return;
      }
      try {
        data = JSON.parse(el.textContent);
      } catch (e) {
        document.getElementById("summary").textContent = "שגיאה בנתונים. הרץ סריקה מחדש.";
        document.getElementById("lastUpdate").textContent = "-";
        return;
      }
      var lastStr = "-";
      if (data.last_updated) {
        var d = new Date(data.last_updated);
        if (!isNaN(d.getTime())) lastStr = d.toLocaleString("he-IL", { dateStyle: "short", timeStyle: "short" });
        else lastStr = data.last_updated;
      }
      document.getElementById("lastUpdate").textContent = lastStr;
      var total = 0;
      var parts = (data.sources || []).map(function(b) {
        var n = (b.listings || []).length;
        total += n;
        return (b.label || b.source_key) + ": " + n + " תוצאות";
      });
      document.getElementById("summary").textContent = parts.length ? parts.join("  |  ") + "  —  סה״כ: " + total + " מודעות" : "אין תוצאות. הרץ סריקה (python main.py --no-headless).";
      var container = document.getElementById("sources");
      (data.sources || []).forEach(function(block) {
        var section = document.createElement("section");
        var n = (block.listings || []).length;
        var h2 = document.createElement("h2");
        h2.textContent = txt(block.label || block.source_key) + " (" + n + " מודעות)";
        section.appendChild(h2);
        var table = document.createElement("table");
        var thead = document.createElement("thead");
        var thr = document.createElement("tr");
        ["כתובת","חדרים","מ״ר","קומה","מחיר","טלפון","לינק"].forEach(function(thText) {
          var th = document.createElement("th");
          th.textContent = thText;
          thr.appendChild(th);
        });
        thead.appendChild(thr);
        table.appendChild(thead);
        var tbody = document.createElement("tbody");
        (block.listings || []).forEach(function(item) {
          var tr = document.createElement("tr");
          var priceStr = item.price != null ? (typeof item.price === "number" ? item.price.toLocaleString("he-IL") + " ₪" : item.price) : "-";
          function addCell(content, className) {
            var td = document.createElement("td");
            if (className) td.className = className;
            td.textContent = content;
            tr.appendChild(td);
          }
          addCell(txt(item.address));
          addCell(txt(item.rooms));
          addCell(txt(item.sqm));
          addCell(txt(item.floor));
          var priceTd = document.createElement("td");
          priceTd.className = "price";
          priceTd.textContent = priceStr;
          tr.appendChild(priceTd);
          addCell(txt(item.phone));
          var linkTd = document.createElement("td");
          if (item.url) {
            var a = document.createElement("a");
            a.href = item.url;
            a.target = "_blank";
            a.rel = "noopener";
            a.textContent = "למודעה";
            linkTd.appendChild(a);
          } else {
            linkTd.textContent = "-";
          }
          tr.appendChild(linkTd);
          tbody.appendChild(tr);
        });
        if (n === 0) {
          var emptyRow = document.createElement("tr");
          var emptyTd = document.createElement("td");
          emptyTd.colSpan = 7;
          emptyTd.textContent = "לא נמצאו מודעות בסריקה האחרונה";
          emptyRow.appendChild(emptyTd);
          tbody.appendChild(emptyRow);
        }
        table.appendChild(tbody);
        section.appendChild(table);
        container.appendChild(section);
      });
    })();
  </script>
</body>
</html>
"""


def build_report_data(sources_with_listings: List[Dict[str, Any]], last_updated: str) -> Dict[str, Any]:
    """Structure data for the report page (sources + last_updated)."""
    return {
        "last_updated": last_updated,
        "sources": [
            {
                "source_key": b.get("source_key"),
                "label": b.get("label"),
                "listings": b.get("listings", []),
            }
            for b in sources_with_listings
        ],
    }


def write_report_page(
    path: Path,
    sources_with_listings: List[Dict[str, Any]],
    last_updated: str,
) -> None:
    """Generate report.html with embedded JSON and write to path."""
    data = build_report_data(sources_with_listings, last_updated)
    json_str = json.dumps(data, ensure_ascii=False)
    # Inside <script type="application/json"> only </script> would break the tag
    json_str = json_str.replace("</script>", "<\\/script>").replace("</SCRIPT>", "<\\/SCRIPT>")
    html = TEMPLATE.replace("JSON_PLACEHOLDER", json_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    logger.info("Report page written: %s", path)
