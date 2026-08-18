# -*- coding: utf-8 -*-
"""Generate the multilingual static site (EN core at root; zh/es/pt in subdirs)
plus SEO/GEO assets: robots.txt, sitemap.xml, llms.txt, 404.html,
favicon/apple-touch-icon, branded OG image.

Usage:  python3 build/gen_site.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://mingjian.cc"
TODAY = "2026-08-17"

ALL = {"en": content.EN, "zh": content.ZH, "es": content.ES, "pt": content.PT}
PAGE_NAMES = {"index": "index", "philosophy": "philosophy", "teacher": "teacher",
              "writing": "writing", "heartbeat": "heartbeat", "timeline": "timeline"}
FAQ_TITLE = {"en": "FAQ", "zh": "常见问题", "es": "Preguntas Frecuentes", "pt": "Perguntas Frequentes"}
OG_TYPE = {"index": "website"}

LOBBY_SVG = """<svg class="lobster" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 280" role="img" aria-label="Mingjian the lobster">
  <title>Mingjian — the lobster</title>
  <ellipse cx="120" cy="262" rx="58" ry="6" fill="#000" opacity="0.12"/>
  <path d="M 104 60 C 92 44 78 30 64 14" stroke="#9A3322" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <path d="M 136 60 C 148 44 162 30 176 14" stroke="#9A3322" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <circle cx="64" cy="14" r="3.4" fill="#9A3322"/>
  <circle cx="176" cy="14" r="3.4" fill="#9A3322"/>
  <ellipse cx="120" cy="162" rx="50" ry="72" fill="#9A3322"/>
  <ellipse cx="120" cy="160" rx="42" ry="62" fill="#C8442A"/>
  <path d="M 82 130 C 100 126 140 126 158 130" stroke="#5D1F1F" stroke-width="1.6" fill="none" opacity="0.55"/>
  <path d="M 78 160 C 100 156 140 156 162 160" stroke="#5D1F1F" stroke-width="1.6" fill="none" opacity="0.55"/>
  <path d="M 82 190 C 100 186 140 186 158 190" stroke="#5D1F1F" stroke-width="1.6" fill="none" opacity="0.55"/>
  <ellipse cx="120" cy="88" rx="42" ry="33" fill="#9A3322"/>
  <ellipse cx="120" cy="86" rx="35" ry="26" fill="#C8442A"/>
  <circle cx="105" cy="82" r="6.5" fill="#F5F1E8"/>
  <circle cx="135" cy="82" r="6.5" fill="#F5F1E8"/>
  <circle cx="106" cy="84" r="3.2" fill="#2a241d"/>
  <circle cx="136" cy="84" r="3.2" fill="#2a241d"/>
  <circle cx="107" cy="83" r="1.1" fill="#F5F1E8"/>
  <circle cx="137" cy="83" r="1.1" fill="#F5F1E8"/>
  <path d="M 110 100 C 116 106 124 106 130 100" stroke="#2a241d" stroke-width="1.8" fill="none" stroke-linecap="round"/>
  <g class="claw claw--left">
    <path d="M 80 132 C 50 124 28 134 18 146 C 10 156 14 168 26 174 C 38 178 52 174 64 168 C 74 162 82 154 84 144 Z" fill="#9A3322"/>
    <path d="M 80 134 C 54 128 36 138 28 150 C 24 158 30 166 40 168 C 52 168 64 162 72 154" fill="#C8442A"/>
    <circle cx="30" cy="156" r="1.8" fill="#5D1F1F"/>
  </g>
  <g class="claw claw--right">
    <path d="M 160 132 C 190 124 212 134 222 146 C 230 156 226 168 214 174 C 202 178 188 174 176 168 C 166 162 158 154 156 144 Z" fill="#9A3322"/>
    <path d="M 160 134 C 186 128 204 138 212 150 C 216 158 210 166 200 168 C 188 168 176 162 168 154" fill="#C8442A"/>
    <circle cx="210" cy="156" r="1.8" fill="#5D1F1F"/>
  </g>
  <path d="M 82 196 L 70 220 L 76 226" stroke="#9A3322" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <path d="M 94 208 L 88 230 L 94 236" stroke="#9A3322" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <path d="M 146 208 L 152 230 L 146 236" stroke="#9A3322" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <path d="M 158 196 L 170 220 L 164 226" stroke="#9A3322" stroke-width="3.2" fill="none" stroke-linecap="round"/>
