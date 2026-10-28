"""Weekly issues in Supabase Storage: publish from the workflow, download as a reader.

Layout of the private bucket "reports" (see storage.sql):
    weekly/2026-10-23/weekly-report.pdf, issue.json, <chart>.png / <chart>.pdf
    weekly/latest.json      issue.json of the newest issue plus its "path"; written last
"""
import json
import os
from pathlib import Path

BUCKET = 'reports'
STORAGE_SQL = Path(__file__).with_name('storage.sql')
TYPES = {'.pdf': 'application/pdf', '.png': 'image/png', '.json': 'application/json'}


def ensure_bucket(db_url):
    """Create the private bucket and its readers-only policy (idempotent)."""
    import psycopg
    with psycopg.connect(db_url, autocommit=True, prepare_threshold=None) as conn:
        conn.execute(STORAGE_SQL.read_text(encoding='utf-8'))


def _post(url, body, headers):
    import requests
    response = requests.post(url, data=body, headers=headers, timeout=120)
    if response.status_code >= 300:
        raise OSError(f'上传失败 {response.status_code}：{url.rsplit("/", 1)[-1]}')


def _headers(key, content_type, cache='max-age=3600'):
    # A secret key (sb_secret_…) goes in apikey only; the API gateway swaps it for a service-role token.
    return {'apikey': key, 'Content-Type': content_type, 'x-upsert': 'true', 'cache-control': cache}


def publish(folder, url, key, put=None):
    """Upload a built issue folder; returns the object paths. latest.json goes last, once the issue is complete."""
    put = put or _post
    folder = Path(folder)
    summary = json.loads((folder / 'issue.json').read_text(encoding='utf-8'))
    prefix = f"weekly/{summary['as_of']}"
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix in TYPES)
    paths = []
    for path in files:
        target = f'{prefix}/{path.name}'
        put(f'{url}/storage/v1/object/{BUCKET}/{target}', path.read_bytes(), _headers(key, TYPES[path.suffix]))
        paths.append(target)
    latest = json.dumps({**summary, 'path': prefix}, ensure_ascii=False, indent=2).encode('utf-8')
    put(f'{url}/storage/v1/object/{BUCKET}/weekly/latest.json', latest,
        _headers(key, 'application/json', cache='max-age=60'))
    return paths + ['weekly/latest.json']


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
    key = os.environ.get('SUPABASE_SECRET_KEY')
    if not key:
        parser.error('请设置 SUPABASE_SECRET_KEY（Supabase → Settings → API Keys 的 secret key）。')
    from pipeline.warehouse.client import SUPABASE_URL
    try:
        if os.environ.get('WAREHOUSE_DB_URL'):
            ensure_bucket(os.environ['WAREHOUSE_DB_URL'])
        paths = publish(args.folder, os.environ.get('WAREHOUSE_REST_URL', SUPABASE_URL), key)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'无法发布：{exc}\n')
    print(f'已上传 {len(paths)} 个文件到 {BUCKET}/{paths[0].rsplit("/", 1)[0]}')


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
