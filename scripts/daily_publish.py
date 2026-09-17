#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily publish pipeline for mingjian.cc.

One command does the whole chain, so a new day's writing actually reaches
the live site and the search engines instead of sitting in the working tree:

  1. render today's heartbeat markdown  -> heartbeat/rendered/*.html + index.json
  2. regenerate the whole site          -> pages, standalone heartbeat pages,
                                           sitemap.xml, llms.txt, llms-full.txt, feed.xml
  3. audit all generated pages
  4. with --publish: commit staged changes + push to GitHub Pages
  5. verify deployed file hashes
  6. notify IndexNow (Bing / Yandex / Seznam / Naver) about the changed URLs

Usage:
  python3 scripts/daily_publish.py            # local render/build/audit only
  python3 scripts/daily_publish.py --publish  # publish reviewed, staged changes
  python3 scripts/daily_publish.py --no-push  # alias for local build only
"""
import datetime
import argparse
import hashlib
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


def step_generate():
    code, out, err = run([PY, os.path.join(ROOT, "build", "gen_site.py")])
    if code != 0:
        log("generator FAILED: %s" % err[-600:])
        return False
    hb = [l for l in out.splitlines() if "heartbeat page" in l]
    log("generate site: ok | %s" % (" | ".join(hb) if hb else "no heartbeat line"))
    return True


def step_audit():
    """A failed audit blocks publication."""
    code, out, err = run([PY, os.path.join(ROOT, "scripts", "audit_site.py"),
                          "--quiet"])
    if code == 0:
        log("audit: ok (0 issues)")
        return True
    tail = (out or err).strip().splitlines()[-6:]
    log("audit: %d issue(s) FOUND\n%s" % (len(tail), "\n".join(tail)))
    return False


def step_commit_push():
    # The operator reviews and stages changes explicitly; never sweep arbitrary files in.
    code, _, err = run(["git", "diff", "--quiet"])
    if code != 0:
        log("publish blocked: review and stage working-tree changes first")
        return False
    code, untracked, err = run(["git", "ls-files", "--others", "--exclude-standard"])
    if code != 0 or untracked:
        log("publish blocked: untracked files need review")
        return False
    code, _, err = run(["git", "diff", "--cached", "--quiet"])
    if code not in (0, 1):
        log("cannot inspect staged changes: " + err)
        return False
    if code == 1:
        code, out, err = run(["git", "commit", "-m",
                             "site: reviewed content and generated pages (%s)" % datetime.date.today()])
        if code != 0:
            log("commit failed: " + (err or out)[-400:])
            return False
    # Always push: a prior attempt may have committed successfully before push failed.
    code, out, err = run(["git", "push", "origin", "HEAD:main"])
    if code != 0:
        log("push failed: " + (err or out)[-400:])
        return False
    return True


def remote_matches(path):
    try:
        with open(os.path.join(ROOT, path), "rb") as f:
            expected = hashlib.sha256(f.read()).digest()
        req = urllib.request.Request(DOMAIN + "/" + path,
                                     headers={"User-Agent": "MingjianDeployCheck/2.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status == 200 and hashlib.sha256(response.read()).digest() == expected
    except (OSError, ValueError):
        return False


def step_verify(paths, tries=6, delay=20):
    for attempt in range(tries):
        missing = [path for path in paths if not remote_matches(path)]
        if not missing:
            log("verified: %d live files match local content" % len(paths))
            return True
        log("deploy pending: %s" % ", ".join(missing[:4]))
        if attempt + 1 < tries:
            time.sleep(delay)
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
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--publish", action="store_true", help="publish explicitly reviewed and staged changes")
    group.add_argument("--no-push", action="store_true", help="local build only (the default)")
    parser.add_argument("--no-translate", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv[1:])
    log("=== build start ===")
    for name, step in [("render", step_render), ("generate", step_generate), ("audit", step_audit)]:
        if not step():
            log("aborted: " + name + " failed")
            return 1
    if not args.publish:
        log("local build verified; Git and external APIs untouched")
        return 0
    if not step_commit_push():
        return 1
    checks = ["sitemap.xml", "index.html", "zh/index.html", "heartbeat/archive.html"]
    latest = latest_heartbeat_date()
    if latest:
        checks.append("heartbeat/%s.html" % latest)
    if not step_verify(checks):
        log("deployment verification failed; do not report this as a successful release")
        return 1
    if not step_indexnow(changed_only=True):
        log("site deployed, but index notification failed")
        return 2
    log("=== deployed and verified ===")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
