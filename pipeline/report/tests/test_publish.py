"""Publishing an issue to Supabase Storage and fetching it back as a reader (fake HTTP, no network)."""
import json
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
REPORT = REPO / 'pipeline' / 'report'


def built_issue(folder):
    folder = Path(folder)
    (folder / 'weekly-report.pdf').write_bytes(b'%PDF-1.4 issue')
    (folder / 'weekly-returns.png').write_bytes(b'png')
    (folder / 'weekly-returns.pdf').write_bytes(b'%PDF-1.4 chart')
    (folder / 'issue.json').write_text(json.dumps({'as_of': '2026-10-23', 'pages': 6, 'charts': ['returns'],
                                                   'files': ['weekly-report.pdf', 'weekly-returns.png']}),
                                       encoding='utf-8')
    return folder


class PublishTests(unittest.TestCase):
    def test_issue_files_go_up_first_and_latest_pointer_last(self):
        from pipeline.report.publish import publish
        calls = []
        with tempfile.TemporaryDirectory() as folder:
            paths = publish(built_issue(folder), 'https://x.supabase.co', 'sb_secret_test',
                            put=lambda url, body, headers: calls.append((url, body, headers)))
        urls = [url for url, _, _ in calls]
        base = 'https://x.supabase.co/storage/v1/object/reports/'
        self.assertEqual(urls[-1], base + 'weekly/latest.json')
        self.assertEqual(set(urls[:-1]), {base + 'weekly/2026-10-23/' + name for name in
                                          ('weekly-report.pdf', 'issue.json', 'weekly-returns.png', 'weekly-returns.pdf')})
        self.assertIn('weekly/2026-10-23/weekly-report.pdf', paths)
        for url, body, headers in calls:
            self.assertEqual(headers['apikey'], 'sb_secret_test')
            self.assertNotIn('Authorization', headers)        # the gateway turns a secret key into a role token
            self.assertEqual(headers['x-upsert'], 'true')
        types = {url.rsplit('/', 1)[-1]: headers['Content-Type'] for url, _, headers in calls}
        self.assertEqual(types['weekly-report.pdf'], 'application/pdf')
        self.assertEqual(types['weekly-returns.png'], 'image/png')
        latest = json.loads(calls[-1][1])
        self.assertEqual((latest['as_of'], latest['path']), ('2026-10-23', 'weekly/2026-10-23'))

    def test_reader_downloads_the_latest_issue_with_their_own_session(self):
        from pipeline.report.publish import fetch_issue
        latest = json.dumps({'as_of': '2026-10-23', 'path': 'weekly/2026-10-23', 'files': ['weekly-report.pdf']})
        seen = []

        def get(url, headers):
            seen.append((url, headers))
            return latest.encode() if url.endswith('latest.json') else b'%PDF-1.4 issue'
        with tempfile.TemporaryDirectory() as folder:
            saved = fetch_issue(folder, url='https://x.supabase.co', apikey='sb_publishable_x', token='user-jwt', get=get)
            self.assertEqual(saved.name, '市场一周-2026-10-23.pdf')
            self.assertEqual(saved.read_bytes(), b'%PDF-1.4 issue')
        self.assertEqual(seen[0][0], 'https://x.supabase.co/storage/v1/object/authenticated/reports/weekly/latest.json')
        self.assertEqual(seen[1][0], 'https://x.supabase.co/storage/v1/object/authenticated/reports/weekly/2026-10-23/weekly-report.pdf')
        self.assertEqual(seen[0][1], {'apikey': 'sb_publishable_x', 'Authorization': 'Bearer user-jwt'})

    def test_a_named_week_skips_the_latest_pointer(self):
        from pipeline.report.publish import fetch_issue
        seen = []
        with tempfile.TemporaryDirectory() as folder:
            fetch_issue(folder, week='2026-10-16', url='https://x.supabase.co', apikey='k', token='t',
                        get=lambda url, headers: seen.append(url) or b'%PDF')
        self.assertEqual(seen, ['https://x.supabase.co/storage/v1/object/authenticated/reports/weekly/2026-10-16/weekly-report.pdf'])


class StorageAccessTests(unittest.TestCase):
    """The repository is public: issues contain licensed data and must reach readers only."""

    def test_bucket_is_private_and_readable_by_readers_only(self):
        sql = (REPORT / 'storage.sql').read_text(encoding='utf-8').lower()
        self.assertIn("'reports', 'reports', false", sql)
        self.assertIn('on storage.objects for select to authenticated', sql)
        self.assertIn("bucket_id = 'reports' and (select private.is_reader())", sql)
        for verb in ('insert', 'update', 'delete'):
            self.assertNotIn(f'on storage.objects for {verb}', sql)

    def test_workflow_publishes_after_the_weekly_run_and_never_as_a_public_artifact(self):
        workflow = (REPO / '.github' / 'workflows' / 'report.yml').read_text(encoding='utf-8')
        self.assertIn('workflows: [warehouse]', workflow)
        self.assertIn("github.event.workflow_run.event == 'schedule'", workflow)
        self.assertIn('ref: warehouse', workflow)
        self.assertIn('python -m pipeline.report build', workflow)
        self.assertIn('python -m pipeline.report publish', workflow)
        self.assertNotIn('upload-artifact', workflow)
        self.assertNotIn('upload-pages-artifact', workflow)


if __name__ == '__main__':
    unittest.main()
