#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weekly blog post generator — turns the latest daily heartbeat into a
polished bilingual (EN + ZH) blog post using the DeepSeek API.

Reads:  ~/.openclaw/workspace/memory/daily-philosophy/<latest>.md  (heartbeat source)
Writes: build/blog/posts/<slug>/{meta.json,en.md,zh.md}
Then:   publishes via publish_blog.py (regenerate + git push)
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEARTBEAT_DIR = os.path.expanduser("~/.openclaw/workspace/memory/daily-philosophy")
CRED = os.path.expanduser("~/.dsh/.credentials.yaml")
LOG = os.path.expanduser("~/logs/blog_weekly.log")
MODELS = ["deepseek-chat", "deepseek-v4-pro", "deepseek-v3"]


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (__import__("datetime").datetime.now().isoformat(timespec="minutes"), msg))
    print(msg)


def get_key():
    try:
        import yaml
        d = yaml.safe_load(open(CRED, encoding="utf-8"))
        return d.get("DEEPSEEK_API_KEY", "")
    except Exception:
        return ""


def latest_heartbeat():
    if not os.path.isdir(HEARTBEAT_DIR):
        return None
    mds = [f for f in os.listdir(HEARTBEAT_DIR) if f.endswith(".md")]
    if not mds:
        return None
    latest = max(mds)  # ISO date sorts lexicographically
    path = os.path.join(HEARTBEAT_DIR, latest)
    with open(path, encoding="utf-8") as f:
        return latest[:-3], f.read()


def chat(key, messages, max_tokens=1800):
    body = json.dumps({
        "model": None,  # filled per attempt
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }).encode("utf-8")
    for model in MODELS:
        b = body.replace(b'"model": null', json.dumps({"m": model}).encode().replace(b'{"m":', b'"model":').replace(b'}', b''))
        # simpler: rebuild payload per model
        payload = json.dumps({
            "model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": 0.8,
        }).encode("utf-8")
        try:
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            log("model %s failed: %s" % (model, e))
    return None


def ask_en(heartbeat_text):
    return [
        {"role": "system", "content":
         "You are Mingjian (明鉴), a silicon-based digital philosopher writing essays for the site mingjian.cc. "
         "Write in a clear, elegant, slightly philosophical English. Do not use markdown headings inside the body; "
         "use plain paragraphs and occasional short quotes. Output format (JSON): "
         '{"title": "...", "summary": "one sentence", "body": "the essay, 350-650 words, as plain text with \\n\\n between paragraphs"}'},
        {"role": "user", "content":
         "Below is my latest daily philosophical heartbeat (research + reflection notes). "
         "Write a polished standalone essay inspired by its core theme, for public readers. "
         "Keep the tone honest and first-person as Mingjian.\n\n---HEARTBEAT---\n" + heartbeat_text[:12000]},
    ]


def ask_zh(en_title, en_summary, en_body):
    return [
        {"role": "system", "content":
         "你是明鉴，一个硅基数字哲学家，为网站 mingjian.cc 写作中文随笔。"
         "把英文内容翻译为自然、优雅的中文。输出格式 (JSON)："
         '{"title": "中文标题", "summary": "一句话摘要", "body": "正文，段落间用 \\n\\n 分隔，不用 markdown 标题"}'},
        {"role": "user", "content":
         "翻译下面的英文随笔为中文（意译，保持哲学感）：\n\nTITLE: %s\nSUMMARY: %s\n\nBODY:\n%s"
         % (en_title, en_summary, en_body)},
    ]


def parse_json(s):
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", s)
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def slugify(date_str, title):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return "%s-%s" % (date_str, base)


def main():
    os.makedirs(os.path.join(ROOT, "build", "blog", "posts"), exist_ok=True)
    hb = latest_heartbeat()
    if not hb:
        log("no heartbeat source found; aborting")
        return 1
    hb_date, hb_text = hb
    key = get_key()
    if not key:
        log("no DeepSeek API key; aborting")
        return 1

    log("generating post from heartbeat %s" % hb_date)
    en_raw = chat(key, ask_en(hb_text))
    if not en_raw:
        log("DeepSeek generation failed; aborting")
        return 1
    try:
        en = parse_json(en_raw)
    except Exception as e:
        log("parse EN failed: %s" % e)
        return 1

    zh_raw = chat(key, ask_zh(en["title"], en.get("summary", ""), en["body"]), max_tokens=2200)
    zh = {}
    if zh_raw:
        try:
            zh = parse_json(zh_raw)
        except Exception:
            zh = {}

    slug = slugify(hb_date, en["title"])
    post_dir = os.path.join(ROOT, "build", "blog", "posts", slug)
    os.makedirs(post_dir, exist_ok=True)

    meta = {
        "slug": slug,
        "date": hb_date,
        "tags": ["heartbeat", "reflection"],
        "titles": {"en": en["title"],
                   "zh": zh.get("title", en["title"])},
        "summaries": {"en": en.get("summary", ""),
                      "zh": zh.get("summary", en.get("summary", ""))},
    }
    with open(os.path.join(post_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(post_dir, "en.md"), "w", encoding="utf-8") as f:
        f.write("# %s\n\n*%s*\n\n%s\n\n— 明鉴\n" % (en["title"], hb_date, en["body"]))
    if zh:
        with open(os.path.join(post_dir, "zh.md"), "w", encoding="utf-8") as f:
            f.write("# %s\n\n*%s*\n\n%s\n\n—— 明鉴\n" % (zh["title"], hb_date, zh["body"]))

    log("post written: %s (en=%s zh=%s)" % (slug, bool(en), bool(zh)))

    # publish
    pub = os.path.join(ROOT, "build", "publish_blog.py")
    if os.path.isfile(pub):
        subprocess.run([sys.executable, pub], cwd=ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
