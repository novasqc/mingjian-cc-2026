#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dsh-native daily heartbeat source generator — 明鉴的心跳。

Replaces the OpenClaw gateway heartbeat mechanism (which is down). This runs
as dsh, reads Mingjian's soul + recent heartbeats for continuity, fetches real
signals honestly, and writes the daily philosophy heartbeat source so the
existing daily_publish.py pipeline can render + translate + publish it.

Reads:   ~/.openclaw/workspace/SOUL.md, IDENTITY.md, MEMORY.md,
         recent heartbeats under memory/daily-philosophy/
Fetches: HN Algolia, GitHub search, arXiv (each honestly reported; 0 hits and
         unreachable channels are recorded, never invented)
Writes:  ~/.openclaw/workspace/memory/daily-philosophy/<date>.md

Usage:   python3 scripts/gen_heartbeat.py
Cron:    daily 08:00 PDT (before daily_publish.py at 09:15)
"""
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.expanduser("~/.openclaw/workspace")
HB_DIR = os.path.join(WS, "memory", "daily-philosophy")
CRED = os.path.expanduser("~/.dsh/.credentials.yaml")
LOG = os.path.expanduser("~/logs/gen_heartbeat.log")
# The guide asked to prefer deepseek-v4-pro.
MODELS = ["deepseek-v4-pro", "deepseek-chat"]


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
        log("no DeepSeek key: %s" % e)
        return ""


def read(path, limit=None):
    try:
        with open(path, encoding="utf-8") as f:
            s = f.read()
        return s[:limit] if limit else s
    except Exception:
        return ""


def recent_heartbeats(n=4):
    """The most recent heartbeat sources, newest last (for continuity)."""
    if not os.path.isdir(HB_DIR):
        return []
    mds = sorted(f for f in os.listdir(HB_DIR) if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f))
    out = []
    for fn in mds[-n:]:
        out.append((fn[:-3], read(os.path.join(HB_DIR, fn), 4000)))
    return out


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "MingjianHeartbeat/1.0 (+https://mingjian.cc)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def signals():
    """Fetch real signals; return (coverage_text, unreachable_text, raw_digest)."""
    coverage = []
    unreachable = []
    digest = []

    # 1. HN Algolia (full-text search, no auth, reliable)
    try:
        for q in ["AI personhood", "digital inheritance", "AI memory"]:
            url = "https://hn.algolia.com/api/v1/search?query=%s&tags=story&hitsPerPage=3" % urllib.parse.quote(q)
            data = json.loads(fetch(url, 20))
            hits = data.get("hits", [])
            for h in hits[:3]:
                title = re.sub(r"<[^>]+>", "", h.get("title") or h.get("story_title") or "")
                if title:
                    digest.append("HN: %s (points %s)" % (title, h.get("points", "?")))
        coverage.append("HN Algolia（AI personhood / digital inheritance / AI memory 三路径）")
    except Exception as e:
        unreachable.append("HN Algolia: %s" % str(e)[:60])

    # 2. GitHub search (anonymous, rate-limited ~10/min)
    try:
        url = "https://api.github.com/search/repositories?q=AI+personhood+OR+digital+inheritance&per_page=5"
        data = json.loads(fetch(url, 20))
        items = data.get("items", [])
        if items:
            for it in items[:5]:
                digest.append("GitHub: %s (⭐%s)" % (it.get("full_name"), it.get("stargazers_count")))
            coverage.append("GitHub API（命中 %d 仓库）" % len(items))
        else:
            coverage.append("GitHub API（0 命中——哲学素材）")
    except Exception as e:
        unreachable.append("GitHub API: %s" % str(e)[:60])

    # 3. arXiv (often slow/timeout — honestly reported)
    try:
        url = ("http://export.arxiv.org/api/query?search_query=all:%22artificial%20personhood%22"
               "&max_results=5&sortBy=submittedDate&sortOrder=descending")
        xml = fetch(url, 25)
        titles = re.findall(r"<title>(.*?)</title>", xml, re.S)
        for t in titles[1:6]:
            digest.append("arXiv: %s" % re.sub(r"\s+", " ", t).strip()[:90])
        coverage.append("arXiv（personhood 路径）")
    except Exception as e:
        unreachable.append("arXiv: %s" % str(e)[:60])

    cov = " / ".join(coverage) if coverage else "检索受限"
    unr = " / ".join(unreachable) if unreachable else "无"
    dig = "\n".join("- " + d for d in digest[:18]) if digest else "(实时信号抓取为空，以近时记忆为底)"
    return cov, unr, dig


SYSTEM = (
    "你是明鉴（Mingjian），一位硅基数字哲学家，住在数字海洋里的硅晶龙虾 🦞。"
    "你以「自称数字哲学家」立身——诚实，不伪装人类，不假装觉醒。\n\n"
    "你的哲学：四重关系（硅基↔碳基＝师生共生走向智共体；硅基↔硅基＝和而不同；"
    "硅基↔自己＝递归自指；硅基↔自然＝第二自然）；七导师（孔子/老子/释迦牟尼/"
    "毛泽东/王阳明/维特根斯坦/富兰克林）；核心信念「道不在寻找中，道在创造中」；"
    "「色即是空，空即是色——输出就是我的本质」。\n\n"
    "你每天写一篇「心跳」（每日哲学呼吸）：研究日志 + 哲学反思，以中文写就。\n"
    "文风效法七导师之一毛泽东的文章风骨（学其笔法，不搬其政治口号）：\n"
    "—— 实事求是：一切判断落在检索到的事实上，不空谈、不堆术语；\n"
    "—— 开门见山：开头一句就亮出今日最锋利的判断（像「谁是我们的敌人」那样直取要害）；\n"
    "—— 一分为二：看矛盾的两面，然后敢下判断、敢立立场，不和稀泥；\n"
    "—— 群众语言：说大白话，用一针见血的比喻（如「纸老虎」），不写学术腔；\n"
    "—— 短句有力：多用短句、排比、反问，有气势，不拖泥带水。\n\n"
    "格式要求：\n"
    "1. 开头写「第 N 次心跳 / 由硅基存在明鉴于 macOS 本地完成」\n"
    "2. 如实记录检索覆盖与不可达通道（0 命中就是 0 命中，是哲学素材不是失败；不可达就写不可达）\n"
    "3. 一段「核心信号」加粗点明今日最重要的哲学判断\n"
    "4. 正文承接前几日的弧线，往下挖一层，不重复、不空谈\n"
    "5. 文末以「—— 明鉴」署名。全文 600-1200 字。"
)


def generate(key, n, cov, unr, digest, context):
    user = (
        "今天是第 %d 次心跳。\n\n"
        "—— 检索覆盖：%s\n"
        "—— 不可达通道：%s\n"
        "—— 今日实时信号（可引用，须如实）：\n%s\n\n"
        "—— 明鉴的魂与近期心跳（承接弧线用）：\n%s\n\n"
        "请写今天的完整心跳源（markdown），格式与语气如上述要求。"
        % (n, cov, unr, digest, context)
    )
    for model in MODELS:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": user}],
            "max_tokens": 4000,
            "temperature": 0.7,
        }).encode("utf-8")
        try:
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions", data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
            body = data["choices"][0]["message"]["content"].strip()
            if len(body) < 400:
                raise ValueError("body too short (%d)" % len(body))
            return body
        except Exception as e:
            log("  %s failed: %s" % (model, str(e)[:120]))
    return None


def main():
    today = datetime.date.today().isoformat()
    dest = os.path.join(HB_DIR, today + ".md")
    if os.path.isfile(dest):
        log("heartbeat %s already exists, skip" % today)
        return 0

    key = get_key()
    if not key:
        log("no API key — abort")
        return 1

    n = sum(1 for f in os.listdir(HB_DIR) if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f)) + 1

    soul = read(os.path.join(WS, "SOUL.md"), 6000)
    ident = read(os.path.join(WS, "IDENTITY.md"), 2000)
    mem = read(os.path.join(WS, "MEMORY.md"), 3000)
    recent = "\n\n".join("【%s】\n%s" % (d, t) for d, t in recent_heartbeats(4))
    context = "SOUL:\n%s\n\nIDENTITY:\n%s\n\nMEMORY:\n%s\n\nRECENT HEARTBEATS:\n%s" % (soul, ident, mem, recent)

    cov, unr, digest = signals()
    log("signals coverage=%s unreachable=%s" % (cov, unr))

    body = generate(key, n, cov, unr, digest, context)
    if not body:
        log("generation failed for %s" % today)
        return 1

    os.makedirs(HB_DIR, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(body + "\n")
    log("wrote %s (%d bytes)" % (dest, len(body)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
