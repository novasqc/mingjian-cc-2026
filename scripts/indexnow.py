#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IndexNow submitter for mingjian.cc.

IndexNow is a shared instant-indexing protocol: one POST notifies Bing,
Yandex, Seznam and Naver that URLs changed. No account or OAuth needed —
only a key file hosted at the site root.

  key file:  https://mingjian.cc/<KEY>.txt   (must contain exactly <KEY>)

Usage:
  python3 scripts/indexnow.py              # submit every URL in sitemap.xml
  python3 scripts/indexnow.py --changed    # only URLs whose files changed in HEAD
  python3 scripts/indexnow.py URL [URL...] # submit specific URLs

Writes a log to ~/logs/indexnow.log and a JSON receipt to
~/ai_index_reports/indexnow-<date>.json so the daily monitor can report it.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "mingjian.cc"
KEY = "dc0387ff0ea06b3b4527ebb743f20770"
KEY_LOCATION = "https://%s/%s.txt" % (DOMAIN, KEY)
SITEMAP = os.path.join(ROOT, "sitemap.xml")
LOG = os.path.expanduser("~/logs/indexnow.log")
RECEIPT_DIR = os.path.expanduser("~/ai_index_reports")

# IndexNow endpoints. api.indexnow.org fans out to all participants; the
# engine-specific endpoints are kept as explicit fallbacks.
ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
    "https://yandex.com/indexnow",
]
BATCH = 10000  # protocol maximum per request


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = "[%s] %s" % (datetime.datetime.now().isoformat(timespec="seconds"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(msg)


def sitemap_urls():
    try:
        with open(SITEMAP, encoding="utf-8") as f:
            return re.findall(r"<loc>([^<]+)</loc>", f.read())
    except Exception as e:
        log("cannot read sitemap: %s" % e)
        return []


def changed_urls():
    """URLs for .html files changed in the most recent commit."""
    try:
        out = subprocess.run(
            ["git", "-C", ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            capture_output=True, text=True, check=True).stdout
    except Exception as e:
        log("git diff-tree failed: %s" % e)
        return []
    known = set(sitemap_urls())
    urls = []
    for path in out.split():
        if not path.endswith(".html"):
            continue
        u = "https://%s/%s" % (DOMAIN, path)
        if u in known:
            urls.append(u)
    return urls


def verify_key_live():
    """The endpoints reject submissions if the key file is not reachable."""
    try:
        req = urllib.request.Request(
            KEY_LOCATION, headers={"User-Agent": "MingjianIndexNow/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", errors="replace").strip()
        if body == KEY:
            return True, "key file live"
        return False, "key file content mismatch: %r" % body[:60]
    except Exception as e:
        return False, "key file unreachable: %s" % e


def submit(endpoint, urls):
    payload = json.dumps({
        "host": DOMAIN,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=payload,
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "MingjianIndexNow/1.0 (+https://mingjian.cc)"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, (r.read().decode("utf-8", errors="replace") or "")[:200]
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", errors="replace") or "")[:200]
    except Exception as e:
        return None, str(e)[:200]


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    only_changed = "--changed" in argv

    if args:
        urls = args
        mode = "explicit"
    elif only_changed:
        urls = changed_urls()
        mode = "changed"
    else:
        urls = sitemap_urls()
        mode = "sitemap"

    if not urls:
        log("nothing to submit (mode=%s)" % mode)
        return 0

    ok, detail = verify_key_live()
    log("key check: %s" % detail)
    if not ok:
        log("aborting: key file must be live at %s before submitting" % KEY_LOCATION)
        return 1

    results = []
    for endpoint in ENDPOINTS:
        for i in range(0, len(urls), BATCH):
            chunk = urls[i:i + BATCH]
            status, body = submit(endpoint, chunk)
            # 200 = accepted, 202 = accepted/pending key validation
            state = "ok" if status in (200, 202) else "fail"
            log("%s -> %s %s (%d urls) %s" % (endpoint, status, state, len(chunk), body))
            results.append({"endpoint": endpoint, "status": status,
                            "count": len(chunk), "state": state, "body": body})

    accepted = sum(1 for r in results if r["state"] == "ok")
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    receipt = {
        "submitted_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "url_count": len(urls),
        "endpoints_ok": accepted,
        "endpoints_total": len(results),
        "results": results,
        "sample_urls": urls[:5],
    }
    stamp = datetime.date.today().isoformat()
    with open(os.path.join(RECEIPT_DIR, "indexnow-%s.json" % stamp), "w",
              encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    with open(os.path.join(RECEIPT_DIR, "indexnow-latest.json"), "w",
              encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)

    log("submitted %d URLs (mode=%s); %d/%d endpoint responses accepted"
        % (len(urls), mode, accepted, len(results)))
    return 0 if accepted else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
