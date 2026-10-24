"""Download unfamiliar source files and store a text preview (private table),
so parsers are written against real layouts rather than guesses.

    python3 -m pipeline.warehouse.inspect_sources        # uses catalog/inspect_urls.txt
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .db.store import open_store
from .providers.reports import BROWSER_UA, html_text, pdf_pages

URLS = Path(__file__).with_name("catalog") / "inspect_urls.txt"
MAX_CHARS = 60_000


def preview(body: bytes, url: str) -> list[str]:
    head = body[:8]
    if head.startswith(b"%PDF"):
        return [p[:MAX_CHARS] for p in pdf_pages(body)[:12]]
    if head.startswith(b"PK"):
        pages = []
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            names = zf.namelist()
            pages.append("ZIP members:\n" + "\n".join(names[:200]))
            for name in names[:6]:
                pages.extend(f"[{name}]\n{p}" for p in preview(zf.read(name), name)[:4])
        if any(n.startswith("xl/") for n in names):  # it was an xlsx
            return excel_preview(body)
        return pages
    if head.startswith(b"\xd0\xcf\x11\xe0"):  # legacy xls
        return excel_preview(body)
    for enc in ("utf-8", "cp932", "latin-1"):
        try:
            text = body.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if "<html" in text[:2000].lower() or "<!doctype" in text[:200].lower():
        text, links = html_text(body)
        text += "\n\nLINKS:\n" + "\n".join(links[:100])
    return [text[:MAX_CHARS]]


def excel_preview(body: bytes) -> list[str]:
    pages = []
    sheets = pd.read_excel(io.BytesIO(body), sheet_name=None, header=None)
    for name, frame in list(sheets.items())[:12]:
        pages.append(f"[sheet {name}] shape={frame.shape}\n" + frame.head(80).to_csv(index=False)[:MAX_CHARS])
    return pages


def main() -> int:
    import os

    store = open_store(os.environ.get("WAREHOUSE_DB_URL"))
    session = requests.Session()
    today = datetime.now(timezone.utc).date()
    for line in URLS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, url = line.split(None, 1)
        try:
            r = session.get(url, timeout=(15, 120), headers={"User-Agent": BROWSER_UA, "Accept": "*/*"})
            pages = [f"HTTP {r.status_code} {r.headers.get('Content-Type')} {len(r.content)} bytes\n{r.url}"]
            if r.status_code == 200:
                pages += preview(r.content, url)
        except Exception as error:  # noqa: BLE001
            pages = [f"ERROR {type(error).__name__}: {error}"]
        store.upsert_report_pages(f"INSPECT:{name}", today, url, pages)
        print(f"{name}: {pages[0][:120]}")
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
