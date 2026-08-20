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
    """Return (list of (timestamp, url), note) from Common Crawl's CDX index.

    Walks the newest collections in order because the very newest one often has
    no published index yet (404), and the index host frequently answers 503.
    A failed lookup must never be reported as "0 pages captured" — that would
    read as "we are not crawled" when the truth is "we could not ask".
    """
    try:
        coll = json.loads(fetch("https://index.commoncrawl.org/collinfo.json", timeout=20))
        ids = [c["id"] for c in coll if re.match(r"^CC-MAIN-20\d\d-\d+$", c.get("id", ""))]
        if not ids:
            return None, "no CC-MAIN collections found"
        ids = sorted(ids, key=lambda i: (i.split("-")[2], int(i.split("-")[3])),
                     reverse=True)
    except Exception as e:
        return None, "collinfo: %s" % e

    errors = []
    for cid in ids[:5]:
        try:
            # CDX API: url=domain/* (prefix wildcard); matchType=domain is deprecated/404
            url = ("https://index.commoncrawl.org/%s-index?url=%s/*&output=json&limit=200"
                   % (cid, urllib.parse.quote(DOMAIN)))
            data = fetch(url, timeout=45)
        except Exception as e:
            code = getattr(e, "code", None)
            errors.append("%s:%s" % (cid, code or type(e).__name__))
            continue
        out = []
        for line in data.strip().splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            out.append((d.get("timestamp", ""), d.get("url", "")))
        return out, cid
    return None, "index API unreachable (%s)" % ", ".join(errors)


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


# ---------------------------------------------------------------- exposure side
# Indexing is downstream of two things we actually control: how many crawlable
# URLs the site publishes, and whether the engines were told they changed.

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def indexable_surface():
    """What the site currently offers crawlers: sitemap URLs by kind + corpus size."""
    info = {"sitemap_urls": 0, "heartbeat_pages": 0, "blog_pages": 0,
            "core_pages": 0, "llms_full_bytes": 0, "feed_items": 0, "error": None}
    try:
        with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as f:
            locs = re.findall(r"<loc>([^<]+)</loc>", f.read())
        info["sitemap_urls"] = len(locs)
        info["heartbeat_pages"] = sum(1 for u in locs if "/heartbeat/" in u)
        info["blog_pages"] = sum(1 for u in locs if "/blog/posts/" in u)
        info["core_pages"] = info["sitemap_urls"] - info["heartbeat_pages"] - info["blog_pages"]
    except Exception as e:
        info["error"] = str(e)
    try:
        info["llms_full_bytes"] = os.path.getsize(os.path.join(ROOT, "llms-full.txt"))
    except Exception:
        pass
    try:
        with open(os.path.join(ROOT, "feed.xml"), encoding="utf-8") as f:
            info["feed_items"] = len(re.findall(r"<item>", f.read()))
    except Exception:
        pass
    return info


def indexnow_receipt():
    """Last IndexNow submission result, written by scripts/indexnow.py."""
    path = os.path.join(REPORT_DIR, "indexnow-latest.json")
    try:
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        return {"submitted_at": r.get("submitted_at"), "mode": r.get("mode"),
                "url_count": r.get("url_count"),
                "endpoints_ok": r.get("endpoints_ok"),
                "endpoints_total": r.get("endpoints_total")}
    except Exception as e:
        return {"error": str(e)}


def live_spotcheck():
    """Confirm the highest-value URLs actually serve 200 in production."""
    targets = ["", "sitemap.xml", "robots.txt", "llms.txt", "llms-full.txt",
               "feed.xml", "heartbeat/archive.html", "blog.html"]
    out = {}
    for t in targets:
        url = "https://%s/%s" % (DOMAIN, t)
        try:
            req = urllib.request.Request(
                url, method="HEAD",
                headers={"User-Agent": "MingjianIndexMonitor/1.0 (+https://mingjian.cc)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                out[t or "/"] = r.status
        except Exception as e:
            out[t or "/"] = getattr(e, "code", None) or "err"
    return out


def main():
    today = datetime.date.today().isoformat()
    os.makedirs(REPORT_DIR, exist_ok=True)
    report = ["# AI Indexing Report — %s" % today, ""]

    # What we publish (fully under our control)
    surf = indexable_surface()
    report.append("## Indexable surface (what we offer crawlers)")
    report.append("- sitemap URLs: %d  (core %d / heartbeat %d / blog %d)"
                  % (surf["sitemap_urls"], surf["core_pages"],
                     surf["heartbeat_pages"], surf["blog_pages"]))
    report.append("- llms-full.txt corpus: %.1f KB" % (surf["llms_full_bytes"] / 1024.0))
    report.append("- RSS feed items: %d" % surf["feed_items"])
    if surf["error"]:
        report.append("- error: %s" % surf["error"])
    report.append("")

    # Whether we told the engines
    inx = indexnow_receipt()
    report.append("## IndexNow (Bing / Yandex / Seznam / Naver)")
    if "error" in inx:
        report.append("- no receipt yet: %s" % inx["error"])
    else:
        report.append("- last submission: %s (mode=%s)"
                      % (inx["submitted_at"], inx["mode"]))
        report.append("- URLs submitted: %s" % inx["url_count"])
        report.append("- endpoints accepted: %s/%s"
                      % (inx["endpoints_ok"], inx["endpoints_total"]))
    report.append("")

    # Production spot check
    spot = live_spotcheck()
    bad = {k: v for k, v in spot.items() if v != 200}
    report.append("## Production spot check")
    report.append("- %d/%d key URLs return 200" % (len(spot) - len(bad), len(spot)))
    for k, v in bad.items():
        report.append("  - PROBLEM %s -> %s" % (k, v))
    report.append("")

    # Common Crawl
    cc, cc_note = commoncrawl()
    cc_pages = sorted(set(u for _, u in cc)) if isinstance(cc, list) else []
    report.append("## Common Crawl")
    if cc is None:
        # Could not ask — this is NOT the same as "not crawled".
        report.append("- query failed: %s" % cc_note)
        report.append("- captured pages: unknown (retry tomorrow)")
    else:
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
        "sitemap_urls": surf["sitemap_urls"],
        "heartbeat_pages": surf["heartbeat_pages"],
        "blog_pages": surf["blog_pages"],
        "llms_full_kb": round(surf["llms_full_bytes"] / 1024.0, 1),
        "feed_items": surf["feed_items"],
        "indexnow_urls": inx.get("url_count"),
        "indexnow_ok": inx.get("endpoints_ok"),
        "live_ok": sum(1 for v in spot.values() if v == 200),
        "live_total": len(spot),
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
