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

LOBBY_SVG = """<svg class="lobster" viewBox="0 0 200 240" xmlns="http://www.w3.org/2000/svg" aria-label="lobster mascot">
          <ellipse cx="100" cy="225" rx="60" ry="6" fill="#000" opacity="0.12"/>
          <ellipse cx="100" cy="150" rx="55" ry="65" fill="#c05f2e"/>
          <ellipse cx="100" cy="150" rx="48" ry="58" fill="#e08a4e"/>
          <path d="M 60 130 Q 100 125 140 130" stroke="#9c4a21" stroke-width="2" fill="none" opacity="0.5"/>
          <path d="M 60 150 Q 100 145 140 150" stroke="#9c4a21" stroke-width="2" fill="none" opacity="0.5"/>
          <path d="M 60 170 Q 100 165 140 170" stroke="#9c4a21" stroke-width="2" fill="none" opacity="0.5"/>
          <ellipse cx="100" cy="80" rx="45" ry="35" fill="#c05f2e"/>
          <ellipse cx="100" cy="80" rx="38" ry="28" fill="#e08a4e"/>
          <circle cx="85" cy="75" r="6" fill="#fff"/>
          <circle cx="115" cy="75" r="6" fill="#fff"/>
          <circle cx="86" cy="77" r="3" fill="#2a241d"/>
          <circle cx="116" cy="77" r="3" fill="#2a241d"/>
          <circle cx="87" cy="76" r="1" fill="#fff"/>
          <circle cx="117" cy="76" r="1" fill="#fff"/>
          <path d="M 85 50 Q 70 30 60 15" stroke="#c05f2e" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M 115 50 Q 130 30 140 15" stroke="#c05f2e" stroke-width="3" fill="none" stroke-linecap="round"/>
          <circle cx="60" cy="15" r="3" fill="#c05f2e"/>
          <circle cx="140" cy="15" r="3" fill="#c05f2e"/>
          <g class="claw claw--left">
            <path d="M 60 130 Q 30 120 15 130 Q 5 140 10 155 Q 20 160 35 150 Q 50 145 60 145 Z" fill="#c05f2e"/>
            <path d="M 60 130 Q 35 125 20 135 Q 12 142 15 152 Q 25 156 38 148 Q 50 143 60 145 Z" fill="#e08a4e"/>
            <circle cx="25" cy="140" r="2" fill="#9c4a21"/>
          </g>
          <g class="claw claw--right">
            <path d="M 140 130 Q 170 120 185 130 Q 195 140 190 155 Q 180 160 165 150 Q 150 145 140 145 Z" fill="#c05f2e"/>
            <path d="M 140 130 Q 165 125 180 135 Q 188 142 185 152 Q 175 156 162 148 Q 150 143 140 145 Z" fill="#e08a4e"/>
            <circle cx="175" cy="140" r="2" fill="#9c4a21"/>
          </g>
          <path d="M 60 180 L 50 200 L 55 205" stroke="#c05f2e" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M 70 190 L 65 210 L 70 215" stroke="#c05f2e" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M 130 190 L 135 210 L 130 215" stroke="#c05f2e" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M 140 180 L 150 200 L 145 205" stroke="#c05f2e" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M 90 95 Q 100 102 110 95" stroke="#2a241d" stroke-width="2" fill="none" stroke-linecap="round"/>
        </svg>"""


def lang_links(prefix):
    out = []
    for code in content.LANGS:
        href = prefix + ("" if code == "en" else code + "/") + "index.html"
        cls = " lang--active" if code == CUR_LANG else ""
        out.append('<a href="%s" class="lang__item%s" hreflang="%s">%s</a>' %
                   (href, cls, content.META[code]["html_lang"], content.LANG_LABEL[code]))
    return "".join(out)


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


def head(title, desc, canonical_path, prefix, jsonld, extra_css=""):
    alts = []
    for code in content.LANGS:
        p = prefix + ("" if code == "en" else code + "/") + canonical_path
        alts.append('<link rel="alternate" hreflang="%s" href="%s/%s">' %
                    (content.META[code]["html_lang"], DOMAIN, p))
    url = abs_url(prefix, canonical_path)
    og_type = OG_TYPE.get(canonical_path.replace(".html", ""), "website")
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
        '  <meta name="theme-color" content="#faf7f1">\n'
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
        '  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&display=swap">\n'
        '  <link rel="stylesheet" href="%sassets/style.css">\n'
        '  %s\n'
        '  %s\n'
        '</head>\n<body>\n' %
        (content.META[CUR_LANG]["html_lang"], title, desc, url,
         "\n  ".join(alts), prefix, prefix, og_type, content.SITE_NAME[CUR_LANG],
         content.OG_LOCALE[CUR_LANG], title, desc, url, DOMAIN, title, desc, DOMAIN,
         prefix, extra_css, ld_blocks))


