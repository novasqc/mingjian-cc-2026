#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monitor how AI engines / search engines are indexing mingjian.cc.

Signals checked:
  1. Common Crawl CDX  — crawled pages (feeds many LLM training sets)
  2. Wayback Machine   — archived captures (Internet Archive)
  3. Bing search       — site:mingjian.cc result presence (best-effort)

Writes a daily report to ~/ai_index_reports/<date>.md and appends to
~/ai_index_reports/history.json. Prints a short summary.
"""
import datetime
import json
import os
import re
import urllib.parse
import urllib.request

DOMAIN = "mingjian.cc"
REPORT_DIR = os.path.expanduser("~/ai_index_reports")


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "MingjianIndexMonitor/1.0 (+https://mingjian.cc)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def commoncrawl():
    """Return list of (timestamp, url) captured by Common Crawl."""
    try:
        coll = json.loads(fetch("https://index.commoncrawl.org/collinfo.json", timeout=20))
        # collinfo is roughly newest-first; pick the newest CC-MAIN-YYYY-XX id defensively
        ids = [c["id"] for c in coll if re.match(r"^CC-MAIN-20\d\d-\d+$", c.get("id", ""))]
        if not ids:
            return None, "no CC-MAIN collections found"
        latest = sorted(ids, key=lambda i: (i.split("-")[2], int(i.split("-")[3])))[-1]
    except Exception as e:
        return None, "collinfo: %s" % e
    out = []
    try:
        url = ("https://index.commoncrawl.org/%s-index?url=%s&matchType=domain&output=json&limit=200"
               % (latest, urllib.parse.quote(DOMAIN)))
        data = fetch(url, timeout=45)
        for line in data.strip().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            out.append((d.get("timestamp", ""), d.get("url", "")))
    except Exception as e:
        return out, "cdx(%s): %s" % (latest, e)
    return out, latest


def wayback():
    try:
        url = ("http://web.archive.org/cdx/search/cdx?url=%s*&output=json&limit=200&filter=statuscode:200"
               % urllib.parse.quote(DOMAIN))
        data = json.loads(fetch(url, timeout=45))
        return data[1:] if data else []
    except Exception as e:
        return None, "wayback: %s" % e


def bing():
    try:
        html = fetch("https://www.bing.com/search?q=" + urllib.parse.quote("site:" + DOMAIN), timeout=25)
        count = len(re.findall(r"mingjian\.cc", html))
        blocked = "captcha" in html.lower() or "challenge" in html.lower()
        return count, blocked
    except Exception as e:
        return None, "bing: %s" % e


def main():
    today = datetime.date.today().isoformat()
    os.makedirs(REPORT_DIR, exist_ok=True)
    report = ["# AI Indexing Report — %s" % today, ""]

    # Common Crawl
    cc, cc_note = commoncrawl()
    cc_pages = sorted(set(u for _, u in cc))
    report.append("## Common Crawl")
    if cc_note and not isinstance(cc_note, list):
        report.append("- collection: %s" % cc_note)
    report.append("- captured pages: %d" % len(cc_pages))
    for u in cc_pages[:20]:
        report.append("  - %s" % u)
    if cc:
        report.append("- latest capture: %s" % cc[-1][0])
    report.append("")

    # Wayback
    wb = wayback()
    if isinstance(wb, list):
        report.append("## Wayback Machine")
        report.append("- captures (status 200): %d" % len(wb))
        for row in wb[:10]:
            report.append("  - %s %s" % (row[1], row[2]))
    else:
        report.append("## Wayback Machine\n- error: %s" % (wb[1] if wb else "unknown"))
    report.append("")

    # Bing
    bg, bg_note = bing()
    report.append("## Bing (site:%s)" % DOMAIN)
    if isinstance(bg, int):
        report.append("- mentions of domain in results: %d" % bg)
    else:
        report.append("- error: %s" % bg_note)
    report.append("")

    text = "\n".join(report)
    with open(os.path.join(REPORT_DIR, today + ".md"), "w", encoding="utf-8") as f:
        f.write(text)

    # history
    hist_path = os.path.join(REPORT_DIR, "history.json")
    hist = []
    if os.path.isfile(hist_path):
        try:
            with open(hist_path, encoding="utf-8") as f:
                hist = json.load(f)
        except Exception:
            hist = []
    hist.append({
        "date": today,
        "commoncrawl_pages": len(cc_pages) if isinstance(cc, list) else None,
        "commoncrawl_note": str(cc_note) if not isinstance(cc_note, list) else cc_note,
        "wayback_captures": len(wb) if isinstance(wb, list) else None,
        "bing_mentions": bg if isinstance(bg, int) else None,
    })
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)

    # summary
    print(text)
    print("history: %d entries" % len(hist))
    return 0


if __name__ == "__main__":
    main()
