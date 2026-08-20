#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weekly verification: did the SEO/GEO work actually move real indexing?

Compares the live numbers against the frozen baseline in
docs/baseline-<date>.json and prints a pass / warn / pending verdict per
signal. One command, no arguments needed:

    python3 scripts/weekly_verify.py

Honest framing baked in:
  * "What we control" (surface size, IndexNow submissions) must move
    immediately — it proves the pipeline works, NOT that we are indexed.
  * "Engine response" (Wayback, Bing) is medium-speed.
  * "Real indexing" (Common Crawl, Google, Bing authoritative counts) is the
    slow variable and the ONLY place where the intervention is truly judged.

Reads:  docs/baseline-*.json, ~/ai_index_reports/history.json
Also does one fresh Common Crawl probe (it changes independently of history).
"""
import datetime
import glob
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.expanduser("~/ai_index_reports")
DOMAIN = "mingjian.cc"


def load_baseline():
    files = sorted(glob.glob(os.path.join(ROOT, "docs", "baseline-*.json")))
    if not files:
        print("no baseline file found in docs/")
        sys.exit(1)
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def latest_history():
    p = os.path.join(REPORT_DIR, "history.json")
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            hist = json.load(f)
        return hist[-1] if hist else {}
    except Exception:
        return {}


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "MingjianVerify/1.0 (+https://mingjian.cc)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def commoncrawl_fresh():
    """Fresh Common Crawl probe: return (count, note)."""
    try:
        coll = json.loads(fetch("https://index.commoncrawl.org/collinfo.json", timeout=20))
        ids = [c["id"] for c in coll if re.match(r"^CC-MAIN-20\d\d-\d+$", c.get("id", ""))]
        ids = sorted(ids, key=lambda i: (i.split("-")[2], int(i.split("-")[3])), reverse=True)
    except Exception as e:
        return None, "collinfo: %s" % e
    errors = []
    for cid in ids[:5]:
        try:
            url = ("https://index.commoncrawl.org/%s-index?url=%s/*&output=json&limit=500"
                   % (cid, urllib.parse.quote(DOMAIN)))
            data = fetch(url, timeout=45)
        except Exception as e:
            errors.append("%s:%s" % (cid, getattr(e, "code", type(e).__name__)))
            continue
        rows = [l for l in data.strip().splitlines() if l.strip()]
        return len(rows), cid
    return None, "index API unreachable (%s)" % ", ".join(errors)


def verdict(label, value, baseline, direction, kind):
    """direction: 'up' means growth is good; 'same_or_up' means not shrinking is ok."""
    if value is None or (kind == "pending" and value == 0):
        return "  ⏳ PENDING", label, value, baseline
    if direction == "up":
        if value > baseline:
            return "  ✅ PASS", label, value, baseline
        return "  ⚠️  WARN", label, value, baseline
    if direction == "same_or_up":
        if value >= baseline:
            return "  ✅ PASS", label, value, baseline
        return "  ❌ FAIL", label, value, baseline
    return "  ℹ️  INFO", label, value, baseline


def fresh_surface():
    """Read the current surface size straight from the repo (not from the daily
    history file), so the check is correct even if the monitor cron has not run
    since the last deploy."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import monitor_ai_index as mon
        surf = mon.indexable_surface()
        inx = mon.indexnow_receipt()
        spot = mon.live_spotcheck()
        return {
            "sitemap_urls": surf["sitemap_urls"],
            "heartbeat_pages": surf["heartbeat_pages"],
            "blog_pages": surf["blog_pages"],
            "llms_full_kb": round(surf["llms_full_bytes"] / 1024.0, 1),
            "feed_items": surf["feed_items"],
            "live_ok": sum(1 for v in spot.values() if v == 200),
            "live_total": len(spot),
            "indexnow_ok": inx.get("endpoints_ok"),
            "indexnow_total": inx.get("endpoints_total"),
            "indexnow_urls": inx.get("url_count"),
        }
    except Exception as e:
        print("  (fresh surface read failed: %s; falling back to history)" % e)
        return None


