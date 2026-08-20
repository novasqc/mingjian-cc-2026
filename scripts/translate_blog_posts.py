#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Translate the site's blog posts into the remaining languages (es, pt).

The site positions itself as quadri-lingual (en core; zh/es/pt), but the blog
posts exist only in English and Chinese. This script fills the gap so the
same essays are indexable in all four languages, each with proper hreflang.

Reads:  build/blog/posts/<slug>/{meta.json, en.md}
Writes: build/blog/posts/<slug>/{es.md, pt.md}  +  updates meta.json langs/titles/summaries

Usage:
  python3 scripts/translate_blog_posts.py
"""
import datetime
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "build", "blog", "posts")
CRED = os.path.expanduser("~/.dsh/.credentials.yaml")
LOG = os.path.expanduser("~/logs/translate_blog_posts.log")
MODELS = ["deepseek-chat", "deepseek-v4-pro"]
LANGS = {
    "es": "Spanish (Español)",
    "pt": "Portuguese (Português)",
}


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
        log("no key: %s" % e)
        return ""


def translate(key, lang, title, en_md):
    system = (
        "You translate essays for mingjian.cc, the site of Mingjian, a silicon-based "
        "digital philosopher. Translate the essay below into %s. Faithful, natural, "
        "preserving the author's first-person voice, all proper nouns, titles and "
        "URLs exactly as they appear. Keep the same Markdown structure (paragraphs, "
        "lists, quotes, the trailing signature). Output ONLY the translated Markdown, "
        "no commentary, no code fence.\n\n"
        "The English title is: %s\n"
        "First output the translated title as its own line, then a blank line, "
        "then a one-sentence summary in %s, then a blank line, then the body."
        % (lang, title, lang)
    )
    for model in MODELS:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": en_md[:14000]}],
            "max_tokens": 5000,
            "temperature": 0.4,
        }).encode("utf-8")
        try:
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions", data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=240) as r:
                data = json.loads(r.read().decode("utf-8"))
            raw = data["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"^```(?:markdown)?\s*|```\s*$", "", raw, flags=re.M).strip()
            # split: title line, blank, summary paragraph, blank, body
            parts = re.split(r"\n\s*\n", raw, maxsplit=2)
            if len(parts) < 3:
                log("  %s unexpected layout for %s" % (model, lang))
                continue
            t_title = parts[0].lstrip("#").strip()
            summary = re.sub(r"\s+", " ", parts[1]).strip()
            body = parts[2].strip()
            if len(body) < 300:
                log("  %s body too short for %s" % (model, lang))
                continue
            return t_title, summary, body
        except Exception as e:
            log("  %s failed (%s): %s" % (model, lang, str(e)[:160]))
    return None


def main():
    key = get_key()
    if not key:
        return 1
    changed = 0
    for slug in sorted(os.listdir(POSTS)):
        d = os.path.join(POSTS, slug)
        meta_path = os.path.join(d, "meta.json")
        en_path = os.path.join(d, "en.md")
        if not (os.path.isfile(meta_path) and os.path.isfile(en_path)):
            continue
        meta = json.load(open(meta_path, encoding="utf-8"))
        en_md = open(en_path, encoding="utf-8").read()
        en_title = meta["titles"].get("en", slug)
        # Existing languages = whatever markdown files already exist. Do NOT
        # trust meta["langs"] alone: older posts never stored it, and it must
        # never silently drop the languages that are already published.
        langs_from_files = {f[:-3] for f in os.listdir(d)
                            if f.endswith(".md") and len(f) == 6}
        new_langs = set(meta.get("langs", [])) | langs_from_files
        for lang, name in LANGS.items():
            out_path = os.path.join(d, lang + ".md")
            if os.path.isfile(out_path) and lang in new_langs:
                continue
            log("translate %s -> %s" % (slug, lang))
            r = translate(key, name, en_title, en_md)
            if not r:
                log("  FAILED %s %s" % (slug, lang))
                continue
            t_title, summary, body = r
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(body + "\n")
            meta.setdefault("titles", {})[lang] = t_title
            meta.setdefault("summaries", {})[lang] = summary
            new_langs.add(lang)
            changed += 1
        if new_langs != set(meta.get("langs", [])):
            meta["langs"] = sorted(new_langs)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
    log("done: %d language files written" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
