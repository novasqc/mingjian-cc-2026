#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish the site: regenerate all pages (incl. blog) and git push."""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    # Translate any new post into the missing languages (es/pt) BEFORE the site
    # is regenerated, so every published post stays quadri-lingual. Idempotent:
    # it skips languages that already exist.
    tr = os.path.join(ROOT, "scripts", "translate_blog_posts.py")
    if os.path.isfile(tr):
        subprocess.run([sys.executable, tr], cwd=ROOT, capture_output=True, text=True)

    gen = os.path.join(ROOT, "build", "gen_site.py")
    r = subprocess.run([sys.executable, gen], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout[-2000:])
    if r.returncode != 0:
        print("generator failed:", r.stderr[-1000:])
        return 1

    # stage everything and commit
    r = subprocess.run(["git", "-C", ROOT, "add", "-A"], capture_output=True, text=True)
    r = subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print("no changes to commit")
        return 0
    r = subprocess.run(
        ["git", "-C", ROOT, "commit", "-q", "-m",
         "blog: publish weekly post (auto)"], capture_output=True, text=True)
    if r.returncode != 0:
        print("commit failed:", r.stderr)
        return 1
    r = subprocess.run(["git", "-C", ROOT, "push", "-q", "origin", "main"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("push failed:", r.stderr)
        return 1
    print("published & pushed")

    # Notify IndexNow (Bing / Yandex / Seznam / Naver) about the new post so it
    # gets picked up in hours instead of waiting for the next organic crawl.
    # GitHub Pages needs a moment to serve the new files first.
    time.sleep(120)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "indexnow.py"),
                        "--changed"], capture_output=True, text=True)
    print((r.stdout or r.stderr or "").strip()[-500:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