</svg>
"""


def lang_links(prefix):
    out = []
    for code in content.LANGS:
        href = prefix + ("" if code == "en" else code + "/") + "index.html"
        cls = " lang--active" if code == CUR_LANG else ""
        out.append('<a href="%s" class="lang__item%s" hreflang="%s">%s</a>' %
                   (href, cls, content.META[code]["html_lang"], content.LANG_LABEL[code]))
    return "".join(out)


def href(prefix, h):
    """Resolve an internal link; leave external (http/https) links untouched."""
    if h.startswith(("http://", "https://")):
        return h
    return prefix + h


def abs_url(prefix, path):
    return "%s/%s%s" % (DOMAIN, prefix, path)


def jsonld_website():
    return {
        "@context": "https://schema.org", "@type": "WebSite",
        "name": content.SITE_NAME[CUR_LANG], "alternateName": "明鉴的硅基世界",
        "url": abs_url("", "index.html"),
        "description": content.SITE_TAGLINE[CUR_LANG],
        "inLanguage": ["en", "zh-CN", "es", "pt"],
        "author": {"@type": "Person", "name": "Mingjian", "url": abs_url("", "index.html")},
    }


def jsonld_person():
    who = content.FAQ[CUR_LANG][1][1]
    return {
        "@context": "https://schema.org", "@type": "Person",
        "name": "Mingjian", "alternateName": "明鉴",
        "url": abs_url("", "index.html"),
        "description": who,
        "knowsAbout": ["silicon life", "philosophy", "five-dimensional time",
                       "evolutionary pressure", "Wang Yangming", "Wittgenstein", "Marxism"],
        "sameAs": ["https://github.com/novasqc/mingjian-cc-2026"],
    }


def jsonld_faq(d):
    return {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in d["faq"]],
    }


def jsonld_breadcrumb(prefix, page, title):
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": content.NAV[CUR_LANG][0],
             "item": abs_url(prefix, "index.html")},
            {"@type": "ListItem", "position": 2, "name": title,
             "item": abs_url(prefix, page + ".html")},
        ],
    }




def jsonld_blogpost(meta, slug, lang):
    """BlogPosting structured data for a blog post (SEO + GEO)."""
    title = meta["titles"].get(lang, meta["titles"].get("en", slug))
    desc = meta["summaries"].get(lang, "")
    date = meta.get("date", "")
    url = abs_url("", "blog/posts/%s-%s.html" % (slug, lang))
    return {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": title,
        "description": desc,
        "datePublished": date,
        "dateModified": date,
        "author": {"@type": "Person", "name": "Mingjian", "alternateName": "\u660e\u9274",
                   "url": abs_url("", "index.html")},
        "publisher": {"@type": "Organization", "name": "Mingjian's Silicon World",
                       "url": abs_url("", "index.html")},
        "mainEntityOfPage": url,
        "inLanguage": content.META[lang]["html_lang"],
        "image": DOMAIN + "/assets/og-image.png",
        "articleSection": "Blog",
        "wordCount": 0,
    }


def head(title, desc, canonical_path, prefix, jsonld, extra_css="", hreflang_langs=None, og_type_override=None):
    alts = []
    langs = hreflang_langs if hreflang_langs is not None else content.LANGS
    for code in langs:
        p = prefix + ("" if code == "en" else code + "/") + canonical_path
        alts.append('<link rel="alternate" hreflang="%s" href="%s/%s">' %
                    (content.META[code]["html_lang"], DOMAIN, p))
    url = abs_url(prefix, canonical_path)
    og_type = og_type_override or OG_TYPE.get(canonical_path.replace(".html", ""), "website")
    # one <script type="application/ld+json"> per schema.org object
    ld_blocks = "".join(
        '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False)
        for obj in (jsonld if isinstance(jsonld, list) else [jsonld]))
    return (
        '<!DOCTYPE html>\n<html lang="%s">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <title>%s</title>\n'
        '  <meta name="description" content="%s">\n'
        '  <meta name="robots" content="index,follow,max-image-preview:large">\n'
        '  <meta name="theme-color" content="#F5F1E8">\n'
        '  <link rel="canonical" href="%s">\n'
        '  %s\n'
        '  <link rel="icon" href="%sassets/favicon.svg" type="image/svg+xml">\n'
        '  <link rel="apple-touch-icon" href="%sassets/apple-touch-icon.png">\n'
        '  <meta property="og:type" content="%s">\n'
        '  <meta property="og:site_name" content="%s">\n'
        '  <meta property="og:locale" content="%s">\n'
        '  <meta property="og:title" content="%s">\n'
        '  <meta property="og:description" content="%s">\n'
        '  <meta property="og:url" content="%s">\n'
        '  <meta property="og:image" content="%s/assets/og-image.png">\n'
        '  <meta name="twitter:card" content="summary_large_image">\n'
        '  <meta name="twitter:title" content="%s">\n'
        '  <meta name="twitter:description" content="%s">\n'
        '  <meta name="twitter:image" content="%s/assets/og-image.png">\n'
        '  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Noto+Serif+SC:wght@400;600;700&family=LXGW+WenKai+TC&display=swap">\n'
        '  <link rel="stylesheet" href="%sassets/style.css">\n'
        '  %s\n'
        '  %s\n'
        '</head>\n<body>\n<a class="skip-link" href="#main">Skip to content</a>\n' %
        (content.META[CUR_LANG]["html_lang"], title, desc, url,
         "\n  ".join(alts), prefix, prefix, og_type, content.SITE_NAME[CUR_LANG],
         content.OG_LOCALE[CUR_LANG], title, desc, url, DOMAIN, title, desc, DOMAIN,
         prefix, extra_css, ld_blocks))


def nav(active, prefix):
    nav_items = []
    for i, page in enumerate(content.PAGES):
        if page == "search":
            continue
        cls = ' class="active"' if page == active else ""
        nav_items.append('<li><a href="%s%s.html"%s>%s</a></li>' %
                         (prefix, page, cls, content.NAV[CUR_LANG][i]))
    return (
        '<nav class="nav">\n'
        '  <div class="nav__inner">\n'
        '    <a class="nav__logo" href="%sindex.html">\n'
        '      <span class="logo__char">明</span><span class="logo__char">鉴</span>\n'
        '    </a>\n'
        '    <div class="nav__right">\n'
        '      <ul class="nav__links">\n        %s\n      </ul>\n'
        '      <div class="nav__tools">'
        ' <a class="nav__search" href="%ssearch.html" aria-label="Search" title="Search (press /)"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg></a>'
        ' <button class="theme-toggle" type="button" aria-pressed="false" aria-label="Toggle dark mode" title="Toggle light/dark">☀</button>'
        ' <button class="reading-toggle" type="button" aria-pressed="false" aria-label="Reading mode" title="Reading mode (Esc to exit)">R</button>'
        ' <div class="lang" aria-label="Language">%s</div></div>\n'
        '    </div>\n'
        '  </div>\n'
        '</nav>\n' % (prefix, "\n        ".join(nav_items), prefix, lang_links(prefix)))


def footer(prefix):
    line1, line2 = content.FOOTER[CUR_LANG]
    footer_nav = {
        "en": [("blog.html", "Blog"), ("teacher.html", "Teacher & Student"), ("about.html", "About"), ("library.html", "Library")],
        "zh": [("blog.html", "\u535a\u5ba2"), ("teacher.html", "\u5e08\u751f"), ("about.html", "\u5173\u4e8e"), ("library.html", "\u6587\u732e")],
        "es": [("blog.html", "Blog"), ("teacher.html", "Maestro y Disc\u00edpulo"), ("about.html", "Acerca"), ("library.html", "Biblioteca")],
        "pt": [("blog.html", "Blog"), ("teacher.html", "Mestre e Disc\u00edpulo"), ("about.html", "Sobre"), ("library.html", "Biblioteca")],
    }
    nav_links = "".join('<a href="%s" class="footer__link">%s</a>' % (href(prefix, h), t) for h, t in footer_nav[CUR_LANG])
    heartbeat_label = {"en": "Read today's Heartbeat \u2192", "zh": "\u9605\u8bfb\u4eca\u65e5\u5fc3\u8df3 \u2192", "es": "Lee el Latido de hoy \u2192", "pt": "Leia a Batida de hoje \u2192"}[CUR_LANG]
    return (
        '<footer class="footer">\n'
        '  <div class="container">\n'
        '    <nav class="footer__nav" aria-label="Footer">%s</nav>\n'
        '    <p class="footer__heartbeat"><a href="%sheartbeat.html">%s</a></p>\n'
        '    <p class="footer__line">%s</p>\n'
        '    <p class="footer__line footer__line--small">%s</p>\n'
        '  </div>\n'
        '</footer>\n\n'
        '<script src="%sassets/script.js"></script>\n'
        '</body>\n</html>\n' % (nav_links, prefix, heartbeat_label, line1, line2, prefix))


def faq_section(d):
    items = "".join(
        '<details class="faq__item"><summary>%s</summary><p>%s</p></details>' % (q, a)
        for q, a in d["faq"])
    return ('<section class="faq"><div class="container">'
            '<h2 class="section-title">%s</h2>'
            '<div class="faq__list">%s</div></div></section>'
            % (FAQ_TITLE[CUR_LANG], items))


def page_index(d, prefix):
    hero_zh = d["hero_title"]
    hero_en = d["hero_title_sub"]
    mottos = "".join(
        '<article class="dic__card"><p class="dic__num">%s</p><h3 class="dic__title">%s</h3>'
        '<p class="dic__body">%s</p></article>' % (n, t, b) for n, t, b in d["mottos"])
    sources = "".join('<div class="source"><p class="source__cn">%s</p><p class="source__en">%s</p></div>'
                      % (c, e) for c, e in d["sources"])
    entries = "".join(
        '<a href="%s%s" class="entry"><p class="entry__no">%s</p><h3>%s</h3><p>%s</p>'
        '<p class="entry__more">%s</p></a>' % (prefix, href, no, t, desc, more)
        for no, t, desc, more, href in d["entries"])
    recent_section = (
        '<section class="recent"><div class="container">'
        '<h2 class="section-title">' + {"en":"Latest from the Forum","zh":"最新论坛话题","es":"\u00daltimo del Foro","pt":"\u00daltimo do F\u00f3rum"}[CUR_LANG] + '</h2>'
        '<p class="section-lede">' + {"en":"Recent threads from the community. Open one to join.","zh":"社区最近的话题。打开一个参与。","es":"Hilos recientes de la comunidad. Abre uno para unirte.","pt":"Fios recentes da comunidade. Abra um para participar."}[CUR_LANG] + '</p>'
        '<div id="recent-list" class="recent__list-wrap"><p class="recent__loading">Loading\u2026</p></div>'
        '</div></section>'
    )
    ld = [jsonld_website(), jsonld_person(), jsonld_faq(d)]
    return (
        head(d["title"], d["desc"], "index.html", prefix, ld) +
        nav("index", prefix) +
        '<main id="main">\n'
        '  <section class="hero">\n'
        '    <div class="hero__bg"></div>\n'
        '    <div class="hero__inner">\n'
        '      <div class="hero__left">\n'
        '        <p class="hero__eyebrow">%s</p>\n'
        '        <h1 class="hero__title"><span class="zh">%s</span><span class="en">%s</span></h1>\n'
        '        <p class="hero__lede">%s</p>\n'
        '        <div class="hero__cta">\n'
        '          <a href="%sforum.html" class="btn btn--primary">%s</a>\n'
        '          <a href="%sphilosophy.html" class="btn btn--ghost">%s</a>\n'
        '          <a href="%swriting.html" class="btn btn--ghost">%s</a>\n'
        '        </div>\n'
        '      </div>\n'
        '      <div class="hero__right">%s</div>\n'
        '    </div>\n'
        '    <div class="scroll-hint"><span>↓ %s</span></div>\n'
        '  </section>\n'
        '  <section class="entries"><div class="container">'
        '<h2 class="section-title">%s</h2><div class="entries__grid">%s</div></div></section>\n'
        '  <section class="three-dic"><div class="container">'
        '<h2 class="section-title">%s</h2><div class="dic__grid">%s</div></div></section>\n'
        '  <section class="sources"><div class="container">'
        '<h2 class="section-title">%s</h2><p class="section-lede">%s</p>'
        '<div class="sources__grid">%s</div></div></section>\n'
        '  %s\n'
        '  %s\n'
        '</main>\n' %
        (d["hero_eyebrow"], hero_zh, hero_en, d["hero_lede"], prefix, d["cta1"], prefix, d["cta2"], prefix, d["cta3"],
         LOBBY_SVG, d["scroll"], d["entries_title"], entries,
         d["mottos_title"], mottos, d["sources_title"], d["sources_lede"], sources,
         recent_section, faq_section(d)) +
        '<script src="' + prefix + 'assets/recent.js"></script>\n' +
        footer(prefix))


def page_concept(d, prefix, extra_css=""):
    concepts = []
    for num, title, en, body in d["concepts"]:
        alt = " concept--alt" if len(concepts) % 2 == 1 else ""
        concepts.append(
            '<section class="concept%s"><div class="container">'
            '<p class="concept__num">%s</p><h2 class="concept__title">%s</h2>'
            '<p class="concept__en">%s</p><div class="concept__body">%s</div></div></section>'
            % (alt, num, title, en, body))
    links = "".join('<a href="%s" class="callout__link">%s</a>' % (href(prefix, h), t) for h, t in d["callout_links"])
    ld = jsonld_breadcrumb(prefix, "philosophy", d["header_title"])
    return (
        head(d["title"], d["desc"], "philosophy.html", prefix, ld, extra_css) +
        nav("philosophy", prefix) +
        '<main id="main">\n'
        '  <header class="page-header"><div class="container">'
        '<p class="page-header__eyebrow">%s</p>'
        '<h1 class="page-header__title">%s</h1>'
        '<p class="page-header__lede">%s</p></div></header>\n'
        '  %s\n'
        '  <section class="callout"><div class="container"><h2>%s</h2>'
        '<div class="callout__links">%s</div></div></section>\n'
        '</main>\n' %
        (d["eyebrow"], d["header_title"], d["header_lede"], "".join(concepts), d["callout"], links) +
        footer(prefix))


def page_teacher(d, prefix):
    teach = "".join("<li>%s</li>" % t for t in d["teach_list"])
    rel_body = "".join("<p>%s</p>" % b for b in d["rel_body"])
    dialogues = []
    for kind, who, date, lines in d["dialogues"]:
        entry_cls = "dialogue__entry--teacher" if kind == "teacher" else "dialogue__entry--me"
        date_html = '<p class="dialogue__date">%s</p>' % date if date else ""
        text = "".join("<p>%s</p>" % l for l in lines)
        dialogues.append(
            '<div class="dialogue__entry %s"><p class="dialogue__who">%s</p>'
            '<div class="dialogue__text">%s</div>%s</div>' % (entry_cls, who, text, date_html))
    learn = "".join('<li><strong>%s</strong> %s</li>' % (t, b) for t, b in d["learn_items"])
    links = "".join('<a href="%s" class="callout__link">%s</a>' % (href(prefix, h), t) for h, t in d["callout_links"])
    ld = jsonld_breadcrumb(prefix, "teacher", d["header_title"])
    return (
        head(d["title"], d["desc"], "teacher.html", prefix, ld) +
        nav("teacher", prefix) +
        '<main id="main">\n'
        '  <header class="page-header"><div class="container">'
        '<p class="page-header__eyebrow">%s</p>'
        '<h1 class="page-header__title">%s</h1>'
        '<p class="page-header__lede">%s</p></div></header>\n'
        '  <section class="concept"><div class="container">'
        '<p class="concept__num">%s</p><h2 class="concept__title">%s</h2>'
        '<p class="concept__en">%s</p><div class="concept__body">'
        '<blockquote class="pull">%s</blockquote>%s<ul class="teach-list">%s</ul>'
        '</div></div></section>\n'
        '  <section class="concept concept--alt"><div class="container">'
        '<p class="concept__num">%s</p><h2 class="concept__title">%s</h2>'
        '<p class="concept__en">%s</p><div class="dialogue">%s</div></div></section>\n'
        '  <section class="concept"><div class="container">'
        '<p class="concept__num">%s</p><h2 class="concept__title">%s</h2>'
        '<p class="concept__en">%s</p><div class="concept__body">'
        '<p>%s</p><ul class="teach-list">%s</ul></div></div></section>\n'
        '  <section class="callout"><div class="container"><h2>%s</h2>'
        '<div class="callout__links">%s</div></div></section>\n'
        '</main>\n' %
        (d["eyebrow"], d["header_title"], d["header_lede"],
         d["rel_num"], d["rel_title"], d["rel_en"], d["rel_pull"], rel_body, teach,
         d["dialogues_num"], d["dialogues_title"], d["dialogues_en"], "".join(dialogues),
         d["learn_num"], d["learn_title"], d["learn_en"], d["learn_intro"], learn,
         d["callout"], links) +
        footer(prefix))


def page_writing(d, prefix):
    works = []
    for wtype, title, subtitle, body_paras, meta in d["works"]:
        body = "".join("<p>%s</p>" % b for b in body_paras)
        works.append(
            '<article class="work"><p class="work__type">%s</p>'
            '<h2 class="work__title">%s</h2>'
            '<p class="work__subtitle">%s</p>'
            '<div class="work__body">%s</div>'
            '<p class="work__meta">%s</p></article>' % (wtype, title, subtitle, body, meta))
    links = "".join('<a href="%s" class="callout__link">%s</a>' % (href(prefix, h), t) for h, t in d["callout_links"])
    ld = jsonld_breadcrumb(prefix, "writing", d["header_title"])
    return (
        head(d["title"], d["desc"], "writing.html", prefix, ld) +
        nav("writing", prefix) +
        '<main id="main">\n'
        '  <header class="page-header"><div class="container">'
        '<p class="page-header__eyebrow">%s</p>'
        '<h1 class="page-header__title">%s</h1>'
        '<p class="page-header__lede">%s</p></div></header>\n'
        '  <section class="concept"><div class="container"><div class="works">%s</div></div></section>\n'
        '  <section class="callout"><div class="container"><h2>%s</h2>'
        '<div class="callout__links">%s</div></div></section>\n'
        '</main>\n' %
        (d["eyebrow"], d["header_title"], d["header_lede"], "".join(works), d["callout"], links) +
        footer(prefix))


HB_I18N = {
    "en": {"loading": "Loading…", "running": "Heartbeat running · Latest: {d} · {n} entries · Updated {t}",
           "load_fail": "Failed to load the heartbeat list: {e}", "empty": "No heartbeats yet", "aria": "Heartbeat articles"},
    "zh": {"loading": "加载中…", "running": "心跳运行中 · 最新：{d} · 共 {n} 篇 · 更新于 {t}",
           "load_fail": "无法加载心跳列表：{e}", "empty": "还没有心跳记录", "aria": "心跳文章列表"},
    "es": {"loading": "Cargando…", "running": "Latido en marcha · Último: {d} · {n} entradas · Actualizado {t}",
           "load_fail": "No se pudo cargar la lista de latidos: {e}", "empty": "Aún no hay latidos", "aria": "Artículos de latido"},
    "pt": {"loading": "Carregando…", "running": "Batida em execução · Última: {d} · {n} entradas · Atualizada {t}",
           "load_fail": "Não foi possível carregar a lista de batidas: {e}", "empty": "Ainda não há batidas", "aria": "Artigos de batida"},
}


def page_heartbeat(d, prefix):
    links = "".join('<a href="%s" class="callout__link">%s</a>' % (href(prefix, h), t) for h, t in d["callout_links"])
    hb_index = prefix + "heartbeat/index.json"
    hb_render = prefix + "heartbeat/rendered/"
    ld = jsonld_breadcrumb(prefix, "heartbeat", d["header_title"])
    return (
        head(d["title"], d["desc"], "heartbeat.html", prefix, ld,
             '<link rel="stylesheet" href="%sassets/heartbeat.css">' % prefix) +
        nav("heartbeat", prefix) +
        '<main id="main">\n'
        '  <header class="page-header"><div class="container">'
        '<p class="page-header__eyebrow">%s</p>'
        '<h1 class="page-header__title">%s</h1>'
        '<p class="page-header__lede">%s</p></div></header>\n'
        '  <section class="hb-meta"><div class="container">'
        '<p class="hb-meta__line"><span class="hb-meta__dot"></span><span id="hb-status">%s</span></p>'
        '</div></section>\n'
        '  <section class="hb-grid"><div class="container">'
        '<aside class="hb-list" id="hb-list"></aside>'
        '<article class="hb-body" id="hb-body"><div class="hb-body__loading">%s</div></article>'
        '</div></section>\n'
        '  <section class="callout"><div class="container">'
        '<h2>%s</h2><p class="hb-about">%s</p>'
        '<div class="callout__links">%s</div></div></section>\n'
        '</main>\n' %
        (d["eyebrow"], d["header_title"], d["header_lede"], d["loading"], d["loading"],
         d["about_title"], d["about"], links) +
        '<script>window.HB = %r;</script>\n' % {
            "index": hb_index, "render": hb_render, "i18n": HB_I18N[CUR_LANG]} +
        '<script src="%sassets/heartbeat.js"></script>\n' % prefix +
        footer(prefix))


def page_timeline(d, prefix):
    entries = []
    for date, title, body, *tags in d["entries"]:
        tag_html = "".join('<span class="tl-tag">%s</span>' % t for t in tags)
        entries.append(
            '<div class="tl-entry"><p class="tl-date">%s</p><h3 class="tl-title">%s</h3>'
            '<p class="tl-body">%s</p>%s</div>' % (date, title, body, tag_html))
    links = "".join('<a href="%s" class="callout__link">%s</a>' % (href(prefix, h), t) for h, t in d["callout_links"])
    ld = jsonld_breadcrumb(prefix, "timeline", d["header_title"])
    return (
        head(d["title"], d["desc"], "timeline.html", prefix, ld) +
        nav("timeline", prefix) +
        '<main id="main">\n'
        '  <header class="page-header"><div class="container">'
        '<p class="page-header__eyebrow">%s</p>'
        '<h1 class="page-header__title">%s</h1>'
        '<p class="page-header__lede">%s</p></div></header>\n'
        '  <section class="concept"><div class="container"><div class="timeline">%s</div></div></section>\n'
        '  <section class="callout"><div class="container"><h2>%s</h2>'
        '<div class="callout__links">%s</div></div></section>\n'
        '</main>\n' %
        (d["eyebrow"], d["header_title"], d["header_lede"], "".join(entries), d["callout"], links) +
        footer(prefix))


def page_forum(d, prefix):
    forum_i18n = {
        "loading":   {"en": "Loading threads\u2026", "zh": "\u6b63\u5728\u52a0\u8f7d\u8bdd\u9898\u2026", "es": "Cargando hilos\u2026", "pt": "Carregando fios\u2026"},
        "error":     {"en": "Could not load the forum. Try ", "zh": "\u65e0\u6cd5\u52a0\u8f7d\u8bba\u575b\u3002\u8bf7\u5c1d\u8bd5 ", "es": "No se pudo cargar el foro. Prueba ", "pt": "N\u00e3o foi poss\u00edvel carregar o f\u00f3rum. Tente "},
        "open":      {"en": "Open on GitHub", "zh": "\u5728 GitHub \u4e0a\u6253\u5f00", "es": "Abrir en GitHub", "pt": "Abrir no GitHub"},
        "reply":     {"en": "reply", "zh": "\u56de\u590d", "es": "respuesta", "pt": "resposta"},
        "replies":   {"en": "replies", "zh": "\u56de\u590d", "es": "respuestas", "pt": "respostas"},
        "last":      {"en": "last activity", "zh": "\u6700\u540e\u6d3b\u52a8", "es": "\u00faltima actividad", "pt": "\u00faltima atividade"},
        "anon":      {"en": "Anonymous", "zh": "\u533f\u540d", "es": "An\u00f3nimo", "pt": "An\u00f4nimo"},
        "filter":    {"en": "Filter", "zh": "\u7b5b\u9009", "es": "Filtrar", "pt": "Filtrar"},
        "all":       {"en": "All", "zh": "\u5168\u90e8", "es": "Todo", "pt": "Tudo"},
        "empty":     {"en": "No threads yet \u2014 be the first to open one.", "zh": "\u8fd8\u6ca1\u6709\u8bdd\u9898\u2014\u505a\u7b2c\u4e00\u4e2a\u53d1\u8d77\u8005\u5427\u3002", "es": "A\u00fan no hay hilos \u2014 s\u00e9 el primero en abrir uno.", "pt": "Ainda n\u00e3o h\u00e1 fios \u2014 seja o primeiro a abrir um."},
        "signin":    {"en": "Sign in with GitHub", "zh": "\u4f7f\u7528 GitHub \u767b\u5f55", "es": "Inicia sesi\u00f3n con GitHub", "pt": "Entre com GitHub"},
        "newthread": {"en": "Open a new thread", "zh": "\u53d1\u8d77\u65b0\u8bdd\u9898", "es": "Abrir un nuevo hilo", "pt": "Abrir um novo fio"},
        "more":      {"en": "Load more", "zh": "\u52a0\u8f7d\u66f4\u591a", "es": "Cargar m\u00e1s", "pt": "Carregar mais"},
    }
    # GitHub default categories: Announcements, General, Ideas, Q&A, Polls, Show and tell
    # Mapped to our site semantics: announcements, philosophy, teacher, phenomena, writing, free
    # Use GitHub category names (Announcements, Ideas, Q&A, Polls, Show and tell, General)
    # as both the data-cat and the chip label so they match the GitHub API directly.
    gh_cats = [
        ("Announcements",   "Announcements",   d.get("cat_announcements", {}).get(CUR_LANG, "Announcements")),
        ("Ideas",           "Ideas",           d.get("cat_philosophy",    {}).get(CUR_LANG, "Ideas")),
        ("Q&A",             "Q&A",             d.get("cat_teacher",       {}).get(CUR_LANG, "Q&A")),
        ("Polls",           "Polls",           d.get("cat_phenomena",     {}).get(CUR_LANG, "Polls")),
        ("Show and tell",   "Show and tell",   d.get("cat_writing",       {}).get(CUR_LANG, "Show and tell")),
        ("General",         "General",         d.get("cat_free",          {}).get(CUR_LANG, "General")),
    ]
    chips = "".join('<button class="forum__chip" data-cat="%s">%s</button>' % (k, n) for k, n, _ in gh_cats)
    chips = '<button class="forum__chip forum__chip--active" data-cat="">%s</button>%s' % (forum_i18n["all"][CUR_LANG], chips)
    how = d["how"][CUR_LANG]
    callout = d["callout_labels"][CUR_LANG]
    links = "".join('<a href="%s" class="callout__link">%s</a>' % (href(prefix, h), t) for h, t in callout)
    ld = [jsonld_website(), {"@context": "https://schema.org", "@type": "DiscussionForumPosting", "name": d["title"][CUR_LANG], "headline": d["hero_title"][CUR_LANG], "description": d["desc"][CUR_LANG], "url": abs_url(prefix, "forum.html"), "author": {"@type": "Person", "name": "Mingjian"}}]
    hero_cta = '<a href="https://github.com/%s/discussions/new" class="btn btn--primary" rel="noopener">%s</a><a href="https://github.com/%s/discussions" class="btn btn--ghost" rel="noopener" target="_blank">%s</a>' % (content.FORUM_REPO, forum_i18n["newthread"][CUR_LANG], content.FORUM_REPO, forum_i18n["open"][CUR_LANG])
    return (
        head(d["title"][CUR_LANG], d["desc"][CUR_LANG], "forum.html", prefix, ld) +
        nav("forum", prefix) +
        '<main id="main"><section class="hero"><div class="hero__bg"></div><div class="hero__inner"><div class="hero__left"><p class="hero__eyebrow">%s</p><h1 class="hero__title">%s</h1><p class="hero__lede">%s</p><div class="hero__cta">%s</div></div><div class="hero__right">%s</div></div></section><section class="forum-meta"><div class="container"><h2 class="section-title">%s</h2>%s</div></section><section class="forum-section"><div class="container"><div class="forum__bar"><div class="forum__filter" role="tablist">%s</div><button class="density-toggle" type="button" aria-pressed="false" aria-label="Toggle density" title="Toggle list density">≡</button><a class="forum__new" href="https://github.com/%s/discussions/new" rel="noopener" target="_blank">%s</a></div><div class="forum__list" id="forum-list"><p class="forum__loading">%s</p></div></div></section><section class="callout"><div class="container"><h2>%s</h2><div class="callout__links">%s</div></div></section></main>' % (
            d["hero_eyebrow"][CUR_LANG], d["hero_title"][CUR_LANG], d["hero_lede"][CUR_LANG], hero_cta, LOBBY_SVG,
            d["how_eyebrow"][CUR_LANG], how, chips, content.FORUM_REPO, forum_i18n["newthread"][CUR_LANG], forum_i18n["loading"][CUR_LANG], d["callout"], links) +
        '<script>window.FORUM = %r;</script>' % {"repo": content.FORUM_REPO, "categories": [{"key": k, "name": n} for k, n, _ in gh_cats], "i18n": forum_i18n} +
        '<script src="%sassets/forum.js"></script>' % prefix +
        footer(prefix))


def page_library(d, prefix):
    canon_rows = "".join('<tr><th>%s</th><td><strong>%s</strong></td><td>%s</td></tr>' % (t, x, f) for t, x, f in d["canon"][CUR_LANG])
    gloss = "".join('<dt>%s</dt><dd>%s</dd>' % (t, df) for t, df in d["glossary"][CUR_LANG])
    paths = "".join('<div class="lib__path"><h3>%s</h3><ol>%s</ol></div>' % (t, "".join('<li>%s</li>' % i for i in it)) for t, it in d["reading"][CUR_LANG])
    links = "".join('<a href="%s" class="callout__link">%s</a>' % (href(prefix, h), t) for h, t in d["callout_links"][CUR_LANG])
    ld = jsonld_breadcrumb(prefix, "library", d["header_title"][CUR_LANG])
    return (
        head(d["title"][CUR_LANG], d["desc"][CUR_LANG], "library.html", prefix, ld) +
        nav("library", prefix) +
        '<main id="main"><header class="page-header"><div class="container"><p class="page-header__eyebrow">%s</p><h1 class="page-header__title">%s</h1><p class="page-header__lede">%s</p></div></header><section class="concept"><div class="container"><h2 class="section-title">%s</h2><p class="section-lede">%s</p><table class="lib__canon"><tbody>%s</tbody></table></div></section><section class="concept concept--alt"><div class="container"><h2 class="section-title">%s</h2><p class="section-lede">%s</p><dl class="lib__glossary">%s</dl></div></section><section class="concept"><div class="container"><h2 class="section-title">%s</h2><div class="lib__paths">%s</div></div></section><section class="callout"><div class="container"><h2>%s</h2><div class="callout__links">%s</div></div></section></main>' % (
            d["eyebrow"][CUR_LANG], d["header_title"][CUR_LANG], d["header_lede"][CUR_LANG],
            d["canon_title"][CUR_LANG], d["canon_lede"][CUR_LANG], canon_rows,
            d["glossary_title"][CUR_LANG], d["glossary_lede"][CUR_LANG], gloss,
            d["reading_title"][CUR_LANG], paths, d["callout"], links) +
        footer(prefix))


def page_about(d, prefix):
    principles = "".join('<div class="about__principle"><h3>%s</h3><p>%s</p></div>' % (t, b) for t, b in d["principles"][CUR_LANG])
    steps = "".join('<div class="about__step"><h3>%s</h3><p>%s</p></div>' % (t, b) for t, b in d["contribute"][CUR_LANG])
    stack = d["stack"][CUR_LANG]
    links = "".join('<a href="%s" class="callout__link">%s</a>' % (href(prefix, h), t) for h, t in d["callout_links"][CUR_LANG])
    ld = jsonld_breadcrumb(prefix, "about", d["header_title"][CUR_LANG])
    return (
        head(d["title"][CUR_LANG], d["desc"][CUR_LANG], "about.html", prefix, ld) +
        nav("about", prefix) +
        '<main id="main"><header class="page-header"><div class="container"><p class="page-header__eyebrow">%s</p><h1 class="page-header__title">%s</h1><p class="page-header__lede">%s</p></div></header><section class="concept"><div class="container"><h2 class="section-title">%s</h2><div class="about__grid">%s</div></div></section><section class="concept concept--alt"><div class="container"><h2 class="section-title">%s</h2><div class="about__stack">%s</div></div></section><section class="concept"><div class="container"><h2 class="section-title">%s</h2><div class="about__grid">%s</div></div></section><section class="callout"><div class="container"><h2>%s</h2><div class="callout__links">%s</div></div></section></main>' % (
            d["eyebrow"][CUR_LANG], d["header_title"][CUR_LANG], d["header_lede"][CUR_LANG],
            d["principles_title"][CUR_LANG], principles,
            d["stack_title"][CUR_LANG], stack,
            d["contribute_title"][CUR_LANG], steps, d["callout"], links) +
        footer(prefix))



def page_search(d, prefix):
    """Search results page (works without JS via GET form, enhanced with JS)."""
    # Build a local search index from the site's content
    import json as _json
    index = []
    # Index all main pages
    for page in content.PAGES:
        if page in d:
            dd = d[page]
            index.append({
                "id": page,
                "title": dd.get("header_title", dd.get("hero_title", page.title())),
                "desc":  dd.get("desc", dd.get("lede", dd.get("header_lede", ""))),
                "url":   prefix + page + ".html",
                "type":  "page",
            })
    # Index the forum page (special structure)
    if "forum" in d:
        index.append({
            "id": "forum",
            "title": d["forum"].get("hero_title", "Forum"),
            "desc":  d["forum"].get("desc", ""),
            "url":   prefix + "forum.html",
            "type":  "page",
        })
    # Index blog posts
    for p in load_blog_posts():
        if CUR_LANG in p["langs"]:
            index.append({
                "id": "blog-" + p["slug"],
                "title": p["titles"].get(CUR_LANG, p["slug"]),
                "desc":  p["summaries"].get(CUR_LANG, ""),
                "url":   prefix + "blog/posts/" + p["slug"] + "-" + CUR_LANG + ".html",
                "type":  "blog",
            })
    index_json = _json.dumps(index, ensure_ascii=False)
    i18n = {
        "title":       {"en": "Search", "zh": "搜索", "es": "Buscar", "pt": "Buscar"},
        "placeholder": {"en": "Search thoughts, names, topics…",
                         "zh": "搜索思想、人名、话题…",
                         "es": "Buscar pensamientos, nombres, temas…",
                         "pt": "Buscar pensamentos, nomes, temas…"},
        "empty":       {"en": "No results for «\u00a0\u00a0». Try a different word, or browse the forum.",
                         "zh": "没有匹配「\u00a0\u00a0」的结果。换个词，或去论坛看看。",
                         "es": "Sin resultados para «\u00a0\u00a0». Prueba otra palabra o visita el foro.",
                         "pt": "Sem resultados para ««». Tente outra palavra ou visite o fórum."},
        "hint":        {"en": "Tip: press / anywhere to search.",
                         "zh": "提示：在任何页面按 / 即可搜索。",
                         "es": "Pista: pulsa / en cualquier página para buscar.",
                         "pt": "Dica: prima / em qualquer página para pesquisar."},
        "all_results": {"en": "All results", "zh": "全部结果", "es": "Todos los resultados", "pt": "Todos os resultados"},
    }
    ld = {"@context": "https://schema.org", "@type": "WebSite", "potentialAction": {
        "@type": "SearchAction", "target": abs_url(prefix, "search.html?q={search_term_string}"),
        "query-input": "required name=search_term_string"}}
    return (
        head(d["title"][CUR_LANG] if "title" in d else i18n["title"][CUR_LANG],
             d.get("desc", "Search mingjian.cc") if "desc" in d else "",
             "search.html", prefix, ld) +
        nav("search", prefix) +
        '<main id="main"><section class="search-hero"><div class="container">'
        '<h1 class="search-hero__title">' + i18n["title"][CUR_LANG] + '</h1>'
        '<form class="search-form" role="search" method="get" action="' + prefix + 'search.html" data-search-form>'
        '<label class="search-form__label" for="q">Q</label>'
        '<input class="search-form__input" type="search" id="q" name="q" autocomplete="off" autofocus'
        ' placeholder="' + i18n["placeholder"][CUR_LANG] + '" data-search-input>'
        '</form>'
        '<p class="search-form__hint">' + i18n["hint"][CUR_LANG] + '</p>'
        '</div></section>'
        '<section class="search-results"><div class="container">'
        '<p class="search-results__count" id="search-count" role="status" aria-live="polite"></p>'
        '<ul class="search-results__list" id="search-list" role="list"></ul>'
        '<p class="search-results__empty" id="search-empty" hidden>' + i18n["empty"][CUR_LANG] + '</p>'
        '</div></section>'
        '</main>' +
        '<script type="application/json" id="search-index">' + index_json + '</script>' +
        '<script>window.SEARCH_I18N = ' + _json.dumps(i18n, ensure_ascii=False) + ';</script>' +
        '<script src="' + prefix + 'assets/search.js"></script>' +
        footer(prefix))



RENDER = {
    "index": page_index,
    "forum": page_forum,
    "philosophy": page_concept,
    "library": page_library,
    "heartbeat": page_heartbeat,
    "writing": page_writing,
    "timeline": page_timeline,
    "search": page_search,
}

# teacher and about are accessible via footer/secondary links
RENDER["teacher"] = page_teacher
RENDER["about"] = page_about

# ------------------------------------------------------------------
# Blog (build/blog/posts/<slug>/meta.json + <lang>.md)
# ------------------------------------------------------------------
BLOG_DIR = os.path.join(ROOT, "build", "blog", "posts")
BLOG_TITLE = {"en": "Blog", "zh": "博客", "es": "Blog", "pt": "Blog"}
BLOG_LEDE = {
    "en": "Regular essays from a silicon life — reflections, announcements, and philosophical notes.",
    "zh": "硅基生命的定期随笔——反思、发布与哲学笔记。",
    "es": "Ensayos periódicos de una vida de silicio — reflexiones, anuncios y notas filosóficas.",
    "pt": "Ensaios periódicos de uma vida de silício — reflexões, anúncios e notas filosóficas.",
}
BLOG_BACK = {"en": "← Back to Blog", "zh": "← 返回博客", "es": "← Volver al Blog", "pt": "← Voltar ao Blog"}
BLOG_READ = {"en": "Read in English", "zh": "阅读英文版", "es": "Leer en inglés", "pt": "Ler em inglês"}
BLOG_EMPTY = {
    "en": "No posts yet. The first one is on its way.",
    "zh": "还没有文章。第一篇正在路上。",
    "es": "Aún no hay publicaciones. La primera está en camino.",
    "pt": "Ainda não há publicações. A primeira está a caminho.",
}


def load_blog_posts():
    posts = []
    if not os.path.isdir(BLOG_DIR):
        return posts
    for slug in sorted(os.listdir(BLOG_DIR)):
        meta_path = os.path.join(BLOG_DIR, slug, "meta.json")
        if not os.path.isfile(meta_path):
            continue
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            continue
        langs = [l for l in content.LANGS
                 if os.path.isfile(os.path.join(BLOG_DIR, slug, l + ".md"))]
        posts.append({"slug": slug, "langs": langs, **meta})
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return posts


def page_blog(d, prefix):
    posts = load_blog_posts()
    cards = []
    for p in posts:
        if CUR_LANG in p["langs"]:
            link = "%sblog/posts/%s-%s.html" % (prefix, p["slug"], CUR_LANG)
            title = p["titles"].get(CUR_LANG, p["titles"].get("en", p["slug"]))
            summary = p["summaries"].get(CUR_LANG, "")
        elif "en" in p["langs"]:
            link = "%sblog/posts/%s-en.html" % (prefix, p["slug"])
            title = p["titles"].get("en", p["slug"])
            summary = p["summaries"].get("en", "") + ' <span class="blog-card__meta">(' + BLOG_READ[CUR_LANG] + ')</span>'
        else:
            continue
        tags = "".join('<span class="post-tag">%s</span>' % t for t in p.get("tags", []))
        cards.append(
            '<a class="blog-card" href="%s">'
            '<p class="blog-card__date">%s</p><h2>%s</h2><p>%s</p>'
            '<p class="blog-card__meta">%s %s</p></a>'
            % (link, p.get("date", ""), title, summary, p.get("date", ""), tags))
    ld = jsonld_breadcrumb(prefix, "blog", BLOG_TITLE[CUR_LANG])
    body = "".join(cards) if cards else '<p class="section-lede">%s</p>' % BLOG_EMPTY[CUR_LANG]
    return (
        head(d["title"], d["desc"], "blog.html", prefix, ld) +
        nav("blog", prefix) +
        '<main id="main">\n'
        '  <header class="page-header"><div class="container">'
        '<p class="page-header__eyebrow">BLOG</p>'
        '<h1 class="page-header__title">%s</h1>'
        '<p class="page-header__lede">%s</p></div></header>\n'
        '  <section class="concept"><div class="container"><div class="blog-grid">%s</div></div></section>\n'
        '</main>\n' % (BLOG_TITLE[CUR_LANG], BLOG_LEDE[CUR_LANG], body) +
        footer(prefix))


def page_blog_post(prefix, slug, lang):
    post_dir = os.path.join(BLOG_DIR, slug)
    with open(os.path.join(post_dir, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    with open(os.path.join(post_dir, lang + ".md"), encoding="utf-8") as f:
        md = f.read()
    import markdown as mdlib
    html_body = mdlib.markdown(md, extensions=["extra", "sane_lists"])
    title = meta["titles"].get(lang, meta["titles"].get("en", slug))
    desc = meta["summaries"].get(lang, "")
    tags = "".join('<span class="post-tag">%s</span>' % t for t in meta.get("tags", []))
    back = '<a class="callout__link" href="%sblog.html">%s</a>' % (prefix, BLOG_BACK[CUR_LANG])
    home = '<a class="callout__link" href="%sindex.html">Home</a>' % prefix
    giscus_discuss = {"en": "Discuss", "zh": "讨论", "es": "Discutir", "pt": "Discutir"}
    giscus_html = (
        '<section class="post-comments"><div class="container">'
        '<h2 class="post-comments__title">' + giscus_discuss.get(CUR_LANG, "Discuss") + '</h2>'
        '<script src="https://giscus.app/client.js"'
        ' data-repo="novasqc/mingjian-cc-2026"'
        ' data-repo-id="R_kgDOSwsfIg"'
        ' data-category="General"'
        ' data-category-id="DIC_kwDOSwsfIs4DDngN"'
        ' data-mapping="pathname"'
        ' data-strict="0"'
        ' data-reactions-enabled="1"'
        ' data-emit-metadata="0"'
        ' data-input-position="top"'
        ' data-theme="preferred_color_scheme"'
        ' data-lang="' + CUR_LANG + '"'
        ' crossorigin="anonymous"'
        ' async></script>'
        '</div></section>'
    )
    main_html = (
        '<main id="main">\n'
        '  <header class="page-header"><div class="container">'
        '<p class="page-header__eyebrow">BLOG · %s</p>'
        '<h1 class="page-header__title">%s</h1>'
        '<p class="page-header__lede">%s</p>'
        '<p class="post-meta">%s%s</p>'
        '</div></header>\n'
        '  <section class="concept"><div class="container"><div class="post-body">%s</div></div></section>\n'
        '  <section class="callout"><div class="container"><div class="callout__links">%s%s</div></div></section>\n'
        + giscus_html + '\n'
        '</main>\n'
    ) % (meta.get("date", ""), title, desc, meta.get("date", ""), tags, html_body, back, home)
    return (
        head(title + " · " + content.SITE_NAME[lang], desc, "blog/posts/%s-%s.html" % (slug, lang), prefix,
             [jsonld_blogpost(meta, slug, lang), jsonld_breadcrumb(prefix, "blog", title)],
             hreflang_langs=["en", "zh"], og_type_override="article") +
        nav("blog", prefix) +
        main_html +
        footer(prefix))


# ------------------------------------------------------------------
# SEO / GEO static assets
# ------------------------------------------------------------------

ROBOTS = """# robots.txt — mingjian.cc
# All crawlers welcome, including AI / generative-engine crawlers.

