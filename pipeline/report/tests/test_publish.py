"""Publishing an issue to Supabase Storage and fetching it back as a reader (fake HTTP, no network)."""
import json
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
REPORT = REPO / 'pipeline' / 'report'


def built_issue(folder, as_of='2026-10-23'):
    folder = Path(folder)
    (folder / 'weekly-report.pdf').write_bytes(b'%PDF-1.4 issue')
    (folder / 'weekly-returns.png').write_bytes(b'png')
    (folder / 'weekly-returns.pdf').write_bytes(b'%PDF-1.4 chart')
    (folder / 'yield-curve.png').write_bytes(b'stale chart from an earlier build in the same folder')
    (folder / 'issue.json').write_text(json.dumps({'as_of': as_of, 'pages': 6, 'charts': ['returns'],
                                                   'files': ['weekly-report.pdf', 'weekly-returns.png',
                                                             'weekly-returns.pdf']}),
                                       encoding='utf-8')
    return folder


class FakeLinks:
    """Stands in for the report-upload function: records the paths asked for, returns one link per path."""

    def __init__(self):
        self.asked = []

    def __call__(self, paths):
        self.asked.append(list(paths))
        return {path: f'https://x.supabase.co/storage/v1/object/upload/sign/reports/{path}?token=t' for path in paths}


class PublishTests(unittest.TestCase):
    def test_issue_files_go_up_first_and_latest_pointer_last(self):
        from pipeline.report.publish import publish
        links, puts = FakeLinks(), []
        with tempfile.TemporaryDirectory() as folder:
            paths = publish(built_issue(folder), sign=links, newest=None,
                            put=lambda url, body, headers: puts.append((url, body, headers)))
        base = 'https://x.supabase.co/storage/v1/object/upload/sign/reports/'
        urls = [url for url, _, _ in puts]
        self.assertEqual(urls[-1], base + 'weekly/latest.json?token=t')
        self.assertEqual(set(urls[:-1]), {base + f'weekly/2026-10-23/{name}?token=t' for name in
                                          ('weekly-report.pdf', 'issue.json', 'weekly-returns.png', 'weekly-returns.pdf')})
        self.assertEqual(len(urls), 5)
        self.assertEqual(len(links.asked), 1)                      # one signing request per issue
        self.assertNotIn('weekly/2026-10-23/yield-curve.png', links.asked[0])  # not part of this build
        self.assertIn('weekly/2026-10-23/weekly-report.pdf', paths)
        types = {url.split('?')[0].rsplit('/', 1)[-1]: headers['Content-Type'] for url, _, headers in puts}
        self.assertEqual(types['weekly-report.pdf'], 'application/pdf')
        self.assertEqual(types['weekly-returns.png'], 'image/png')
        for _, _, headers in puts:
            self.assertNotIn('Authorization', headers)               # signed links carry their own token
        latest = json.loads(puts[-1][1])
        self.assertEqual((latest['as_of'], latest['path']), ('2026-10-23', 'weekly/2026-10-23'))

    def test_backfilling_an_older_week_leaves_latest_alone(self):
        from pipeline.report.publish import publish
        links, puts = FakeLinks(), []
        with tempfile.TemporaryDirectory() as folder:
            paths = publish(built_issue(folder, as_of='2026-10-16'), sign=links, newest='2026-10-23',
                            put=lambda url, body, headers: puts.append(url))
        self.assertNotIn('weekly/latest.json', links.asked[0])
        self.assertNotIn('weekly/latest.json', paths)
        self.assertTrue(all('/weekly/2026-10-16/' in url for url in puts))

    def test_republishing_the_newest_week_refreshes_latest(self):
        from pipeline.report.publish import publish
        links = FakeLinks()
        with tempfile.TemporaryDirectory() as folder:
            publish(built_issue(folder), sign=links, newest='2026-10-23', put=lambda url, body, headers: None)
        self.assertIn('weekly/latest.json', links.asked[0])

    def test_upload_tickets_are_hashed_and_short_lived(self):
        from pipeline.report.publish import new_ticket
        token, digest = new_ticket()
        import hashlib, re
        self.assertRegex(token, r'^[0-9a-f]{64}$')
        self.assertEqual(digest, hashlib.sha256(token.encode()).hexdigest())

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


class CommandLineTests(unittest.TestCase):
    def test_every_command_prints_help(self):
        import subprocess, sys
        for command in ([], ['build'], ['publish'], ['latest']):
            with self.subTest(command=command):
                run = subprocess.run([sys.executable, '-m', 'pipeline.report', *command, '--help'],
                                     capture_output=True, text=True, cwd=REPO)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn('python3 -m pipeline.report', run.stdout)


class StorageAccessTests(unittest.TestCase):
    """The repository is public: issues contain licensed data and must reach readers only."""

    def test_bucket_is_private_and_readable_by_readers_only(self):
        sql = (REPORT / 'storage.sql').read_text(encoding='utf-8').lower()
        self.assertIn("'reports', 'reports', false", sql)
        self.assertIn('on storage.objects for select to authenticated', sql)
        self.assertIn("bucket_id = 'reports' and (select private.is_reader())", sql)
        for verb in ('insert', 'update', 'delete'):
            self.assertNotIn(f'on storage.objects for {verb}', sql)

    def test_upload_tickets_are_invisible_to_api_users(self):
        sql = (REPORT / 'storage.sql').read_text(encoding='utf-8').lower()
        self.assertIn('alter table public.report_upload_tokens enable row level security', sql)
        self.assertIn('revoke all on public.report_upload_tokens from anon, authenticated', sql)
        self.assertNotIn('create policy', sql.split('report_upload_tokens', 1)[1])

    def test_workflow_publishes_after_the_weekly_run_and_never_as_a_public_artifact(self):
        workflow = (REPO / '.github' / 'workflows' / 'report.yml').read_text(encoding='utf-8')
        self.assertIn('workflows: [warehouse]', workflow)
        self.assertIn("github.event.workflow_run.event == 'schedule'", workflow)
        self.assertIn('ref: warehouse', workflow)
        self.assertIn('python -m pipeline.report build', workflow)
        self.assertIn('python -m pipeline.report publish', workflow)
        self.assertNotIn('upload-artifact', workflow)
        self.assertNotIn('upload-pages-artifact', workflow)

    def test_workflow_steps_fail_loudly_and_see_only_the_secrets_they_use(self):
        workflow = (REPO / '.github' / 'workflows' / 'report.yml').read_text(encoding='utf-8')
        self.assertNotIn('SUPABASE_SECRET_KEY', workflow)       # uploads need no extra secret
        steps = workflow.split('\n      - ')[1:]
        for step in steps:
            first = step.splitlines()[0]
            if '| tee' in step:
                self.assertIn('set -euo pipefail', step, first)
            if 'pip install' in step or 'unittest' in step:
                self.assertNotIn('secrets.', step, first)
        self.assertNotIn('secrets.', workflow.split('    steps:')[0])
        publish = next(step for step in steps if 'pipeline.report publish' in step)
        self.assertIn('secrets.WAREHOUSE_DB_URL', publish)


if __name__ == '__main__':
    unittest.main()
