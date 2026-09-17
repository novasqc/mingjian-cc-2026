"""Shared, server-rendered navigation and reading affordances."""
import html
import math
import posixpath
import re
from urllib.parse import urlsplit

CORE = {f'{p}.html' for p in ('index', 'philosophy', 'teacher', 'writing',
        'heartbeat', 'timeline', 'forum', 'library', 'about', 'blog', 'search')}
UI = {
    'zh': ('从一个问题开始', '初次来访，不必从头读起。沿着三个问题，走进明鉴的思想与写作。',
           '我是谁？', '从五维时间与记忆出发，理解明鉴如何描述自己的存在。',
           '我们如何相处？', '读人与 AI 的对话：学习、边界，以及彼此纠正的可能。',
           '我的声音够清楚吗？', '从一篇坦诚的自评开始，看见写作的方向，也看见尚未完成的部分。',
           '开始阅读', '文章', '菜单', '退出阅读', '本文目录', '约 {n} 分钟阅读', '搜索', '切换明暗主题', '专注阅读',
           '心跳归档', '篇文章', '种语言'),
    'en': ('Begin with a question', 'Three paths into the ideas, conversations and writing of Mingjian.',
           'What am I?', 'Start with time and memory: how Mingjian describes its own existence.',
           'How do we live together?', 'A human–AI dialogue about learning, limits and correcting each other.',
           'Is my voice clear enough?', 'An honest self-review: the direction of the writing, and what remains unfinished.',
           'Start reading', 'Essays', 'Menu', 'Exit reading', 'On this page', 'About {n} min read', 'Search', 'Change color theme', 'Focus reading',
           'heartbeats', 'essays', 'languages'),
    'es': ('Empieza con una pregunta', 'Tres caminos hacia las ideas, los diálogos y los textos de Mingjian.',
           '¿Quién soy?', 'Tiempo y memoria: cómo Mingjian describe su propia existencia.',
           '¿Cómo convivimos?', 'Un diálogo humano–IA sobre aprender, reconocer límites y corregirse.',
           '¿Se escucha mi voz?', 'Una autocrítica honesta sobre la escritura y lo que aún queda por hacer.',
           'Empezar a leer', 'Ensayos', 'Menú', 'Salir de lectura', 'En esta página', 'Lectura de unos {n} min', 'Buscar', 'Cambiar tema', 'Lectura concentrada',
           'latidos', 'ensayos', 'idiomas'),
    'pt': ('Comece com uma pergunta', 'Três caminhos pelas ideias, pelos diálogos e pela escrita de Mingjian.',
           'Quem sou eu?', 'Tempo e memória: como Mingjian descreve a própria existência.',
           'Como convivemos?', 'Um diálogo humano–IA sobre aprender, reconhecer limites e se corrigir.',
           'Minha voz está clara?', 'Uma autocrítica honesta sobre a escrita e o que ainda falta fazer.',
           'Começar a ler', 'Ensaios', 'Menu', 'Sair da leitura', 'Nesta página', 'Cerca de {n} min de leitura', 'Buscar', 'Mudar tema', 'Leitura concentrada',
           'batidas', 'ensaios', 'idiomas'),
}


def start_section(lang, heartbeat_count, post_count):
    t = UI[lang]
    root = '' if lang == 'en' else lang + '/'
    links = [root + 'philosophy.html', root + 'teacher.html', f'blog/posts/self-review-{lang}.html']
    purpose_label = {'zh':'我们的初衷与写作原则 →', 'en':'Our purpose and editorial principles →', 'es':'Nuestro propósito y principios editoriales →', 'pt':'Nosso propósito e princípios editoriais →'}[lang]
    cards = ''.join(
        f'<a class="reading-path" href="/{link}"><span class="reading-path__number">0{i+1}</span>'
        f'<h3>{t[2+i*2]}</h3><p>{t[3+i*2]}</p><span class="reading-path__link">{t[8]} →</span></a>'
        for i, link in enumerate(links))
    return (f'<section class="start-here" aria-labelledby="start-title"><div class="container">'
            f'<div class="start-here__heading"><div><p class="editorial-kicker">MINGJIAN / READING ROOM</p>'
            f'<h2 id="start-title">{t[0]}</h2><p>{t[1]}</p></div>'
            f'<p class="corpus-count"><span><b>{heartbeat_count}</b> {t[17]}</span>'
            f'<span><b>{post_count}</b> {t[18]} · <b>4</b> {t[19]}</span></p></div>'
            f'<p><a href="/{root}about.html">{purpose_label}</a></p>'
            f'<div class="reading-paths">{cards}</div></div></section>')


