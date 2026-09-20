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
