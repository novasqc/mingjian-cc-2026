#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive internal QA audit for mingjian.cc.

One command that runs every check a search engine cares about, so a regression
is caught before it is pushed instead of discovered weeks later in the index.

Checks:
  1. broken internal links (href/src)
  2. JSON-LD blocks parse
  3. no `../` leaking into absolute URLs (canonical / og:url / hreflang / JSON-LD)
  4. canonical is absolute and resolves to a real page
  5. hreflang alternates are absolute and resolve
  6. <html lang> matches the page's path/language
  7. robots.txt references the sitemap
  8. sitemap.xml is valid XML and non-trivial
  9. RSS auto-discovery link present in <head>
 10. llms.txt / llms-full.txt / feed.xml exist and are non-empty
 11. no duplicate canonical URLs

Usage:
  python3 scripts/audit_site.py            # human-readable report, exit 1 on failure
  python3 scripts/audit_site.py --quiet    # only print failures (for the pipeline)
"""
import glob
import json
import os
import re
import sys
import xml.dom.minidom

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://mingjian.cc"


def collect_pages():
    files = []
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith("build" + os.sep) or rel.startswith("heartbeat/rendered/"):
            continue
        if rel.startswith("google-site-verification-"):
            continue  # a verification token, not a page
        files.append(rel)
    return sorted(files)


def audit(quiet=False):
    failures = []  # (page_or_section, kind, detail)
    def fail(where, kind, detail):
        failures.append((where, kind, detail))

    pages = collect_pages()
    page_set = set(pages)

    # ---------- 1-6: per-page checks ----------
    canonicals = {}
    for rel in pages:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as f:
            s = f.read()
        base = os.path.dirname(rel)

        # 1. broken internal links
        for href in re.findall(r'(?:href|src)="([^"]+)"', s):
            if href.startswith(("http://", "https://", "mailto:", "#", "data:", "//")):
                continue
            p = href.split("#")[0].split("?")[0]
            if not p:
                continue
            target = p.lstrip("/") if p.startswith("/") else os.path.normpath(
                os.path.join(base, p))
            if target.endswith("/") or target == "":
                target += "index.html"
            if not os.path.exists(os.path.join(ROOT, target)):
                fail(rel, "broken-link", href)

        # 2. JSON-LD validity
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                json.loads(m)
            except Exception as e:
                fail(rel, "jsonld-invalid", str(e)[:80])

        # 3. ../ leaking into absolute URLs
        for m in re.findall(r'https://mingjian\.cc/[^\s"\'<>]*\.\.', s):
            fail(rel, "url-leak", m)

        # 4. canonical
        for c in re.findall(r'<link rel="canonical" href="([^"]+)"', s):
            if not c.startswith(DOMAIN + "/"):
                fail(rel, "canonical-not-abs", c)
                continue
            cpath = c[len(DOMAIN) + 1:]
            if cpath not in page_set:
                fail(rel, "canonical-404", c)
            canonicals.setdefault(cpath, []).append(rel)

        # 5. hreflang alternates
        for h, href in re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', s):
            if not href.startswith(DOMAIN + "/"):
                fail(rel, "hreflang-not-abs", href)
                continue
            apath = href[len(DOMAIN) + 1:]
            if apath not in page_set:
                fail(rel, "hreflang-404", href)

        # 6. html lang vs path
        m = re.search(r'<html lang="([^"]+)"', s)
        if m:
            got = m.group(1)
            langmap = {"en": "en", "zh": "zh-CN", "es": "es", "pt": "pt"}
            exp = None
            if rel.startswith(("blog/posts/", "blog/tag/")):
                lm = re.search(r'-([a-z]{2})\.html$', rel)
                exp = langmap.get(lm.group(1)) if lm else None
            elif rel.startswith("heartbeat/en/"):
                exp = "en"
            elif rel.startswith("heartbeat/"):
                exp = "zh-CN"
            elif rel.startswith(("zh/", "es/", "pt/")):
                exp = langmap.get(rel[:2])
            else:
                exp = "en"
            if exp and got != exp:
                fail(rel, "lang-mismatch", "expected %s got %s" % (exp, got))

        # 9. RSS auto-discovery
        if 'type="application/rss+xml"' not in s and rel not in ("404.html",):
            fail(rel, "no-rss-autodiscovery", "")

    # ---------- 7. robots.txt ----------
    rb = os.path.join(ROOT, "robots.txt")
    if os.path.isfile(rb):
        with open(rb, encoding="utf-8") as f:
            robots = f.read()
        if "sitemap" not in robots.lower():
            fail("robots.txt", "no-sitemap-ref", "")
    else:
        fail("robots.txt", "missing", "")

    # ---------- 8. sitemap.xml ----------
    sm = os.path.join(ROOT, "sitemap.xml")
    if os.path.isfile(sm):
        try:
            xml.dom.minidom.parse(sm)
            with open(sm, encoding="utf-8") as f:
                n = f.read().count("<loc>")
            if n < 10:
                fail("sitemap.xml", "too-few-urls", str(n))
        except Exception as e:
            fail("sitemap.xml", "invalid-xml", str(e)[:80])
    else:
        fail("sitemap.xml", "missing", "")

    # ---------- 10. llms / feed ----------
    for name in ("llms.txt", "llms-full.txt", "feed.xml"):
        p = os.path.join(ROOT, name)
        if not os.path.isfile(p) or os.path.getsize(p) < 100:
            fail(name, "missing-or-empty", "")

    # ---------- 11. duplicate canonical ----------
    for cpath, owners in canonicals.items():
        if len(owners) > 1:
            fail("canonical", "duplicate", "%s <- %s" % (cpath, ", ".join(owners[:3])))

    # ---------- report ----------
    if not quiet:
        print("MINGJIAN.CC — site audit")
        print("pages scanned: %d" % len(pages))
        print("failures: %d" % len(failures))
    for where, kind, detail in failures:
        print("  ✗ [%s] %s %s" % (where, kind, detail))
    if not quiet and not failures:
        print("  ✓ all checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    quiet = "--quiet" in sys.argv
    sys.exit(audit(quiet))