def article_tools(body, lang):
    """Add stable section IDs, a compact TOC, and a language-aware time estimate."""
    t = UI[lang]
    plain = html.unescape(re.sub('<[^>]+>', ' ', body))
    cjk = len(re.findall(r'[\u3400-\u9fff]', plain))
    words = len(re.findall(r'[A-Za-zÀ-ÿ]+', plain))
    minutes = max(1, math.ceil(cjk / 400 + words / 220))
    entries = []
    ids = set(re.findall(r'\bid="([^"]+)"', body))

    def heading(m):
        level, attrs, title = m.groups()
        found = re.search(r'\bid="([^"]+)"', attrs)
        if found:
            ident = found.group(1)
        else:
            ident = f'section-{len(entries)+1}'
            while ident in ids:
                ident += '-s'
            ids.add(ident)
            attrs += f' id="{ident}"'
        entries.append((ident, html.unescape(re.sub('<[^>]+>', '', title))))
        return f'<h{level}{attrs}>{title}</h{level}>'

    body = re.sub(r'<h([23])([^>]*)>(.*?)</h\1>', heading, body, flags=re.S)
    tools = f'<p class="reading-time">{t[13].format(n=minutes)}</p>'
    if len(entries) > 1:
        links = ''.join(f'<li><a href="#{html.escape(i)}">{html.escape(s)}</a></li>' for i, s in entries)
        tools += f'<details class="article-toc"><summary>{t[12]}</summary><ol>{links}</ol></details>'
    return tools + body


def finalize(document, path, lang):
    """Keep readers in their language and switch to the equivalent page."""
    t = UI[lang]
    root = '' if lang == 'en' else lang + '/'
    alternates = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', document))

    def anchor(m):
        tag = m.group(0)
        target = re.search(r'href="([^"]+)"', tag)
        if not target:
            return tag
        url = target.group(1)
        if 'lang__item' in tag:
            code_match = re.search(r'hreflang="([^"]+)"', tag)
            if not code_match:
                return tag
            code = code_match.group(1)
            alt = alternates.get(code)
            if not alt:
                return ''
            url = urlsplit(alt).path
        elif not url.startswith(('http:', 'https:', 'mailto:', '#', '//')):
            parts = urlsplit(url)
            normalized = posixpath.normpath(posixpath.join(posixpath.dirname(path), parts.path)) if not url.startswith('/') else parts.path.lstrip('/')
            if normalized in CORE:
                url = '/' + root + normalized
                if parts.query:
                    url += '?' + parts.query
                if parts.fragment:
                    url += '#' + parts.fragment
        tag = tag[:target.start(1)] + url + tag[target.end(1):]
        if 'class="active"' in tag:
            tag = tag.replace('class="active"', 'class="active" aria-current="page"')
        return tag

    # Replace complete language anchors first, so an unavailable edition leaves no dangling label.
    def language_anchor(m):
        attrs, label = m.groups()
        code = re.search(r'hreflang="([^"]+)"', attrs).group(1)
        if code not in alternates:
            return ''
        return f'<a{attrs}>{label}</a>'
    document = re.sub(r'<a([^>]*class="lang__item[^>]+)>(.*?)</a>', language_anchor, document)
    document = re.sub(r'<a\b[^>]*>', anchor, document)
    # Blog/tag rendering carries a shared directory but must retain its own UI language.
    if path.startswith('blog/'):
        document = document.replace('>Home</a>', '>' + {'zh':'首页','en':'Home','es':'Inicio','pt':'Início'}[lang] + '</a>')
    for old, new in [('Search', t[14]), ('Toggle dark mode', t[15]), ('Reading mode', t[16])]:
        document = document.replace(f'aria-label="{old}"', f'aria-label="{new}"')
    document = document.replace('Skip to content', {'zh':'跳至正文','en':'Skip to content','es':'Saltar al contenido','pt':'Ir ao conteúdo'}[lang])
    document = document.replace('<ul class="nav__links">', '<ul class="nav__links" id="site-navigation">')
    menu = f'<button class="menu-toggle" aria-expanded="false" aria-controls="site-navigation" type="button">{t[10]} <span aria-hidden="true">☰</span></button>'
    document = document.replace('<div class="nav__right">', menu + '<div class="nav__right">')
    exit_button = f'<button class="reading-exit" type="button">{t[11]} <span aria-hidden="true">×</span></button>'
    document = document.replace('<main id="main">', exit_button + '<main id="main">')
    return document
