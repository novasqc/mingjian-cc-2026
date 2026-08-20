#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render daily philosophy heartbeat markdown sources into site HTML.

Reads:  ~/.openclaw/workspace/memory/daily-philosophy/<date>.md
Writes: heartbeat/rendered/<date>.html  (converted via markdown)
Updates: heartbeat/index.json  (latest / count / updated / items)

Usage: python3 heartbeat/build_heartbeat.py
"""
import json
import os
import re
import sys

HEARTBEAT_SOURCE = os.path.expanduser("~/.openclaw/workspace/memory/daily-philosophy")
RENDERED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "heartbeat", "rendered")
INDEX_PATH = os.path.join(os.path.dirname(RENDERED_DIR), "index.json")


def md_to_html(md_text):
    """Convert heartbeat markdown to the site's hb__* HTML."""
    try:
        import markdown as mdlib
        html = mdlib.markdown(md_text, extensions=["extra", "sane_lists"])
    except Exception:
        # fallback: naive conversion
        html = "<p>" + md_text.replace("\n\n", "</p><p>") + "</p>"
    # The site's heartbeat.css styles h1/h2/h3/blockquote/ul/li inside .hb-body,
    # so we only need to keep the semantic elements. Optionally add hb__* classes.
    return strip_local_links(html)


def strip_local_links(html):
    """Unwrap anchors that point at local files instead of web resources.

    The heartbeat sources are written in Mingjian's local workspace and
    sometimes reference files there (e.g. `anti-patterns.md`). Published as-is
    those are dead links: bad for readers, wasted crawl budget. Keep the link
    text, drop the broken href.
    """
    def repl(m):
        href, text = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#|/)", href.strip(), re.I):
            return m.group(0)
        return text
    return re.sub(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', repl, html,
                  flags=re.S | re.I)


def extract_summary(md_text, max_len=240):
    """Extract a summary: the first meaningful paragraph after the header blockquote."""
    # strip header + first blockquote, then take first non-empty paragraph
    lines = md_text.split("\n")
    summary_parts = []
    in_blockquote = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            in_blockquote = True
            # keep blockquote text as summary
            content = stripped.lstrip(">").strip()
            if content and not content.startswith("#"):
                summary_parts.append(content)
            continue
        elif stripped.startswith("#"):
            continue
        elif in_blockquote and stripped == "":
            in_blockquote = False
            continue
        elif stripped and not in_blockquote and not summary_parts:
            # first paragraph after blockquote
            summary_parts.append(stripped)
        if summary_parts and not in_blockquote:
            # stop after first paragraph
            break
    summary = " ".join(summary_parts).replace("**", "").replace("`", "")
    if len(summary) > max_len:
        summary = summary[:max_len] + "…"
    return summary


def get_title(md_text, date):
    """Extract H1 title, fallback to a default."""
    m = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return "每日哲学呼吸 - " + date


def main():
    os.makedirs(RENDERED_DIR, exist_ok=True)

    # Load existing index
    index = {"latest": None, "count": 0, "updated": None, "items": []}
    if os.path.isfile(INDEX_PATH):
        try:
            with open(INDEX_PATH, encoding="utf-8") as f:
                index = json.load(f)
        except Exception:
            index = {"latest": None, "count": 0, "updated": None, "items": []}

    # Existing rendered dates
    existing_dates = set()
    for it in index.get("items", []):
        existing_dates.add(it.get("date"))

    # Scan source files
    source_files = []
    if os.path.isdir(HEARTBEAT_SOURCE):
        for fn in os.listdir(HEARTBEAT_SOURCE):
            if fn.endswith(".md"):
                date = fn[:-3]  # strip .md
                if re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                    source_files.append((date, os.path.join(HEARTBEAT_SOURCE, fn)))
    source_files.sort()

    new_items = []
    rendered_count = 0
    for date, path in source_files:
        if date in existing_dates:
            # already rendered, reuse existing item
            for it in index["items"]:
                if it["date"] == date:
                    new_items.append(it)
                    break
            continue
        # Render new
        with open(path, encoding="utf-8") as f:
            md_text = f.read()
        html = md_to_html(md_text)
        # ensure the h1 exists with hb__h1 class (site CSS relies on it)
        title = get_title(md_text, date)
        rendered_path = os.path.join(RENDERED_DIR, date + ".html")
        with open(rendered_path, "w", encoding="utf-8") as f:
            f.write(html)
        size = os.path.getsize(rendered_path)
        summary = extract_summary(md_text)
        new_items.append({
            "date": date,
            "h1": title,
            "summary": summary,
            "size": size,
            "rendered": "heartbeat/rendered/" + date + ".html",
        })
        rendered_count += 1
        print(f"rendered {date} ({size} bytes)")

    # Sort items by date descending (newest first)
    new_items.sort(key=lambda x: x["date"], reverse=True)

    index["items"] = new_items
    index["count"] = len(new_items)
    index["latest"] = new_items[0]["date"] if new_items else None
    index["updated"] = new_items[0]["date"] if new_items else None

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"index.json updated: {index['count']} items, latest {index['latest']}")
    print(f"newly rendered: {rendered_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
