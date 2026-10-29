"""Draw an issue spec with the design system's own components in headless Chromium.

The page is the Richard Wei Finance component bundle (ds/components.js, vendored with a
CJK text-width patch) plus ds/issue.js, which packs bands onto A4 pages. Output: an A4 PDF
with embedded fonts, and one PNG per chart block (title, chart and source line).
"""
import json
from pathlib import Path
import tempfile

DS = Path(__file__).with_name('ds')
FONTS = Path(__file__).parent / 'assets' / 'fonts'
FACES = [('Public Sans', 400, 'PublicSans-Regular.ttf'), ('Public Sans', 700, 'PublicSans-Bold.ttf'),
         ('Newsreader', 400, 'Newsreader-Regular.ttf'), ('Newsreader', 700, 'Newsreader-Bold.ttf'),
         ('Noto Sans SC', 400, 'NotoSansSC-Regular.ttf'), ('Noto Sans SC', 700, 'NotoSansSC-Bold.ttf'),
         ('Noto Serif SC', 400, 'NotoSerifSC-Regular.ttf'), ('Noto Serif SC', 700, 'NotoSerifSC-Bold.ttf')]
SCRIPTS = ['react.production.min.js', 'react-dom.production.min.js', 'components.js', 'issue.js']

PAGE_CSS = """
html, body { margin: 0; padding: 0; background: #fff; }
#issue { width: 794px; }
.rwf-page { box-shadow: none; }
.rwf-page + .rwf-page { margin-top: 0; }
.mw-probe { position: absolute; left: -20000px; top: 0; width: 696px; }
.mw-pair { display: grid; grid-template-columns: 1fr 1fr; column-gap: 24px; }
.mw-col > * + *:not(.rwf-para) { margin-top: 12px; }
.mw-group > .rwf-section-title { margin-top: 2px; }
.mw-group > [data-chart], .mw-group > .mw-pair { margin-top: 4px; }
.mw-group > .rwf-warning { margin-top: 14px; }
.mw-keyfigs { display: grid; row-gap: 10px; }
.mw-keyfigs .rwf-keyfig-label { margin-top: 1px; }
@page { size: A4; margin: 0; }
@media print { .rwf-page { break-after: page; } .rwf-page:last-child { break-after: auto; } }
"""


def font_css():
    rules = []
    for family, weight, name in FACES:
        path = FONTS / name
        if not path.exists():
            raise ValueError(f'缺少字体：{path}')
        rules.append(f'@font-face {{ font-family: "{family}"; font-weight: {weight}; font-style: normal; '
                     f'src: url("{path.resolve().as_uri()}") format("truetype"); }}')
    return '\n'.join(rules)


def build_html(spec):
    data = json.dumps(spec, ensure_ascii=False).replace('</', '<\\/')
    css = '\n'.join([font_css(), (DS / 'tokens.css').read_text(encoding='utf-8'),
                     (DS / 'components.css').read_text(encoding='utf-8'), PAGE_CSS])
    scripts = ''.join(f'<script src="{(DS / name).resolve().as_uri()}"></script>' for name in SCRIPTS)
    loads = json.dumps([f'{weight} 16px "{family}"' for family, weight, _ in FACES])
    return f"""<!doctype html>
<html lang="{spec.get('lang', 'zh')}"><head><meta charset="utf-8"><title>{spec.get('series', '')}</title>
<style>{css}</style>{scripts}</head>
<body><div id="issue" class="rwf"></div>
<script>window.ISSUE = {data};
window.addEventListener('error', function (e) {{ window.ISSUE_ERROR = String(e.message || e); }});
Promise.all({loads}.map(function (f) {{ return document.fonts.load(f, 'Aa1中'); }}))
  .then(function () {{ return document.fonts.ready; }})
  .then(function () {{ try {{ window.renderIssue(); }} catch (e) {{ window.ISSUE_ERROR = String(e && e.stack || e); }} }});
</script></body></html>"""


def render(spec, pdf_path, png_dir=None, scale=3):
    """Lay out and print the issue; returns the layout report (pages, charts, overflow, plan)."""
    from playwright.sync_api import sync_playwright
    pdf_path = Path(pdf_path)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        page_file = Path(tmp) / 'issue.html'
        page_file.write_text(build_html(spec), encoding='utf-8')
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 794, 'height': 1123}, device_scale_factor=scale)
            page.goto(page_file.as_uri())
            page.wait_for_function('window.ISSUE_REPORT || window.ISSUE_ERROR', timeout=120000)
            error = page.evaluate('window.ISSUE_ERROR || null')
            if error:
                raise ValueError(f'排版失败：{error}')
            report = page.evaluate('window.ISSUE_REPORT')
            if png_dir is not None:
                png_dir = Path(png_dir)
                png_dir.mkdir(parents=True, exist_ok=True)
                for key in report['charts']:
                    page.locator(f'[data-chart="{key}"]').first.screenshot(path=str(png_dir / f'{key}.png'))
            page.emulate_media(media='print')
            page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True,
                     tagged=True, outline=False)
        finally:
            browser.close()
    return report
