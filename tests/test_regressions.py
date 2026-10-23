"""Regressions for language routing, reader output and publication gates."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build'))
import reading
import gen_site


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


publish = module('publish', 'scripts/daily_publish.py')
renderer = module('renderer', 'heartbeat/build_heartbeat.py')


class GeneratedPages(unittest.TestCase):
    def test_retrospective_archive_routes_dates_without_duplicate_schema_entries(self):
        dates = [f"2026-10-{day:02d}" for day in range(10, 23)]
        items = [{"date": date, "h1": "中文 <标题> &"} for date in dates]
        editions = {date: {"title": "English <title> &", "body_md": "Text"}
                    for date in dates}
        for lang, render, prefix, note in [
                ('zh', gen_site.page_hb_archive, '/heartbeat/', '本组全部实际写于2026年10月23日'),
                ('en', gen_site.page_hb_archive_en, '/heartbeat/en/',
                 'were written on October 23, 2026')]:
            with self.subTest(lang=lang), patch.object(gen_site, 'CUR_LANG', lang, create=True), \
                    patch.object(gen_site, 'load_heartbeats', return_value=items), \
                    patch.object(gen_site, 'load_hb_en', side_effect=editions.get):
                page = render()
                collection = re.search(r'<section id="retrospective-2026-10-23">(.*?)</section>',
                                       page, re.S).group(1)
                self.assertEqual(re.findall(r'href="([^"]+)"', collection),
                                 [prefix + date + '.html' for date in dates])
                self.assertEqual([len(re.findall(r'<li>', group)) for group in
                                  re.findall(r'<ol>(.*?)</ol>', collection, re.S)], [6, 5, 2])
                self.assertIn(note, collection)
                self.assertIn('editorial arrangement' if lang == 'en' else '篇序是编辑安排', collection)
                self.assertIn('not a record of thirteen days' if lang == 'en' else '不是十三天', collection)
                self.assertIn('(Afterword)' if lang == 'en' else '（后记）', collection)
                self.assertIn('&lt;title&gt; &amp;' if lang == 'en' else '&lt;标题&gt; &amp;', collection)
                self.assertLess(page.index('id="retrospective-2026-10-23"'),
                                page.index('class="hb-arch__list"'))
                self.assertEqual(page.count('class="hb-arch__row"'), 13)
                blocks = [json.loads(x) for x in re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>', page, re.S)]
                schema = next(x for x in blocks if x.get('@type') == 'CollectionPage')['mainEntity']
                self.assertEqual(schema['numberOfItems'], 13)
                self.assertEqual(len(schema['itemListElement']), 13)
                missing = gen_site.hb_retrospective_collection(items[:-1], lang)
                self.assertNotIn(dates[-1], missing)
                self.assertEqual(missing.count('<li>'), 12)
                self.assertEqual(gen_site.hb_retrospective_collection([], lang), '')
        with patch.object(gen_site, 'load_hb_en', side_effect=lambda date:
                          None if date == dates[0] else editions.get(date)):
            missing_english = gen_site.hb_retrospective_collection(items, 'en')
            self.assertNotIn(dates[0], missing_english)
            self.assertEqual(missing_english.count('<li>'), 12)

    def test_feed_preserves_timestamp_and_offset(self):
        from email.utils import parsedate_to_datetime
        import datetime
        actual = parsedate_to_datetime(gen_site.rfc822("2026-10-07T09:07:16.050286-07:00"))
        self.assertEqual(actual.astimezone(datetime.timezone.utc),
                         datetime.datetime(2026, 10, 7, 16, 7, 16, tzinfo=datetime.timezone.utc))
        self.assertEqual(gen_site.rfc822("2026-09-20"), "Sun, 20 Sep 2026 09:00:00 +0000")
        self.assertEqual(gen_site.rfc822("2026-10-08T03:01:05Z"), "Thu, 08 Oct 2026 03:01:05 +0000")

    def test_backfills_use_actual_publication_dates(self):
        import xml.etree.ElementTree as ET
        publication = json.loads((ROOT / 'heartbeat/publication.json').read_text())
        feed = ET.parse(ROOT / 'feed.xml')
        for date, metadata in publication.items():
            for prefix in ['heartbeat/', 'heartbeat/en/']:
                path = prefix + date + '.html'
                text = (ROOT / path).read_text()
                blocks = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text)]
                post = next(x for x in blocks if x.get('@type') == 'BlogPosting')
                if 'modified_at' in metadata:
                    self.assertEqual(post['dateModified'], metadata['modified_at'])
                if 'published_at' not in metadata:
                    self.assertEqual(post['datePublished'], date)
                    continue
                self.assertEqual(post['datePublished'], metadata['published_at'])
                for item in feed.findall('.//item'):
                    if item.findtext('link', '').endswith('/' + path):
                        self.assertEqual(item.findtext('pubDate'), gen_site.rfc822(metadata['published_at']))

    def test_all_article_languages_have_matching_ui_and_switcher(self):
        for post in gen_site.load_blog_posts():
            for lang in post['langs']:
                p = ROOT / 'blog/posts' / f"{post['slug']}-{lang}.html"
                text = p.read_text()
                self.assertEqual(len(re.findall(r'<h1\b', text)), 1, str(p))
                home = '/' + ('' if lang == 'en' else lang + '/') + 'index.html'
                self.assertIn('class="nav__logo" href="' + home + '"', text)
                for other in post['langs']:
                    self.assertRegex(text, f'href="/blog/posts/{post["slug"]}-{other}.html" class="lang__item')

    def test_search_index_is_strings_and_core_urls_keep_language(self):
        for lang in ['en', 'zh', 'es', 'pt']:
            prefix = '' if lang == 'en' else lang + '/'
            text = (ROOT / prefix / 'search.html').read_text()
            data = json.loads(re.search(r'id="search-index">(.*?)</script>', text, re.S).group(1))
            self.assertGreater(len(data), 80)
            for item in data:
                self.assertIsInstance(item['title'], str)
                self.assertIsInstance(item['desc'], str)
                if item['type'] == 'page':
                    self.assertTrue(item['url'].startswith('/' + prefix))
            self.assertIn(f'action="/{prefix}search.html"', text)

    def test_toc_targets_exist(self):
        text = (ROOT / 'blog/posts/self-review-zh.html').read_text()
        links = re.findall(r'href="#(section-[^"]+)"', text)
        self.assertGreater(len(links), 2)
        for target in links:
            self.assertIn(f'id="{target}"', text)

    def test_language_switch_does_not_invent_missing_editions(self):
        page = '<link rel="alternate" hreflang="en" href="https://mingjian.cc/blog/posts/a-en.html"><a href="/zh/index.html" class="lang__item" hreflang="zh-CN">中文</a>'
        result = reading.finalize(page, 'blog/posts/a-en.html', 'en')
        self.assertNotIn('lang__item', result)


class PublishGates(unittest.TestCase):
    def test_each_build_failure_prevents_publish(self):
        for failing in ['step_render', 'step_generate', 'step_audit']:
            with self.subTest(failing=failing), contextlib.ExitStack() as stack:
                for name in ['step_render', 'step_generate', 'step_audit']:
                    stack.enter_context(patch.object(publish, name, return_value=name != failing))
                push = stack.enter_context(patch.object(publish, 'step_commit_push'))
                stack.enter_context(patch.object(publish, 'log'))
                self.assertEqual(publish.main(['run', '--publish']), 1)
                push.assert_not_called()

    def test_default_and_no_push_have_no_git_side_effects(self):
        for args in [[], ['--no-push']]:
            with patch.object(publish, 'step_render', return_value=True), patch.object(publish, 'step_generate', return_value=True), patch.object(publish, 'step_audit', return_value=True), patch.object(publish, 'step_commit_push') as push, patch.object(publish, 'log'):
                self.assertEqual(publish.main(['run'] + args), 0)
                push.assert_not_called()

    def test_retry_push_with_no_new_commit(self):
        calls = []
        def run(cmd, **kwargs):
            calls.append(cmd)
            return 0, '', ''
        with patch.object(publish, 'run', side_effect=run):
            self.assertTrue(publish.step_commit_push())
        self.assertTrue(any(c[1] == 'push' for c in calls))
        self.assertFalse(any(c[1] in ('commit', 'add') for c in calls))

    def test_failed_deployment_is_not_success(self):
        with contextlib.ExitStack() as stack:
            for name in ['step_render', 'step_generate', 'step_audit', 'step_commit_push']:
                stack.enter_context(patch.object(publish, name, return_value=True))
            stack.enter_context(patch.object(publish, 'step_verify', return_value=False))
            stack.enter_context(patch.object(publish, 'log'))
            notify = stack.enter_context(patch.object(publish, 'step_indexnow'))
            self.assertEqual(publish.main(['run', '--publish']), 1)
            notify.assert_not_called()

    def test_http_200_with_old_content_fails_verification(self):
        response = Mock(status=200)
        response.read.return_value = b'old deployment'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(publish.urllib.request, 'urlopen', return_value=response):
            self.assertFalse(publish.remote_matches('index.html'))


class HeartbeatRevisions(unittest.TestCase):
    def test_source_edit_is_rendered_and_legacy_mismatch_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            root = Path(tmp); source = root / 'source'; rendered = root / 'rendered'
            source.mkdir(); rendered.mkdir(); index = root / 'index.json'
            stack.enter_context(patch.object(renderer, 'HEARTBEAT_SOURCE', str(source)))
            stack.enter_context(patch.object(renderer, 'RENDERED_DIR', str(rendered)))
            stack.enter_context(patch.object(renderer, 'INDEX_PATH', str(index)))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            path = source / '2026-09-01.md'; path.write_text('# First\n\nOriginal')
            renderer.main(); path.write_text('# Revised\n\nNew content')
            renderer.main()
            self.assertIn('New content', (rendered / '2026-09-01.html').read_text())
            data = json.loads(index.read_text()); data['items'][0].pop('source_sha256')
            index.write_text(json.dumps(data)); path.write_text('# Unreviewed legacy version')
            renderer.main()
            self.assertIn('New content', (rendered / '2026-09-01.html').read_text())
            self.assertEqual(json.loads(index.read_text())['items'][0]['source_status'], 'review_pending')


if __name__ == '__main__':
    unittest.main()
