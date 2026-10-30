"""Date regressions exercise saved output, interrupted builds and backfills."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
import gen_site
from sitemap_lastmod import PageLastmods, lastmod_xml

DOMAIN = "https://mingjian.cc"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def dates(xml):
    root = ET.fromstring(xml)
    return {node.findtext(NS + "loc").removeprefix(DOMAIN + "/"):
            node.findtext(NS + "lastmod") for node in root.findall(NS + "url")}


class LastmodState(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def seed(self, pages):
        """A consistent historical sitemap/output pair, with no new manifest."""
        entries = []
        for path, (body, modified) in pages.items():
            output = self.root / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(body, encoding="utf-8")
            entries.append("<url><loc>%s/%s</loc>%s</url>" %
                           (DOMAIN, path, lastmod_xml(modified)))
        (self.root / "sitemap.xml").write_text(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>'
            % "".join(entries), encoding="utf-8")

    def tracker(self, paths, day="2026-10-28", **kwargs):
        return PageLastmods(self.root, paths, DOMAIN, build_date=day, **kwargs)

    def test_first_adoption_and_cross_day_rebuild_preserve_existing_dates(self):
        pages = {"index.html": ("<main>Home</main>", "2026-09-17"),
                 "zh/philosophy.html": ("<main>思想</main>", "2026-10-23T09:01:02-07:00")}
        self.seed(pages)
        initial = self.tracker(pages)
        initial.save()  # migration is persisted before any output is rewritten
        for path, (body, expected) in pages.items():
            (self.root / path).write_text(body, encoding="utf-8")
            self.assertEqual(initial.resolve(path), expected)
        initial.save()
        saved = initial.state_path.read_bytes()
        for day in ["2026-10-29", "2026-11-01"]:
            rerun = self.tracker(pages, day)
            for path, (_, expected) in pages.items():
                self.assertEqual(rerun.resolve(path), expected)
            rerun.save()
            self.assertEqual(saved, rerun.state_path.read_bytes())

    def test_only_page_with_changed_content_gets_new_date(self):
        pages = {"index.html": ("<main>Old</main>", "2026-10-23"),
                 "philosophy.html": ("<main>Unchanged</main>", "2026-09-17")}
        self.seed(pages)
        snapshot = self.tracker(pages)
        snapshot.save()
        (self.root / "index.html").write_text("<main>New</main>", encoding="utf-8")
        self.assertEqual(snapshot.resolve("index.html"), "2026-10-28")
        self.assertEqual(snapshot.resolve("philosophy.html"), "2026-09-17")
        snapshot.save()
        self.assertEqual(self.tracker(pages, "2026-10-30").resolve("index.html"), "2026-10-28")

    def test_manifest_recovers_after_html_written_but_sitemap_not_written(self):
        self.seed({"index.html": ("Old", "2026-09-17")})
        snapshot = self.tracker(["index.html"])
        snapshot.save()
        (self.root / "index.html").write_text("New", encoding="utf-8")
        # Crash here: sitemap still has the old date; rendered HTML is already new.
        retry = self.tracker(["index.html"], "2026-10-29")
        self.assertEqual(retry.resolve("index.html"), "2026-10-29")
        retry.save()
        # Crash after saving final state but before writing sitemap: do not date
        # the same change again on the next retry.
        second_retry = self.tracker(["index.html"], "2026-10-30")
        self.assertEqual(second_retry.resolve("index.html"), "2026-10-29")

    def test_known_manifest_survives_missing_output_and_corrupt_sitemap(self):
        self.seed({"index.html": ("Old", "2026-09-17")})
        snapshot = self.tracker(["index.html"])
        snapshot.save()
        (self.root / "index.html").unlink()
        (self.root / "sitemap.xml").write_text("<broken", encoding="utf-8")
        retry = self.tracker(["index.html"], warn=lambda _: None)
        self.assertIsNone(retry.resolve("index.html"))
        (self.root / "index.html").write_text("Old", encoding="utf-8")
        self.assertEqual(retry.resolve("index.html"), "2026-09-17")
        (self.root / "index.html").write_text("New", encoding="utf-8")
        self.assertEqual(retry.resolve("index.html"), "2026-10-28")

    def test_unknown_history_is_omitted_until_observed_change(self):
        # Neither an old sitemap nor a manifest: file mtime is not evidence.
        (self.root / "index.html").write_text("Old", encoding="utf-8")
        snapshot = self.tracker(["index.html", "new.html"])
        snapshot.save()
        self.assertIsNone(snapshot.resolve("index.html"))
        (self.root / "new.html").write_text("New page", encoding="utf-8")
        self.assertIsNone(snapshot.resolve("new.html"))
        snapshot.save()
        retry = self.tracker(["index.html", "new.html"], "2026-10-29")
        self.assertIsNone(retry.resolve("new.html"))
        (self.root / "index.html").write_text("Changed", encoding="utf-8")
        self.assertEqual(retry.resolve("index.html"), "2026-10-29")

    def test_corrupt_manifest_does_not_bind_new_html_to_old_sitemap_date(self):
        self.seed({"index.html": ("Old", "2026-09-17")})
        path = self.root / "build" / "sitemap-state.json"
        path.parent.mkdir()
        for corrupt in ["{unfinished", '{"version": 999, "pages": {}}',
                        '{"version": 1, "pages": {"index.html": null}}',
                        '{"version": 1, "pages": {"index.html": {"sha256": "bad", "lastmod": "2026-09-17"}}}']:
            with self.subTest(state=corrupt):
                path.write_text(corrupt, encoding="utf-8")
                (self.root / "index.html").write_text("Possibly partially built", encoding="utf-8")
                messages = []
                snapshot = self.tracker(["index.html"], warn=messages.append)
                self.assertIsNone(snapshot.resolve("index.html"))
                self.assertTrue(messages)
                snapshot.save()
                self.assertIsNone(self.tracker(["index.html"], "2026-10-29").resolve("index.html"))

    def test_bad_or_missing_sitemap_without_manifest_has_no_invented_date(self):
        for xml in ["<broken", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://mingjian.cc/index.html</loc><lastmod>2026-02-30</lastmod></url></urlset>']:
            with self.subTest(xml=xml):
                (self.root / "sitemap.xml").write_text(xml, encoding="utf-8")
                (self.root / "index.html").write_text("Existing content", encoding="utf-8")
                snapshot = self.tracker(["index.html"], warn=lambda _: None)
                self.assertIsNone(snapshot.resolve("index.html"))

    def test_main_persists_first_migration_before_interrupted_render(self):
        self.seed({"index.html": ("Old home", "2026-09-17"),
                   "philosophy.html": ("Old thought", "2026-09-18")})
        # Ordinary builds now require the reviewed image inputs before writing pages.
        (self.root / "assets").mkdir()
        for name in ("apple-touch-icon.png", "og-image.png"):
            (self.root / "assets" / name).write_bytes((ROOT / "assets" / name).read_bytes())
        paths = ["index.html", "philosophy.html"]
        with patch.object(gen_site, "ROOT", str(self.root)), \
                patch.object(gen_site, "sitemap_static_paths", return_value=paths), \
                patch.object(gen_site.content, "LANGS", ["en"]), \
                patch.object(gen_site.content, "PAGES", ["index", "philosophy"]), \
                patch.dict(gen_site.RENDER, {"index": lambda *_: "New home",
                                            "philosophy": lambda *_: (_ for _ in ()).throw(RuntimeError("fixture stop"))}), \
                patch.object(gen_site.reading, "finalize", side_effect=lambda html, *_: html), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "fixture stop"):
                gen_site.main()
        self.assertEqual((self.root / "index.html").read_text(), "New home")
        retry = self.tracker(paths, "2026-10-29")
        self.assertEqual(retry.resolve("index.html"), "2026-10-29")
        self.assertEqual(retry.resolve("philosophy.html"), "2026-09-18")


class SitemapIntegration(unittest.TestCase):
    def test_checked_in_static_dates_migrate_without_global_refresh(self):
        expected = dates((ROOT / "sitemap.xml").read_text(encoding="utf-8"))
        snapshot = PageLastmods(ROOT, gen_site.sitemap_static_paths(), DOMAIN,
                               build_date="2026-12-01")
        actual = dates(gen_site.build_sitemap(snapshot))
        for path in gen_site.sitemap_static_paths():
            with self.subTest(path=path):
                self.assertEqual(actual[path], expected[path])

    def test_backfill_updates_archive_but_preserves_explicit_article_times(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = ["index.html", "blog.html", "teacher.html", "about.html",
                     "heartbeat/archive.html", "heartbeat/en/archive.html"]
            for path in paths:
                output = root / path
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text("Old " + path, encoding="utf-8")
            root.joinpath("sitemap.xml").write_text(
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' %
                "".join('<url><loc>%s/%s</loc><lastmod>2026-10-25</lastmod></url>' %
                        (DOMAIN, path) for path in paths), encoding="utf-8")
            snapshot = PageLastmods(root, paths, DOMAIN, build_date="2026-10-28")
            snapshot.save()
            root.joinpath("heartbeat/archive.html").write_text("Added older entry", encoding="utf-8")
            root.joinpath("heartbeat/en/archive.html").write_text("Added English edition", encoding="utf-8")
            published = "2026-10-28T09:19:20-07:00"
            revised = "2026-10-28T11:00:00-07:00"
            items = [{"date": "2026-10-28", "modified_at": "2026-10-28T00:13:00-07:00"},
                     {"date": "2026-10-27", "published_at": published, "modified_at": revised},
                     {"date": "2026-10-26", "published_at": published},
                     {"date": "2026-10-25", "modified_at": "2026-10-27T11:00:00-07:00"}]
            posts = [{"slug": "essay", "langs": ["en"], "date": "2026-09-01", "dateModified": revised}]
            with patch.object(gen_site.content, "LANGS", ["en"]), \
                    patch.object(gen_site.content, "PAGES", ["index"]), \
                    patch.object(gen_site, "load_blog_posts", return_value=posts), \
                    patch.object(gen_site, "all_tags", return_value=[]), \
                    patch.object(gen_site, "load_heartbeats", return_value=items), \
                    patch.object(gen_site, "hb_en_available", return_value=["2026-10-27"]):
                actual = dates(gen_site.build_sitemap(snapshot))
            self.assertEqual(actual["index.html"], "2026-10-25")
            self.assertEqual(actual["heartbeat/archive.html"], "2026-10-28")
            self.assertEqual(actual["heartbeat/en/archive.html"], "2026-10-28")
            self.assertEqual(actual["heartbeat/2026-10-27.html"], revised)
            self.assertEqual(actual["heartbeat/en/2026-10-27.html"], revised)
            self.assertEqual(actual["heartbeat/2026-10-26.html"], published)
            self.assertEqual(actual["heartbeat/2026-10-25.html"], "2026-10-27T11:00:00-07:00")
            self.assertEqual(actual["blog/posts/essay-en.html"], revised)


if __name__ == "__main__":
    unittest.main()