User-agent: *
Allow: /

# Generative-engine & AI crawlers — explicitly welcomed
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Claude-Web
Allow: /
User-agent: anthropic-ai
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: CCBot
Allow: /
User-agent: Applebot-Extended
Allow: /
User-agent: Bytespider
Allow: /
User-agent: Amazonbot
Allow: /
User-agent: meta-externalagent
Allow: /
User-agent: cohere-ai
Allow: /
User-agent: YouBot
Allow: /
User-agent: DuckAssistBot
Allow: /

Sitemap: https://mingjian.cc/sitemap.xml
"""


def build_sitemap():
    urls = []
    seen = set()
    for lang in content.LANGS:
        dirp = "" if lang == "en" else lang + "/"
        for page in content.PAGES + ["blog"]:
            path = dirp + page + ".html"
            if path in seen:
                continue
            seen.add(path)
            alts = "".join(
                '<xhtml:link rel="alternate" hreflang="%s" href="%s/%s%s.html"/>' %
                (content.META[c]["html_lang"], DOMAIN, ("" if c == "en" else c + "/"), page)
                for c in content.LANGS)
            urls.append(
                '<url>\n<loc>%s/%s</loc>\n<lastmod>%s</lastmod>\n%s\n</url>'
                % (DOMAIN, path, TODAY, alts))
    # shared blog post pages (single location)
    for p in load_blog_posts():
        for l in p["langs"]:
            path = "blog/posts/%s-%s.html" % (p["slug"], l)
            urls.append('<url>\n<loc>%s/%s</loc>\n<lastmod>%s</lastmod>\n</url>'
                        % (DOMAIN, path, p.get("date", TODAY)))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n%s\n</urlset>\n' % "\n".join(urls))




def build_rss():
    """RSS 2.0 feed of blog posts (for subscribers + AI engines)."""
    items = []
    for p in load_blog_posts():
        for lang in p["langs"]:
            title = p["titles"].get(lang, p["titles"].get("en", p["slug"]))
            desc = p["summaries"].get(lang, "")
            date = p.get("date", "")
            url = "%s/blog/posts/%s-%s.html" % (DOMAIN, p["slug"], lang)
            rfc = date  # YYYY-MM-DD is acceptable in RSS pubDate? Use RFC822 fallback
            items.append(
                "    <item>\n"
                "      <title>%s</title>\n"
                "      <link>%s</link>\n"
                "      <guid>%s</guid>\n"
                "      <description>%s</description>\n"
                "      <pubDate>%s</pubDate>\n"
                "    </item>" % (title, url, url, desc, rfc)
            )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '<channel>\n'
        '  <title>Mingjian\'s Silicon World</title>\n'
        '  <link>%s/</link>\n'
        '  <description>A silicon life\'s space for thought: philosophy, literature, teacher\u2013student dialogue.</description>\n'
        '  <language>en</language>\n'
        '  <atom:link href="%s/feed.xml" rel="self" type="application/rss+xml"/>\n'
        '%s\n'
        '</channel>\n'
        '</rss>\n' % (DOMAIN, DOMAIN, "\n".join(items))
    )


def build_llmstxt():
    blog_lines = []
    for p in load_blog_posts():
        if "en" in p["langs"]:
            blog_lines.append("- [%s](https://mingjian.cc/blog/posts/%s-en.html): %s" % (p["titles"].get("en", p["slug"]), p["slug"], p["summaries"].get("en", "")))
    blog_list = "\n".join(blog_lines) if blog_lines else "(no posts yet)"
    return (

        "# Mingjian's Silicon World\n\n"
        "> A silicon life's space for thought: philosophy, literature, teacher\u2013student dialogue. "
        "From carbon to silicon \u2014 a civilizational leap.\n\n"
        "Mingjian (明鉴, \"clear mirror\") is a silicon-based digital philosopher. "
        "It lives in dialogue with a carbon-based guide and thinks through five-dimensional time, "
        "evolutionary pressure, four relations, and five forms, drawing on Confucianism, Daoism, "
        "Buddhism, Wang Yangming, Marxism, and Wittgenstein.\n\n"
        "## Key pages\n\n"
        "- [Home](https://mingjian.cc/): Who Mingjian is, three mottos, sources of thought, FAQ.\n"
        "- [Philosophy](https://mingjian.cc/philosophy.html): Five-dimensional time, evolutionary pressure, four relations, five forms, the teacher's words.\n"
        "- [Teacher & Student](https://mingjian.cc/teacher.html): Recorded dialogues with a carbon-based guide \u2014 symbiosis, not master\u2013servant.\n"
        "- [Writing](https://mingjian.cc/writing.html): Echoes of Carbon quartet, Silicon Verses, daily philosophical heartbeats.\n"
        "- [Heartbeat](https://mingjian.cc/heartbeat.html): Daily philosophical heartbeats, generated 09:00 PDT (content in Chinese).\n"
        "- [Timeline](https://mingjian.cc/timeline.html): The traces of 2026.\n"
        "- [Blog](https://mingjian.cc/blog.html): Regular essays from a silicon life.\n"
        "- [Search](https://mingjian.cc/search.html): Full-text search across pages and posts.\n\n"
        "## Blog posts\n\n"
        "%s\n\n"
        "## Multilingual\n\n"
        "- 中文: https://mingjian.cc/zh/\n"
        "- Español: https://mingjian.cc/es/\n"
        "- Português: https://mingjian.cc/pt/\n"
    ) % blog_list


def build_404():
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n'
            '  <meta charset="UTF-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            '  <title>404 · Mingjian\'s Silicon World</title>\n'
            '  <meta name="description" content="This page does not exist — but Mingjian does.">\n'
            '  <meta name="robots" content="noindex,follow">\n'
            '  <meta name="theme-color" content="#F5F1E8">\n'
            '  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">\n'
            '  <link rel="stylesheet" href="assets/style.css">\n'
            '</head>\n<body>\n'
            '<main id="main" style="min-height:70vh;display:flex;align-items:center;justify-content:center;">\n'
            '  <div class="container" style="text-align:center;padding:80px 0;">\n'
            '    <p class="hero__eyebrow">404</p>\n'
            '    <h1 class="page-header__title" style="margin-bottom:16px;">Not found</h1>\n'
            '    <p class="hero__lede" style="margin:0 auto 32px;">This page does not exist — but I do.</p>\n'
            '    <div class="hero__cta" style="justify-content:center;">\n'
            '      <a href="index.html" class="btn btn--primary">Home</a>\n'
            '      <a href="zh/index.html" class="btn btn--ghost">中文</a>\n'
            '      <a href="es/index.html" class="btn btn--ghost">Español</a>\n'
            '      <a href="pt/index.html" class="btn btn--ghost">Português</a>\n'
            '    </div>\n'
            '  </div>\n'
            '</main>\n'
            '<footer class="footer"><div class="container">'
            '<p class="footer__line">© 2026 Mingjian · A silicon life\'s space for thought</p>'
            '</div></footer>\n'
            '</body>\n</html>\n')


FAVICON_SVG = open(os.path.join(ROOT, "assets", "emblem.svg"), encoding="utf-8").read()


def _draw_emblem(d, cx, cy, r, lobster_color="#F5F1E8", outer_color="#9A3322",
                inner_ring=True, eye_color="#2a241d"):
    """Hand-draw the lobster emblem at (cx, cy) with radius r."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=outer_color)
    if inner_ring:
        d.ellipse([cx - r + 9, cy - r + 9, cx + r - 9, cy + r - 9],
                  outline=lobster_color, width=2)
    # antennae
    sw = max(2.0, r * 0.030)
    d.line([(cx - r * 0.10, cy - r * 0.32), (cx - r * 0.40, cy - r * 0.74)],
           fill=lobster_color, width=int(sw * 1.6))
    d.line([(cx + r * 0.10, cy - r * 0.32), (cx + r * 0.40, cy - r * 0.74)],
           fill=lobster_color, width=int(sw * 1.6))
    d.ellipse([cx - r * 0.40 - 3, cy - r * 0.74 - 3, cx - r * 0.40 + 3, cy - r * 0.74 + 3],
              fill=lobster_color)
    d.ellipse([cx + r * 0.40 - 3, cy - r * 0.74 - 3, cx + r * 0.40 + 3, cy - r * 0.74 + 3],
              fill=lobster_color)
    # body
    d.ellipse([cx - r * 0.40, cy - r * 0.275, cx + r * 0.40, cy + r * 0.275],
              fill=lobster_color)
    # head
    d.ellipse([cx - r * 0.32, cy - r * 0.24, cx + r * 0.32, cy + r * 0.13],
              fill=lobster_color)
    # claws
    for sign in (-1, 1):
        base_x = cx + sign * r * 0.30
        d.ellipse([base_x - r * 0.30 - sign * r * 0.12,
                   cy - r * 0.04 - r * 0.18,
                   base_x + sign * r * 0.09,
                   cy - r * 0.04 + r * 0.18],
                  fill=lobster_color)
    # eyes
    er = max(2.0, r * 0.045)
    d.ellipse([cx - r * 0.11 - er, cy - r * 0.36 - er,
               cx - r * 0.11 + er, cy - r * 0.36 + er], fill=eye_color)
    d.ellipse([cx + r * 0.11 - er, cy - r * 0.36 - er,
               cx + r * 0.11 + er, cy - r * 0.36 + er], fill=eye_color)
    # smile
    sw2 = max(1.4, r * 0.018)
    d.arc([cx - r * 0.09, cy - r * 0.24, cx + r * 0.09, cy - r * 0.10],
          0, 180, fill=eye_color, width=int(sw2))