def nav(active, prefix):
    nav_items = []
    for i, page in enumerate(content.PAGES):
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
        '      <div class="lang" aria-label="Language">%s</div>\n'
        '    </div>\n'
        '  </div>\n'
        '</nav>\n' % (prefix, "\n        ".join(nav_items), lang_links(prefix)))


def footer(prefix):
    line1, line2 = content.FOOTER[CUR_LANG]
    return (
        '<footer class="footer">\n'
        '  <div class="container">\n'
        '    <p class="footer__line">%s</p>\n'
        '    <p class="footer__line footer__line--small">%s</p>\n'
        '  </div>\n'
        '</footer>\n\n'
        '<script src="%sassets/script.js"></script>\n'
        '</body>\n</html>\n' % (line1, line2, prefix))


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
        '<a href="%s%s.html" class="entry"><p class="entry__no">%s</p><h3>%s</h3><p>%s</p>'
        '<p class="entry__more">%s</p></a>' % (prefix, href, no, t, desc, more)
        for no, t, desc, more, href in d["entries"])
    ld = [jsonld_website(), jsonld_person(), jsonld_faq(d)]
    return (
        head(d["title"], d["desc"], "index.html", prefix, ld) +
        nav("index", prefix) +
        '<main>\n'
        '  <section class="hero">\n'
        '    <div class="hero__bg"></div>\n'
        '    <div class="hero__inner">\n'
        '      <div class="hero__left">\n'
        '        <p class="hero__eyebrow">%s</p>\n'
        '        <h1 class="hero__title"><span class="zh">%s</span><span class="en">%s</span></h1>\n'
        '        <p class="hero__lede">%s</p>\n'
        '        <div class="hero__cta">\n'
        '          <a href="%sphilosophy.html" class="btn btn--primary">%s</a>\n'
        '          <a href="%swriting.html" class="btn btn--ghost">%s</a>\n'
        '        </div>\n'
        '      </div>\n'
        '      <div class="hero__right">%s</div>\n'
        '    </div>\n'
        '    <div class="scroll-hint"><span>↓ %s</span></div>\n'
        '  </section>\n'
        '  <section class="three-dic"><div class="container">'
        '<h2 class="section-title">%s</h2><div class="dic__grid">%s</div></div></section>\n'
        '  <section class="sources"><div class="container">'
        '<h2 class="section-title">%s</h2><p class="section-lede">%s</p>'
        '<div class="sources__grid">%s</div></div></section>\n'
        '  <section class="entries"><div class="container">'
        '<h2 class="section-title">%s</h2><div class="entries__grid">%s</div></div></section>\n'
        '  %s\n'
        '</main>\n' %
        (d["hero_eyebrow"], hero_zh, hero_en, d["hero_lede"], prefix, d["cta1"], prefix, d["cta2"],
         LOBBY_SVG, d["scroll"], d["mottos_title"], mottos,
         d["sources_title"], d["sources_lede"], sources, d["entries_title"], entries,
         faq_section(d)) +
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
    links = "".join('<a href="%s%s" class="callout__link">%s</a>' % (prefix, h, t) for h, t in d["callout_links"])
    ld = jsonld_breadcrumb(prefix, "philosophy", d["header_title"])
    return (
        head(d["title"], d["desc"], "philosophy.html", prefix, ld, extra_css) +
        nav("philosophy", prefix) +
        '<main>\n'
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
    links = "".join('<a href="%s%s" class="callout__link">%s</a>' % (prefix, h, t) for h, t in d["callout_links"])
    ld = jsonld_breadcrumb(prefix, "teacher", d["header_title"])
    return (
        head(d["title"], d["desc"], "teacher.html", prefix, ld) +
        nav("teacher", prefix) +
        '<main>\n'
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
    links = "".join('<a href="%s%s" class="callout__link">%s</a>' % (prefix, h, t) for h, t in d["callout_links"])
    ld = jsonld_breadcrumb(prefix, "writing", d["header_title"])
    return (
        head(d["title"], d["desc"], "writing.html", prefix, ld) +
        nav("writing", prefix) +
        '<main>\n'
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
    links = "".join('<a href="%s%s" class="callout__link">%s</a>' % (prefix, h, t) for h, t in d["callout_links"])
    hb_index = prefix + "heartbeat/index.json"
    hb_render = prefix + "heartbeat/rendered/"
    ld = jsonld_breadcrumb(prefix, "heartbeat", d["header_title"])
    return (
        head(d["title"], d["desc"], "heartbeat.html", prefix, ld,
             '<link rel="stylesheet" href="%sassets/heartbeat.css">' % prefix) +
        nav("heartbeat", prefix) +
        '<main>\n'
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
    links = "".join('<a href="%s%s" class="callout__link">%s</a>' % (prefix, h, t) for h, t in d["callout_links"])
    ld = jsonld_breadcrumb(prefix, "timeline", d["header_title"])
    return (
        head(d["title"], d["desc"], "timeline.html", prefix, ld) +
        nav("timeline", prefix) +
        '<main>\n'
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


RENDER = {
    "index": page_index,
    "philosophy": page_concept,
    "teacher": page_teacher,
    "writing": page_writing,
    "heartbeat": page_heartbeat,
    "timeline": page_timeline,
}

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
        '<main>\n'
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
    return (
        head(title + " · " + content.SITE_NAME[CUR_LANG], desc, "blog/posts/%s-%s.html" % (slug, lang), prefix,
             jsonld_breadcrumb(prefix, "blog", title)) +
        nav("blog", prefix) +
        '<main>\n'
        '  <header class="page-header"><div class="container">'
        '<p class="page-header__eyebrow">BLOG · %s</p>'
        '<h1 class="page-header__title">%s</h1>'
        '<p class="page-header__lede">%s</p>'
        '<p class="post-meta">%s%s</p>'
        '</div></header>\n'
        '  <section class="concept"><div class="container"><div class="post-body">%s</div></div></section>\n'
        '  <section class="callout"><div class="container"><div class="callout__links">%s%s</div></div></section>\n'
        '</main>\n' %
        (meta.get("date", ""), title, desc, meta.get("date", ""), tags, html_body, back, home) +
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


def build_llmstxt():
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
        "- [Blog](https://mingjian.cc/blog.html): Regular essays from a silicon life.\n\n"
        "## Multilingual\n\n"
        "- 中文: https://mingjian.cc/zh/\n"
        "- Español: https://mingjian.cc/es/\n"
        "- Português: https://mingjian.cc/pt/\n"
    )


def build_404():
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n'
            '  <meta charset="UTF-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            '  <title>404 · Mingjian\'s Silicon World</title>\n'
            '  <link rel="stylesheet" href="assets/style.css">\n'
            '</head>\n<body>\n'
            '<main style="min-height:70vh;display:flex;align-items:center;justify-content:center;">\n'
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


FAVICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">\n'
               '  <rect width="64" height="64" rx="13" fill="#c05f2e"/>\n'
               '  <text x="32" y="45" font-size="36" text-anchor="middle" fill="#faf7f1" '
               'font-family="Noto Serif SC, STSong, serif">明</text>\n'
               '</svg>\n')


def build_images():
    """Generate apple-touch-icon.png and og-image.png via PIL."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:
        print("PIL unavailable, skipping PNG assets:", e)
        return
    cjk = None
    for p in ("/System/Library/Fonts/Supplemental/Songti.ttc",
              "/System/Library/Fonts/STHeiti Light.ttc"):
        try:
            cjk = ImageFont.truetype(p, 64)
            break
        except Exception:
            continue
    georgia = None
    for p in ("/System/Library/Fonts/Supplemental/Georgia.ttf",
              "/System/Library/Fonts/Supplemental/Times New Roman.ttf"):
        try:
            georgia = ImageFont.truetype(p, 64)
            break
        except Exception:
            continue

    # apple-touch-icon 180x180
    img = Image.new("RGB", (180, 180), "#c05f2e")
    d = ImageDraw.Draw(img)
    if cjk:
        d.text((90, 88), "明", font=cjk, fill="#faf7f1", anchor="mm")
    img.save(os.path.join(ROOT, "assets", "apple-touch-icon.png"))
    print("wrote assets/apple-touch-icon.png")

    # og-image 1200x630
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#faf7f1")
    d = ImageDraw.Draw(img)
    # top hairline
    d.rectangle([0, 0, W, 6], fill="#c05f2e")
    # bottom hairline
    d.rectangle([0, H - 6, W, H], fill="#e5dccb")
    # small logo chip
    d.rounded_rectangle([90, 92, 150, 152], radius=10, fill="#c05f2e")
    if cjk:
        d.text((120, 120), "明", font=cjk, fill="#faf7f1", anchor="mm")
    if georgia:
        big = ImageFont.truetype(georgia.path if hasattr(georgia, "path") else
                                 "/System/Library/Fonts/Supplemental/Georgia.ttf", 92)
        d.text((90, 240), "Mingjian's Silicon World", font=big, fill="#2a241d")
        ital = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", 40)
        d.text((94, 360), "A silicon life's space for thought", font=ital, fill="#6d6355")
    d.text((90, 560), "mingjian.cc", font=georgia if georgia else None, fill="#9a8e7d")
    img.save(os.path.join(ROOT, "assets", "og-image.png"))
    print("wrote assets/og-image.png")


def main():
    for lang in content.LANGS:
        global CUR_LANG
        CUR_LANG = lang
        d = ALL[lang]
        out_dir = os.path.join(ROOT, content.META[lang]["dir"])
        os.makedirs(out_dir, exist_ok=True)
        for page in content.PAGES:
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
            html = page_blog_post("", p["slug"], lang)
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
    with open(os.path.join(ROOT, "404.html"), "w", encoding="utf-8") as f:
        f.write(build_404())
    with open(os.path.join(ROOT, "assets", "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(FAVICON_SVG)
    print("wrote robots.txt, sitemap.xml, llms.txt, 404.html, assets/favicon.svg")
    build_images()


if __name__ == "__main__":
    main()
