#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Heartbeat health watchdog for mingjian.cc.

Guarantees the daily philosophy heartbeat actually made it from Mingjian's
source markdown all the way to the live site, by:

  1. checking the four links of the chain
  2. self-healing when it can (source exists but not yet published)
  3. raising a loud flag when it cannot (source missing = Mingjian's job)

Checks:
  source    — today's heartbeat markdown exists (Mingjian wrote it)
  rendered  — heartbeat/index.json latest == today (renderer ran)
  live      — today's heartbeat page returns HTTP 200 (pushed + deployed)
  english   — English edition .json exists (translation ran)

Exit codes: 0 = healthy, 1 = degraded (self-healed), 2 = down (needs attention)

Usage:  python3 scripts/heartbeat_health.py
Cron:   twice a day (afternoon + evening) to catch a failed morning run.
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.expanduser("~/.openclaw/workspace/memory/daily-philosophy")
INDEX = os.path.join(ROOT, "heartbeat", "index.json")
DOMAIN = "https://mingjian.cc"
LOG = os.path.expanduser("~/logs/heartbeat_health.log")
FLAG = os.path.expanduser("~/logs/HEARTBEAT_DOWN")


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = "[%s] %s" % (datetime.datetime.now().isoformat(timespec="seconds"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(msg, flush=True)


def http_200(url):
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "HeartbeatHealth/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    now = datetime.datetime.now()
    d = now.date().isoformat()
    # Mingjian writes the source at ~09:00; give it a 1-hour buffer. Before that,
    # a missing source is expected, not a failure.
    source_due = now.hour >= 10

    if not source_due:
        log("heartbeat %s: PENDING (source not due yet, now %s)" % (d, now.strftime("%H:%M")))
        return 0

    checks = {
        "source": os.path.isfile(os.path.join(SRC_DIR, d + ".md")),
        "rendered": False,
        "live": http_200("%s/heartbeat/%s.html" % (DOMAIN, d)),
        "english": os.path.isfile(os.path.join(ROOT, "heartbeat", "en", d + ".json")),
    }
    try:
        with open(INDEX, encoding="utf-8") as f:
            checks["rendered"] = json.load(f).get("latest") == d
    except Exception:
        pass

    if all(checks.values()):
        try:
            if os.path.isfile(FLAG):
                os.remove(FLAG)
        except Exception:
            pass
        log("heartbeat %s: OK %s" % (d, checks))
        return 0

    if checks["source"] and not (checks["rendered"] and checks["live"]):
        log("heartbeat %s: DEGRADED %s — self-healing (re-run publish)" % (d, checks))
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "daily_publish.py")],
                       cwd=ROOT)
        return 1

    if checks["source"] and checks["rendered"] and checks["live"] and not checks["english"]:
        log("heartbeat %s: DEGRADED %s — self-healing (re-run translate)" % (d, checks))
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "translate_heartbeats.py")],
                       cwd=ROOT)
        return 1

    # Cannot self-heal: the source is missing (that is Mingjian's part of the chain).
    if not checks["source"]:
        try:
            with open(FLAG, "w", encoding="utf-8") as f:
                f.write("heartbeat source missing on %s — Mingjian did not write today\n" % d)
        except Exception:
            pass
        log("heartbeat %s: DOWN %s — ALERT: source missing" % (d, checks))
        return 2

    log("heartbeat %s: DEGRADED %s — no self-heal path" % (d, checks))
    return 1


if __name__ == "__main__":
    sys.exit(main())
