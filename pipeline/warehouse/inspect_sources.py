"""Development tool: download unfamiliar source files and write a text preview to a
local folder, so parsers are written against real layouts rather than guesses.
Nothing is written to the database (the warehouse keeps numbers only).

    python3 -m pipeline.warehouse.inspect_sources [--out inspect_out]   # uses catalog/inspect_urls.txt

Line format: ``name url [FOLLOW "link text" | FOLLOWAFTER "marker" | RAW "marker"]``.
FOLLOW opens the first link whose text contains the words; FOLLOWAFTER opens the first
link after the marker in the raw HTML; RAW stores raw HTML around the marker.
``{BEA_API_KEY}``-style placeholders in a URL are filled from the environment for the
request only: the stored URL keeps the placeholder and key values are masked in previews.
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .providers.documents import BROWSER_UA, html_text, pdf_pages

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
        links = anchors(text)
        text, _ = html_text(body)
        text += "\n\nLINKS:\n" + "\n".join(f"{h} | {t}" for h, t in links[:300])
    return [text[:MAX_CHARS]]


def excel_preview(body: bytes) -> list[str]:
    pages = []
    sheets = pd.read_excel(io.BytesIO(body), sheet_name=None, header=None)
    for name, frame in list(sheets.items())[:12]:
        pages.append(f"[sheet {name}] shape={frame.shape}\n" + frame.head(80).to_csv(index=False)[:MAX_CHARS])
    return pages


def anchors(html: str) -> list[tuple[str, str]]:
    """(href, text) for every <a> in a page."""
    import re

    out = []
    for m in re.finditer(r"<a\b[^>]*href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", html, flags=re.S | re.I):
        text = re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()
        out.append((m.group(1), text))
    return out


def fill_secrets(url: str, env) -> str:
    """Replace {NAME} placeholders whose NAME is an *_API_KEY variable in ``env``."""
    for k, v in env.items():
        if k.endswith("_API_KEY") and v:
            url = url.replace("{" + k + "}", v)
    return url


def mask_secrets(text: str, env) -> str:
    for k, v in env.items():
        if k.endswith("_API_KEY") and v and len(v) >= 6:
            text = text.replace(v, "***")
    return text


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("inspect_out"))
    parser.add_argument("--log-chars", type=int, default=0, help="also print the first N characters of each preview")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    annotated = 0
    session = requests.Session()
    today = datetime.now(timezone.utc).date()
    for line in URLS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, rest = line.split(None, 1)
        url, mode, arg = rest.strip(), "", ""
        for keyword in (" FOLLOWAFTER ", " FOLLOW ", " RAW "):
            if keyword in rest:
                url, arg = (x.strip() for x in rest.split(keyword, 1))
                mode, arg = keyword.strip(), arg.strip('"')
                break
        try:
            if mode in ("FOLLOW", "FOLLOWAFTER"):
                from urllib.parse import urljoin
                import re

                listing = session.get(url, timeout=(15, 60), headers={"User-Agent": BROWSER_UA})
                if mode == "FOLLOW":
                    hit = next((h for h, t in anchors(listing.text) if arg in t), None)
                else:  # first link after the first occurrence of the marker text in the raw HTML
                    at = listing.text.find(arg.replace("&", "&amp;"))
                    at = listing.text.find(arg) if at < 0 else at
                    m = re.search(r"<a\b[^>]*href=[\"']([^\"'#]+)[\"']", listing.text[at:]) if at >= 0 else None
                    hit = m.group(1) if m else None
                if hit is None:
                    raise RuntimeError(f"no link for {arg!r} on {url}")
                url = urljoin(listing.url, hit)
            r = session.get(fill_secrets(url, os.environ), timeout=(15, 120), headers={"User-Agent": BROWSER_UA, "Accept": "*/*"})
            pages = [f"HTTP {r.status_code} {r.headers.get('Content-Type')} {len(r.content)} bytes\n{mask_secrets(r.url, os.environ)}"]
            if r.status_code == 200 and mode == "RAW":
                raw = r.text
                at = max(raw.find(arg.replace("&", "&amp;")), raw.find(arg))
                pages.append(raw[max(0, at - 3000): at + 12000] if at >= 0 else "marker not found\n" + raw[:15000])
            elif r.status_code == 200:
                pages += preview(r.content, url)
        except Exception as error:  # noqa: BLE001
            pages = [f"ERROR {type(error).__name__}: {error}"]
        pages = [mask_secrets(p, os.environ) for p in pages]
        target = args.out / f"{today:%Y%m%d}-{name}.txt"
        target.write_text(f"{url}\n\n" + "\n\n==== page break ====\n\n".join(pages), encoding="utf-8")
        print(f"{name}: {pages[0][:120]} -> {target}")
        if args.log_chars:  # CI has no local folder to read back: show the start of each preview
            text = "\n".join(p[:args.log_chars] for p in pages[:4])
            if os.environ.get("GITHUB_ACTIONS"):
                # annotations are readable through the REST API; GitHub keeps 10 per type per step
                kind = ("notice", "warning", "error")[min(annotated // 10, 2)]
                annotated += 1
                print(f"::{kind} title=inspect {name}::{annotation_escape(text)}")
            else:
                print(text + f"\n==== end {name} ====")
    return 0


def annotation_escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


if __name__ == "__main__":
    raise SystemExit(main())
