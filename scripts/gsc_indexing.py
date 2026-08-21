#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Search Console — authoritative indexing report for mingjian.cc.

Two modes:
  python3 scripts/gsc_indexing.py --auth   # one-time OAuth (opens your browser)
  python3 scripts/gsc_indexing.py          # query GSC with the stored token

Prereqs (one-time, see README in the terminal output):
  1. Google Cloud Console: enable "Search Console API", create a Desktop
     OAuth client, download JSON.
  2. Save that JSON at  ~/.dsh/gsc_client.json  (fields: client_id,
     client_secret, project_id, redirect_uris).
  3. Run `--auth` once on THIS Mac, sign in as the Google account that owns
     the Search Console property, approve read-only access.

Reports (read-only):
  - verified sites (confirm mingjian.cc)
  - sitemap submission status + last download + discovered URLs
  - pages Google has indexed AND served in the last 28 days (the honest,
    authoritative "is it indexed" signal)
"""
import datetime
import json
import os
import sys

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
CLIENT = os.path.expanduser("~/.dsh/gsc_client.json")
TOKEN = os.path.expanduser("~/.dsh/gsc_token.json")
LOG = os.path.expanduser("~/logs/gsc_indexing.log")
DOMAIN = "mingjian.cc"


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = "[%s] %s" % (datetime.datetime.now().isoformat(timespec="seconds"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(msg)


def creds_from_client_json():
    with open(CLIENT, encoding="utf-8") as f:
        c = json.load(f)
    web = c.get("web") or c.get("installed") or c
    return {
        "installed": {
            "client_id": web["client_id"],
            "client_secret": web["client_secret"],
            "project_id": c.get("project_id", ""),
            "auth_uri": web.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": web.get("token_uri", "https://oauth2.googleapis.com/token"),
            "redirect_uris": web.get("redirect_uris", ["http://localhost"]),
        }
    }


def auth():
    from google_auth_oauthlib.flow import InstalledAppFlow
    client = creds_from_client_json()
    flow = InstalledAppFlow.from_client_config(client, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    os.makedirs(os.path.dirname(TOKEN), exist_ok=True)
    with open(TOKEN, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    log("token saved to %s" % TOKEN)
    return creds


def service(creds=None):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    if creds is None:
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def pick_site(svc):
    sites = svc.sites().list().execute().get("siteEntry", [])
    urls = [s["siteUrl"] for s in sites]
    log("verified GSC properties: %s" % ", ".join(urls) if urls else "(none)")
    for u in urls:
        if DOMAIN in u:
            return u
    # fall back to the two standard forms, checking which one is verifiable
    for u in ("https://%s/" % DOMAIN, "sc-domain:%s" % DOMAIN):
        if u in urls:
            return u
    return None


def report_sitemaps(svc, site):
    log("## Sitemaps")
    try:
        sms = svc.sitemaps().list(siteUrl=site).execute().get("sitemap", [])
    except Exception as e:
        log("- sitemap query failed: %s" % e)
        sms = []
    if not sms:
        log("- no sitemap entries reported by GSC yet")
        return
    for sm in sms:
        log("- %s  path=%s  lastSubmitted=%s  lastDownloaded=%s  "
            "isPending=%s" % (sm.get("type"), sm.get("path"),
                              sm.get("lastSubmitted"), sm.get("lastDownloaded"),
                              sm.get("isPending")))
        # discovered-url count lives in sitemaps().get() for sitemap-index type;
        # try a lightweight extra call only when it's a normal sitemap
        try:
            detail = svc.sitemaps().get(siteUrl=site, feedpath=sm["path"]).execute()
            if "contents" in detail:
                log("  discovered URLs: %s" % len(detail.get("contents", [])))
        except Exception:
            pass


def report_indexed_pages(svc, site):
    log("## Indexed pages (last 28 days, pages Google has served)")
    end = datetime.date.today()
    start = end - datetime.timedelta(days=27)
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["page"],
        "rowLimit": 100,
        "searchType": "web",
    }
    try:
        res = svc.searchanalytics().query(siteUrl=site, body=body).execute()
    except Exception as e:
        log("- searchanalytics failed: %s" % e)
        res = {}
    rows = res.get("rows", [])
    log("- distinct indexed pages with impressions: %d" % len(rows))
    for r in rows[:15]:
        log("  - %s  (impressions %s, clicks %s)"
            % (r["keys"][0], r.get("impressions", 0), r.get("clicks", 0)))


def main(argv):
    if "--auth" in argv:
        creds = auth()
        svc = service(creds)
    else:
        if not os.path.isfile(TOKEN):
            log("no token yet — run: python3 scripts/gsc_indexing.py --auth")
            return 1
        svc = service()

    site = pick_site(svc)
    if not site:
        log("ERROR: no verified GSC property for %s found under this account" % DOMAIN)
        return 1
    log("using property: %s" % site)
    report_sitemaps(svc, site)
    report_indexed_pages(svc, site)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
