"""
Render the Flask dashboard HTML to PDF.

Because the dashboard uses Plotly (JavaScript-rendered SVG/canvas), a static
HTML-to-PDF converter (xhtml2pdf, weasyprint) cannot reproduce the charts.
We drive Microsoft Edge in headless mode instead — it executes the Plotly
JS, then writes the rendered page to PDF.

Usage:
    python scripts/build_dashboard_pdf.py
        # renders both dashboard.html (28-trade) and dashboard_all.html (34-trade)
        # to PDFs in output/

    python scripts/build_dashboard_pdf.py --input output/dashboard_all.html --output output/dashboard_all.pdf
        # render one specific file

Requires Microsoft Edge installed at one of the standard paths on Windows.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


EDGE_PATHS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


def _find_browser() -> str:
    for p in EDGE_PATHS + CHROME_PATHS:
        if Path(p).exists():
            return p
    on_path = shutil.which("msedge") or shutil.which("chrome")
    if on_path:
        return on_path
    raise RuntimeError(
        "Could not locate Microsoft Edge or Google Chrome. "
        "Install one of them, or pass --browser <path-to-msedge.exe>."
    )


def _to_file_url(path: Path) -> str:
    abs_path = path.resolve()
    return abs_path.as_uri()


def render(html: Path, pdf: Path, browser: str, wait_ms: int = 10_000) -> None:
    pdf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--virtual-time-budget={wait_ms}",
        f"--print-to-pdf={pdf.resolve()}",
        _to_file_url(html),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        # Edge prints noise to stderr even on success; only surface it if RC != 0
        raise RuntimeError(
            f"Edge headless exited {result.returncode}\n"
            f"stderr: {result.stderr[-2000:]}"
        )
    if not pdf.exists() or pdf.stat().st_size == 0:
        raise RuntimeError(f"PDF was not written to {pdf}")
    print(f"  rendered {html.name} -> {pdf} ({pdf.stat().st_size:,} bytes)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render the dashboard HTML to PDF")
    ap.add_argument("--input", help="Single HTML file to render")
    ap.add_argument("--output", help="Single output PDF path")
    ap.add_argument(
        "--browser",
        help="Path to msedge.exe or chrome.exe (default: auto-detected)",
    )
    ap.add_argument(
        "--wait-ms",
        type=int,
        default=10_000,
        help="Virtual-time budget in ms for Plotly to finish rendering (default: 10000)",
    )
    args = ap.parse_args(argv)

    browser = args.browser or _find_browser()
    print(f"Using browser: {browser}")

    if args.input or args.output:
        if not (args.input and args.output):
            ap.error("--input and --output must both be provided when rendering one file")
        render(Path(args.input), Path(args.output), browser, args.wait_ms)
        return 0

    # Default: render both 28-trade and 34-trade dashboards
    pairs = [
        (Path("output/dashboard.html"),     Path("output/dashboard.pdf")),
        (Path("output/dashboard_all.html"), Path("output/dashboard_all.pdf")),
    ]
    for html, pdf in pairs:
        if not html.exists():
            print(f"  skip {html} — does not exist")
            continue
        render(html, pdf, browser, args.wait_ms)

    return 0


if __name__ == "__main__":
    sys.exit(main())