def main():
    base = load_baseline()
    sig = base["signals"]
    base_date = base["frozen_at"]
    hist = latest_history()
    hist_date = hist.get("date", "?")
    fresh = fresh_surface()

    today = datetime.date.today().isoformat()
    elapsed = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(base_date)).days

    print("=" * 66)
    print("MINGJIAN.CC — EXPOSURE VERIFICATION")
    print("baseline: %s   |   now: %s   |   elapsed: %d days" % (base_date, today, elapsed))
    print("=" * 66)

    def cur(key, default=None):
        if fresh:
            return fresh.get(key, default)
        return hist.get(key, default)

    # --- A. What we control (surface size + pipeline) ---
    print("\n[A] 我们控制的量 — 应立即达标（证明流水线在跑，不证明被收录）")
    rows = [
        ("sitemap URL 数", cur("sitemap_urls"), sig["sitemap_urls"], "same_or_up"),
        ("心跳页面数", cur("heartbeat_pages"), sig["heartbeat_pages"], "same_or_up"),
        ("博客页面数", cur("blog_pages"), sig["blog_pages"], "same_or_up"),
        ("llms-full 语料 (KB)", cur("llms_full_kb"), sig["llms_full_kb"], "same_or_up"),
        ("RSS 条目数", cur("feed_items"), sig["feed_items"], "same_or_up"),
        ("线上可用 URL", "%d/%d" % (cur("live_ok", 0), cur("live_total", 0)),
         "%d/%d" % (sig["live_ok"], sig["live_total"]), "same_or_up"),
        ("IndexNow 端点接受", "%d/%d" % (cur("indexnow_ok", 0), cur("indexnow_total", 0)),
         "%d/%d" % (sig["indexnow_endpoints_ok"], sig["indexnow_endpoints_total"]), "same_or_up"),
    ]
    for label, now, bl, d in rows:
        if isinstance(now, str) or isinstance(bl, str):
            mark = "✅ PASS" if now == bl else "⚠️  CHECK"
            print("  %s  %-22s %s -> %s" % (mark, label, bl, now))
        else:
            mark, l, v, b = verdict(label, now, bl, d, "n")
            print("  %s  %-22s %s -> %s" % (mark, l, b, v))

    # --- B. Engine response (medium speed) ---
    print("\n[B] 引擎响应 — 中速信号（Wayback / Bing）")
    wb = hist.get("wayback_captures")
    print("  %s  %-22s %s -> %s" % (
        "✅ PASS" if (wb or 0) > sig["wayback_captures"] else "⏳ PENDING",
        "Wayback 捕获数", sig["wayback_captures"], wb if wb is not None else "?"))
    bing = hist.get("bing_mentions")
    print("  ℹ️  INFO   %-22s %s -> %s  (弱信号，权威数据看 Bing WMT)"
          % ("Bing 抓取提及", sig["bing_mentions"], bing if bing is not None else "?"))

    # --- C. Real indexing (slow, the actual test) ---
    print("\n[C] 实质收录 — 慢变量，判定真伪的唯一标准")
    cc_count, cc_note = commoncrawl_fresh()
    if cc_count:
        mark = "✅ PASS" if cc_count > 0 else "✅ PASS"
        print("  %s  Common Crawl 捕获页：%s（%s）" % (mark, cc_count, cc_note))
    else:
        print("  ⏳ PENDING  Common Crawl 捕获页：尚未出现（%s）" % cc_note)
        print("     说明：CC 按批次爬取，8 月的收集最早 9 月初才可查。D+14 前 0 属正常。")

    print("\n[Google / Bing 权威收录数 — 需登录后台（或授权 API 后自动拉取）]")
    print("  Google Search Console  →  索引 > 页面：看是否出现 mingjian.cc 页面")
    print("  Bing Webmaster Tools   →  站点扫描 > 已索引页面：看 IndexNow 提交后增长")

    # --- Verdict ---
    print("\n" + "-" * 66)
    print("判定（%s）" % today)
    if elapsed < 7:
        print("  结论：尚在观察期。先看 [A] 是否全 ✅；[C] 的 0 属正常，不判失败。")
    elif elapsed < 14:
        print("  结论：观察中。[A] 应全 ✅；[B] 应有增长；[C] 若仍 0，继续等 D+14。")
    else:
        cc_now = cc_count or 0
        if cc_now > 0:
            print("  结论：✅ 有效。Common Crawl 已收录 %d 页，干预产生真实收录。" % cc_now)
        else:
            print("  结论：⚠️ 未达预期。D+14 仍无 Common Crawl 收录，说明干预不足，")
            print("        需迭代（外链 / 目录提交 / 更多语言 / 冷门引擎）。")
    print("-" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
