#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish the site: regenerate all pages (incl. blog) and git push."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
