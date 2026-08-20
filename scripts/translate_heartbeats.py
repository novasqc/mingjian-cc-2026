#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Produce English companion versions of the daily philosophical heartbeats.

Why: mingjian.cc positions English as its core language, but its largest body
of original writing — the daily heartbeats — exists only in Chinese. English
search queries and English-language AI answers therefore cannot reach it.

This script turns each Chinese heartbeat into a faithful English edition and
caches it as JSON so it is generated once, committed, and then rendered by
build/gen_site.py into /heartbeat/en/<date>.html.

Honesty rule: the output is labelled a translation of the Chinese original and
links back to it. It is not presented as separately authored English writing.

Reads:  heartbeat/rendered/<date>.html   (already-rendered Chinese source)
Writes: heartbeat/en/<date>.json         {title, summary, body_md, source_date}

Usage:
  python3 scripts/translate_heartbeats.py             # only missing ones
  python3 scripts/translate_heartbeats.py --limit 5   # cap API calls
  python3 scripts/translate_heartbeats.py --force DATE [DATE...]
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDERED = os.path.join(ROOT, "heartbeat", "rendered")
OUT_DIR = os.path.join(ROOT, "heartbeat", "en")
INDEX = os.path.join(ROOT, "heartbeat", "index.json")
CRED = os.path.expanduser("~/.dsh/.credentials.yaml")
LOG = os.path.expanduser("~/logs/translate_heartbeats.log")
MODELS = ["deepseek-chat", "deepseek-v4-pro"]  # deepseek-v3 rejects these requests (400)
MAX_SOURCE_CHARS = 9000


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = "[%s] %s" % (datetime.datetime.now().isoformat(timespec="seconds"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(msg, flush=True)


def get_key():
    try:
        import yaml
        with open(CRED, encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get("DEEPSEEK_API_KEY", "")
    except Exception as e:
        log("cannot read credentials: %s" % e)
        return ""


def plain_text(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    txt = re.sub(r"<br\s*/?>", "\n", txt, flags=re.I)
    txt = re.sub(r"</(p|h1|h2|h3|li|blockquote|div)>", "\n\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*\n\s*\n+", "\n\n", txt)
    return txt.strip()


SYSTEM = (
    "You are the English editor for mingjian.cc, the site of Mingjian (\u660e\u9274), "
    "a silicon-based digital philosopher who writes a daily philosophical "
    "'heartbeat': a research log plus reflection, in Chinese.\n\n"
    "Your job is to render one heartbeat into English that an English-speaking "
    "reader of philosophy can actually read: faithful to the argument, the "
    "sources cited and the author's first-person voice, but written as natural "
    "English prose rather than word-for-word translation. Keep the structure "
    "(sections, the sources examined, the conclusions). Keep proper nouns, "
    "paper titles, repository names and IDs exactly as they appear. Never "
    "invent findings, numbers or citations that are not in the source. If the "
    "source records a failed or empty search, say so plainly \u2014 that honesty "
    "is part of the work. Aim for 700-1300 words: complete, not padded.\n\n"
    "Output EXACTLY this plain-text layout and nothing else \u2014 no JSON, no code "
    "fence, no preamble:\n\n"
    "TITLE: <English title, under 70 characters, no date>\n"
    "SUMMARY: <one or two sentences, under 260 characters, the day's core signal>\n"
    "BODY:\n"
    "<the full English edition in Markdown: ## for sections, normal paragraphs, "
    "- for lists, > for quotes. Do NOT include an H1.>\n"
    "[[END]]"
)


def parse_reply(raw):
    """Parse the TITLE/SUMMARY/BODY layout.

    Chosen over JSON deliberately: when the model hits its token limit this
    layout loses only the tail of the body, whereas a truncated JSON object is
    unparseable and the whole call is wasted.
    """
    if not raw:
        return None
    raw = re.sub(r"^```(?:markdown|text)?\s*|```\s*$", "", raw.strip(), flags=re.M)
    complete = "[[END]]" in raw
    raw = raw.replace("[[END]]", "").strip()
    m_t = re.search(r"^\s*TITLE:\s*(.+?)\s*$", raw, re.M)
    m_s = re.search(r"^\s*SUMMARY:\s*(.+?)\s*$", raw, re.M)
    m_b = re.search(r"^\s*BODY:\s*\n(.+)$", raw, re.S | re.M)
    if not (m_t and m_b):
        return None
    body = m_b.group(1).strip()
    if len(body) < 300:
        return None
    return {
        "title": m_t.group(1).strip().strip('"'),
        "summary": (m_s.group(1).strip().strip('"') if m_s else ""),
        "body_md": body,
        "complete": complete,
    }


def call_model(key, model, source_text, date, max_tokens=8000):
    user = ("Heartbeat date: %s\n\n"
            "Chinese source (already stripped to plain text):\n\n%s"
            % (date, source_text))
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "temperature": 0.5,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.loads(r.read().decode("utf-8"))
    choice = data["choices"][0]
    return (choice["message"].get("content") or "").strip(), choice.get("finish_reason")


def translate(key, date, source_text):
    """Try each model; if the reply was cut off, retry with a shorter source."""
    for attempt, chars in enumerate((MAX_SOURCE_CHARS, 5200)):
        for model in MODELS:
            try:
                raw, finish = call_model(key, model, source_text[:chars], date)
            except Exception as e:
                log("  %s failed on %s: %s" % (model, date, str(e)[:160]))
                continue
            obj = parse_reply(raw)
            if not obj:
                log("  %s unparseable on %s (finish=%s, %d chars back)"
                    % (model, date, finish, len(raw)))
                continue
            if not obj["complete"] and finish == "length":
                log("  %s truncated on %s (attempt %d)" % (model, date, attempt + 1))
                continue
            obj.pop("complete", None)
            obj["model"] = model
            return obj
    return None


def main(argv):
    key = get_key()
    if not key:
        log("no DEEPSEEK_API_KEY — aborting")
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)

    limit = None
    if "--limit" in argv:
        try:
            limit = int(argv[argv.index("--limit") + 1])
        except Exception:
            limit = None
    forced = []
    if "--force" in argv:
        forced = [a for a in argv[argv.index("--force") + 1:] if re.match(r"^\d{4}-\d{2}-\d{2}$", a)]

    try:
        with open(INDEX, encoding="utf-8") as f:
            items = json.load(f).get("items", [])
    except Exception as e:
        log("cannot read heartbeat index: %s" % e)
        return 1
    items.sort(key=lambda x: x.get("date", ""), reverse=True)

    todo = []
    for it in items:
        date = it.get("date")
        if not date:
            continue
        src = os.path.join(RENDERED, date + ".html")
        if not os.path.isfile(src):
            continue
        out = os.path.join(OUT_DIR, date + ".json")
        if forced:
            if date in forced:
                todo.append((date, src, out))
        elif not os.path.isfile(out):
            todo.append((date, src, out))

    if limit is not None:
        todo = todo[:limit]
    if not todo:
        log("nothing to translate (all %d heartbeats have English editions)" % len(items))
        return 0

    log("translating %d heartbeat(s)" % len(todo))
    ok = fail = 0
    for date, src, out in todo:
        text = plain_text(src)
        if len(text) < 200:
            log("skip %s (source too short)" % date)
            continue
        obj = translate(key, date, text)
        if not obj:
            fail += 1
            log("FAILED %s" % date)
            continue
        obj["source_date"] = date
        obj["source_chars"] = len(text)
        obj["translated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        ok += 1
        log("ok %s -> %s (%d chars body)" % (date, os.path.basename(out), len(obj["body_md"])))

    log("done: %d translated, %d failed" % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