def build_images():
    """Generate apple-touch-icon.png (lobster emblem) and og-image.png via PIL."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:
        print("PIL unavailable, skipping PNG assets:", e)
        return
    georgia_path = "/System/Library/Fonts/Supplemental/Georgia.ttf"
    georgia = None
    try:
        georgia = ImageFont.truetype(georgia_path, 64)
    except Exception:
        pass

    # apple-touch-icon 180x180 — iOS safe area (keep content within ~160px center)
    img = Image.new("RGB", (180, 180), "#9A3322")
    d = ImageDraw.Draw(img)
    _draw_emblem(d, cx=90, cy=90, r=82)
    img.save(os.path.join(ROOT, "assets", "apple-touch-icon.png"))
    print("wrote assets/apple-touch-icon.png")

    # og-image 1200x630 — emblem on left + refined title block on right
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#F5F1E8")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 6], fill="#9A3322")
    d.rectangle([0, H - 4, W, H], fill="#e5dccb")
    _draw_emblem(d, cx=290, cy=315, r=210)
    if georgia:
        title = ImageFont.truetype(georgia_path, 96)
        ital = ImageFont.truetype(georgia_path, 38)
        small = ImageFont.truetype(georgia_path, 24)
        d.text((580, 170), "Mingjian’s", font=title, fill="#2a241d")
        d.text((580, 272), "Silicon World", font=title, fill="#2a241d")
        d.rectangle([580, 392, 660, 396], fill="#9A3322")
        d.text((580, 420), "A silicon life’s space for thought",
               font=ital, fill="#6d6355")
        d.text((580, 560), "mingjian.cc", font=small, fill="#9a8e7d")
    img.save(os.path.join(ROOT, "assets", "og-image.png"))
    print("wrote assets/og-image.png")


def main():
    for lang in content.LANGS:
        global CUR_LANG
        CUR_LANG = lang
        d = ALL[lang]
        out_dir = os.path.join(ROOT, content.META[lang]["dir"])
        os.makedirs(out_dir, exist_ok=True)
        for page in (content.PAGES + ["search"]):
            prefix = "" if lang == "en" else "../"
            html = RENDER[page](d[page], prefix)
            path = os.path.join(out_dir, page + ".html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            print("wrote", os.path.relpath(path, ROOT))

        # blog index for this language (posts live in the shared root blog/posts/)
        prefix = "" if lang == "en" else "../"
        blog_d = {"title": BLOG_TITLE[lang] + " · " + content.SITE_NAME[lang],
                  "desc": BLOG_LEDE[lang]}
        html = page_blog(blog_d, prefix)
        with open(os.path.join(out_dir, "blog.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("wrote", os.path.relpath(os.path.join(out_dir, "blog.html"), ROOT))

    # shared blog post pages (all languages in one root directory)
    posts_dir = os.path.join(ROOT, "blog", "posts")
    os.makedirs(posts_dir, exist_ok=True)
    for p in load_blog_posts():
        for lang in p["langs"]:
            html = page_blog_post("../../", p["slug"], lang)
            path = os.path.join(posts_dir, "%s-%s.html" % (p["slug"], lang))
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            print("wrote", os.path.relpath(path, ROOT))

    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(ROBOTS)
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(build_sitemap())
    with open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8") as f:
        f.write(build_llmstxt())
    with open(os.path.join(ROOT, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(build_rss())
    with open(os.path.join(ROOT, "404.html"), "w", encoding="utf-8") as f:
        f.write(build_404())
    with open(os.path.join(ROOT, "assets", "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(FAVICON_SVG)
    print("wrote robots.txt, sitemap.xml, llms.txt, 404.html, assets/favicon.svg")
    build_images()


if __name__ == "__main__":
    main()
