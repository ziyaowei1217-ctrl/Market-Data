"""Weekly issues in Supabase Storage: publish from the workflow, download as a reader.

Layout of the private bucket "reports" (see storage.sql):
    weekly/2026-10-23/weekly-report.pdf, issue.json, <chart>.png / <chart>.pdf
    weekly/latest.json      issue.json of the newest issue plus its "path"; written last

Publishing needs only the warehouse connection string: it inserts a one-time ticket into
public.report_upload_tokens, and the report-upload Edge Function trades it for signed upload links.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets

BUCKET = 'reports'
STORAGE_SQL = Path(__file__).with_name('storage.sql')
TYPES = {'.pdf': 'application/pdf', '.png': 'image/png', '.json': 'application/json'}


UPLOAD_FUNCTION = 'functions/v1/report-upload'


def new_ticket():
    """A random upload token and the sha256 hex digest stored for it."""
    token = secrets.token_hex(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


class Storage:
    """Database side of publishing: bucket and policy, one-time upload tickets, the newest issue so far."""

    def __init__(self, db_url):
        import psycopg
        self.conn = psycopg.connect(db_url, autocommit=True, prepare_threshold=None)

    def prepare(self):
        self.conn.execute(STORAGE_SQL.read_text(encoding='utf-8'))

    def ticket(self):
        token, digest = new_ticket()
        self.conn.execute('insert into public.report_upload_tokens (token_hash) values (%s)', [digest])
        return token, digest

    def drop(self, digest):
        self.conn.execute('delete from public.report_upload_tokens where token_hash = %s', [digest])

    def newest(self):
        """The latest issue date already in the bucket (from weekly/<date>/issue.json), or None."""
        row = self.conn.execute(
            "select max(substring(name from '^weekly/([0-9]{4}-[0-9]{2}-[0-9]{2})/issue[.]json$')) "
            "from storage.objects where bucket_id = %s", [BUCKET]).fetchone()
        return row[0] if row else None

    def close(self):
        self.conn.close()


def _sign(url, token):
    """Ask the report-upload function for signed upload links: {path: url}."""
    import requests

    def sign(paths):
        response = requests.post(f'{url}/{UPLOAD_FUNCTION}', json={'token': token, 'paths': list(paths)}, timeout=60)
        if response.status_code != 200:
            raise OSError(f'无法取得上传链接（{response.status_code}）')
        return {item['path']: item['url'] for item in response.json()['uploads']}
    return sign


def _put(url, body, headers):
    import requests
    from pipeline.warehouse.client import PUBLISHABLE_KEY  # identifies the project at the gateway; grants nothing
    response = requests.put(url, data=body, headers={**headers, 'apikey': PUBLISHABLE_KEY}, timeout=120)
    if response.status_code >= 300:
        raise OSError(f'上传失败 {response.status_code}：{url.split("?")[0].rsplit("/", 1)[-1]}')


def _headers(content_type, cache='max-age=3600'):
    return {'Content-Type': content_type, 'x-upsert': 'true', 'cache-control': cache}


def publish(folder, sign, put=None, newest=None):
    """Upload the files a build listed in issue.json; point latest.json at it unless a newer issue is out.

    `sign(paths)` returns a signed upload link per path. Returns the object paths written;
    latest.json goes last, once the issue is complete."""
    put = put or _put
    folder = Path(folder)
    summary = json.loads((folder / 'issue.json').read_text(encoding='utf-8'))
    prefix = f"weekly/{summary['as_of']}"
    names = list(dict.fromkeys(list(summary.get('files', [])) + ['issue.json']))
    for name in names:
        path = folder / name
        if Path(name).name != name or path.suffix not in TYPES or not path.is_file():
            raise ValueError(f'issue.json 列出的文件不存在或类型不对：{name}')
    move_latest = not newest or summary['as_of'] >= newest   # a backfilled older week leaves latest alone
    targets = [f'{prefix}/{name}' for name in names]
    links = sign(targets + (['weekly/latest.json'] if move_latest else []))
    for name, target in zip(names, targets):
        path = folder / name
        put(links[target], path.read_bytes(), _headers(TYPES[path.suffix]))
    if not move_latest:
        return targets
    latest = json.dumps({**summary, 'path': prefix}, ensure_ascii=False, indent=2).encode('utf-8')
    put(links['weekly/latest.json'], latest, _headers('application/json', cache='max-age=60'))
    return targets + ['weekly/latest.json']


def _get(url, headers):
    import requests
    response = requests.get(url, headers=headers, timeout=120)
    if response.status_code == 400 or response.status_code == 404:
        raise OSError('找不到这一期；如果不是日期写错，请确认账号已在读者名单内。')
    response.raise_for_status()
    return response.content


def fetch_issue(folder, week=None, url=None, apikey=None, token=None, get=None):
    """Download one issue's PDF (latest by default) with a reader's own session; returns the saved path."""
    if token is None:
        from pipeline.warehouse import client
        url, apikey, token = url or client.SUPABASE_URL, apikey or client.PUBLISHABLE_KEY, client._token()
    get = get or _get
    headers = {'apikey': apikey, 'Authorization': f'Bearer {token}'}
    base = f'{url}/storage/v1/object/authenticated/{BUCKET}'
    if week:
        prefix, as_of = f'weekly/{week}', week
    else:
        latest = json.loads(get(f'{base}/weekly/latest.json', headers))
        prefix, as_of = latest['path'], latest['as_of']
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / f'市场一周-{as_of}.pdf'
    saved.write_bytes(get(f'{base}/{prefix}/weekly-report.pdf', headers))
    return saved


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog='python3 -m pipeline.report publish',
                                     description='把 build 生成的一期上传到 Supabase Storage（仅读者可下载）。')
    parser.add_argument('folder', type=Path, nargs='?', default=Path('outputs/weekly'))
    args = parser.parse_args(argv)
    db_url = os.environ.get('WAREHOUSE_DB_URL')
    if not db_url:
        parser.error('请设置 WAREHOUSE_DB_URL（数据库连接串）。')
    from pipeline.warehouse.client import SUPABASE_URL
    url = os.environ.get('WAREHOUSE_REST_URL', SUPABASE_URL)
    try:
        store = Storage(db_url)
        try:
            store.prepare()
            token, digest = store.ticket()
            try:
                paths = publish(args.folder, _sign(url, token), newest=store.newest())
            finally:
                store.drop(digest)
        finally:
            store.close()
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'无法发布：{exc}\n')
    note = '' if paths[-1] == 'weekly/latest.json' else '；库里已有更新的一期，latest 未改'
    print(f'已上传 {len(paths)} 个文件到 {BUCKET}/{paths[0].rsplit("/", 1)[0]}{note}')


def latest_main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog='python3 -m pipeline.report latest',
                                     description='用读者账号（WAREHOUSE_EMAIL / WAREHOUSE_PASSWORD）下载周报 PDF。')
    parser.add_argument('--week', help='某一期的周五截点 YYYY-MM-DD；默认最新一期')
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    args = parser.parse_args(argv)
    try:
        print(fetch_issue(args.output_dir, week=args.week).resolve())
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'无法下载：{exc}\n')
