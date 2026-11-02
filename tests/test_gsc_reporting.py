import datetime
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gsc_reporting', ROOT / 'scripts/gsc_indexing.py')
gsc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gsc)


class SearchConsoleReporting(unittest.TestCase):
    def test_property_selection_rejects_lookalikes_and_path_scopes(self):
        svc = Mock()
        lookalikes = ['https://mingjian.cc.evil.example/', 'sc-domain:notmingjian.cc',
                     'https://example.org/mingjian.cc/', 'https://mingjian.cc/blog/']
        with patch.object(gsc, 'log'):
            svc.sites.return_value.list.return_value.execute.return_value = {
                'siteEntry': [{'siteUrl': x} for x in lookalikes]}
            self.assertIsNone(gsc.pick_site(svc))
            for valid in ['https://mingjian.cc/', 'sc-domain:mingjian.cc']:
                svc.sites.return_value.list.return_value.execute.return_value['siteEntry'].append({'siteUrl': valid})
                self.assertEqual(gsc.pick_site(svc), valid)

    def test_sitemap_counts_are_by_type_and_never_deprecated_indexed_counts(self):
        svc = Mock()
        svc.sitemaps.return_value.list.return_value.execute.return_value = {
            'sitemap': [{'path': 'https://mingjian.cc/sitemap.xml'}]}
        svc.sitemaps.return_value.get.return_value.execute.return_value = {
            'contents': [{'type': 'web', 'submitted': '349', 'indexed': '987654'},
                         {'type': 'image', 'submitted': '0'}, {'type': 'video'}]}
        with patch.object(gsc, 'log') as log:
            self.assertTrue(gsc.report_sitemaps(svc, 'sc-domain:mingjian.cc'))
        output = '\n'.join(c.args[0] for c in log.call_args_list)
        self.assertIn('web URLs in sitemap: 349', output)
        self.assertIn('image URLs in sitemap: 0', output)
        self.assertIn('video URLs in sitemap: unavailable', output)
        self.assertNotIn('987654', output)
        self.assertNotIn('discovered URLs: 3', output)

    def test_failed_queries_do_not_report_zero_and_propagate_partial_failure(self):
        svc = Mock()
        svc.sitemaps.return_value.list.return_value.execute.side_effect = RuntimeError('unavailable')
        svc.searchanalytics.return_value.query.return_value.execute.side_effect = RuntimeError('unavailable')
        with patch.object(gsc, 'log') as log:
            self.assertFalse(gsc.report_sitemaps(svc, 'sc-domain:mingjian.cc'))
            self.assertFalse(gsc.report_search_performance(svc, 'sc-domain:mingjian.cc'))
        output = '\n'.join(c.args[0] for c in log.call_args_list)
        self.assertNotIn('returned page rows: 0', output)
        self.assertNotIn('no sitemap entries', output)
        with patch.object(gsc.os.path, 'isfile', return_value=True), \
             patch.object(gsc, 'service', return_value=svc), \
             patch.object(gsc, 'pick_site', return_value='sc-domain:mingjian.cc'), \
             patch.object(gsc, 'report_sitemaps', return_value=False), \
             patch.object(gsc, 'report_search_performance', return_value=True) as performance, \
             patch.object(gsc, 'log'):
            self.assertEqual(gsc.main([]), 1)
            performance.assert_called_once()

    def test_performance_sample_has_explicit_window_and_scope_even_when_empty(self):
        svc = Mock()
        for count in [0, 100]:
            with self.subTest(count=count):
                svc.searchanalytics.return_value.query.return_value.execute.return_value = {
                    'rows': [{'keys': ['https://mingjian.cc/%s' % i], 'impressions': 1, 'clicks': 0}
                             for i in range(count)]}
                with patch.object(gsc, 'log') as log:
                    self.assertTrue(gsc.report_search_performance(svc, 'sc-domain:mingjian.cc'))
                body = svc.searchanalytics.return_value.query.call_args.kwargs['body']
                start = datetime.date.fromisoformat(body['startDate'])
                end = datetime.date.fromisoformat(body['endDate'])
                self.assertEqual((end-start).days, 27)
                self.assertLess(end, datetime.datetime.now(gsc.ZoneInfo('America/Los_Angeles')).date())
                self.assertEqual(body['dataState'], 'final')
                self.assertEqual(body['rowLimit'], 100)
                self.assertEqual(body['type'], 'web')
                output = '\n'.join(c.args[0] for c in log.call_args_list)
                self.assertIn('not all indexed pages or all performance rows', output)
                self.assertIn('Pacific time', output)
                if count == 0:
                    self.assertIn('index coverage remains unknown', output)

    def test_failed_sitemap_detail_is_explicit_and_incomplete(self):
        svc = Mock()
        svc.sitemaps.return_value.list.return_value.execute.return_value = {'sitemap': [{'path': 'x'}]}
        svc.sitemaps.return_value.get.return_value.execute.side_effect = RuntimeError('unavailable')
        with patch.object(gsc, 'log') as log:
            self.assertFalse(gsc.report_sitemaps(svc, 'sc-domain:mingjian.cc'))
        self.assertTrue(any('detail unavailable' in c.args[0] for c in log.call_args_list))


if __name__ == '__main__':
    unittest.main()
