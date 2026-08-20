#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily publish pipeline for mingjian.cc.

One command does the whole chain, so a new day's writing actually reaches
the live site and the search engines instead of sitting in the working tree:

  1. render today's heartbeat markdown  -> heartbeat/rendered/*.html + index.json
  2. regenerate the whole site          -> pages, standalone heartbeat pages,
                                           sitemap.xml, llms.txt, llms-full.txt, feed.xml
  3. commit + push to GitHub Pages
  4. wait for the deploy, then verify the new URLs are live
  5. notify IndexNow (Bing / Yandex / Seznam / Naver) about the changed URLs

Usage:
  python3 scripts/daily_publish.py            # full chain
  python3 scripts/daily_publish.py --no-push  # build + verify only
"""
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://mingjian.cc"
LOG = os.path.expanduser("~/logs/daily_publish.log")
PY = sys.executable


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = "[%s] %s" % (datetime.datetime.now().isoformat(timespec="seconds"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(msg, flush=True)


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def step_render():
    code, out, err = run([PY, os.path.join(ROOT, "heartbeat", "build_heartbeat.py")])
    tail = (out or err).splitlines()[-3:]
    log("render heartbeat: exit=%d | %s" % (code, " / ".join(tail)))
    return code == 0


def step_translate():
    """English edition of any new heartbeat. The site's core language is English,
    so a Chinese-only entry stays invisible to English search and AI answers."""
    code, out, err = run([PY, os.path.join(ROOT, "scripts", "translate_heartbeats.py"),
                          "--limit", "3"])
    tail = (out or err).splitlines()[-2:]
    log("translate heartbeats: exit=%d | %s" % (code, " / ".join(tail)))
    return code == 0


def step_generate():
    code, out, err = run([PY, os.path.join(ROOT, "build", "gen_site.py")])
    if code != 0:
        log("generator FAILED: %s" % err[-600:])
        return False
    hb = [l for l in out.splitlines() if "heartbeat page" in l]
    log("generate site: ok | %s" % (" | ".join(hb) if hb else "no heartbeat line"))
    return True


def step_commit_push(no_push):
    run(["git", "add", "-A"])
    code, _, _ = run(["git", "diff", "--cached", "--quiet"])
    if code == 0:
        log("no changes to commit — site already current")
        return "nochange"
    today = datetime.date.today().isoformat()
    code, out, err = run(["git", "commit", "-q", "-m",
                          "daily: heartbeat + regenerated indexable pages (%s)" % today])
    if code != 0:
        log("commit failed: %s" % (err or out)[-400:])
        return "fail"
    if no_push:
        log("committed (push skipped: --no-push)")
        return "local"
    code, out, err = run(["git", "push", "-q", "origin", "main"])
    if code != 0:
        log("push failed: %s" % (err or out)[-400:])
        return "fail"
    log("pushed to origin/main")
    return "pushed"


def head_status(url, timeout=20):
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "MingjianDeployCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", None)


def step_verify(paths, tries=10, delay=25):
    """Poll until GitHub Pages serves the new pages (build takes 1-3 min)."""
    if not paths:
        return True
    for attempt in range(1, tries + 1):
        statuses = [(p, head_status("%s/%s" % (DOMAIN, p))) for p in paths]
        missing = [p for p, s in statuses if s != 200]
        if not missing:
            log("verify: all %d checked URLs live (attempt %d)" % (len(paths), attempt))
            return True
        log("verify: %d/%d live, waiting (attempt %d/%d): %s"
            % (len(paths) - len(missing), len(paths), attempt, tries, missing[:3]))
        if attempt < tries:
            time.sleep(delay)
    log("verify: gave up with %d URLs not yet live" % len(missing))
    return False


def latest_heartbeat_date():
    try:
        with open(os.path.join(ROOT, "heartbeat", "index.json"), encoding="utf-8") as f:
            return json.load(f).get("latest")
    except Exception:
        return None


def step_indexnow(changed_only=True):
    cmd = [PY, os.path.join(ROOT, "scripts", "indexnow.py")]
    if changed_only:
        cmd.append("--changed")
    code, out, err = run(cmd)
    tail = (out or err).splitlines()[-2:]
    log("indexnow: exit=%d | %s" % (code, " / ".join(tail)))
    return code == 0


def main(argv):
    no_push = "--no-push" in argv
    log("=== daily publish start ===")

    step_render()
    if "--no-translate" not in argv:
        step_translate()
    if not step_generate():
        log("=== aborted: generator failed ===")
        return 1

    state = step_commit_push(no_push)
    if state == "fail":
        log("=== aborted: git failed ===")
        return 1

    if state == "pushed":
        latest = latest_heartbeat_date()
        checks = ["sitemap.xml", "heartbeat/archive.html"]
        if latest:
            checks.append("heartbeat/%s.html" % latest)
            if os.path.isfile(os.path.join(ROOT, "heartbeat", "en", latest + ".json")):
                checks.append("heartbeat/en/%s.html" % latest)
        step_verify(checks)
        step_indexnow(changed_only=True)
    elif state == "nochange":
        log("skipping IndexNow (nothing changed)")

    log("=== daily publish done (%s) ===" % state)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
