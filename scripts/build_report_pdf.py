"""
Generate an interactive PDF of `src/technical_regulatory_report.md`.

Interactive features:
  - Clickable Table of Contents that jumps to each section
  - PDF outline / bookmarks panel (left sidebar in PDF readers)
  - Clickable URLs in references and inline links
  - Clean typography with tables, code blocks, headings

Pure-Python pipeline: markdown -> HTML -> xhtml2pdf -> PDF. No external
binaries (no LaTeX, no wkhtmltopdf, no Chromium).

Usage:
    python scripts/build_report_pdf.py
        # writes output/technical_regulatory_report.pdf
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import markdown
from xhtml2pdf import pisa


CSS = """
@page {
  size: A4;
  margin: 2.2cm 2cm;
}

body {
  font-family: 'Helvetica', 'Arial', sans-serif;
  font-size: 10pt;
  line-height: 1.55;
  color: #2c3e50;
}

h1 {
  font-size: 20pt;
  color: #2c3e50;
  border-bottom: 2pt solid #2c3e50;
  padding-bottom: 4pt;
  margin-top: 0;
  margin-bottom: 12pt;
}

h2 {
  font-size: 14pt;
  color: #34495e;
  border-left: 3pt solid #3498db;
  padding-left: 6pt;
  margin-top: 18pt;
  margin-bottom: 8pt;
  page-break-after: avoid;
}

h3 {
  font-size: 11pt;
  color: #34495e;
  margin-top: 12pt;
  margin-bottom: 4pt;
  page-break-after: avoid;
}

p { margin: 6pt 0; text-align: justify; }
strong { color: #2c3e50; }
em { color: #555; }

table {
  border-collapse: collapse;
  width: 100%;
  margin: 8pt 0;
  font-size: 9pt;
}
th {
  background: #ecf0f1;
  padding: 5pt 7pt;
  border: 1pt solid #bdc3c7;
  text-align: left;
  font-weight: bold;
}
td {
  padding: 4pt 7pt;
  border: 1pt solid #bdc3c7;
  vertical-align: top;
}

code {
  background: #f4f6f7;
  padding: 1pt 4pt;
  font-family: 'Courier New', monospace;
  font-size: 9pt;
  color: #c0392b;
  border-radius: 2pt;
}

pre {
  background: #f8f9fa;
  border-left: 3pt solid #95a5a6;
  padding: 8pt 10pt;
  font-family: 'Courier New', monospace;
  font-size: 8pt;
  line-height: 1.4;
  margin: 8pt 0;
  white-space: pre-wrap;
}
pre code {
  background: transparent;
  padding: 0;
  color: #2c3e50;
  font-size: 8pt;
}

a {
  color: #2980b9;
  text-decoration: underline;
}

ul, ol {
  margin: 6pt 0 6pt 16pt;
}
li { margin: 2pt 0; }

hr {
  border: none;
  border-top: 1pt solid #bdc3c7;
  margin: 14pt 0;
}

.toc {
  background: #f8f9fa;
  border: 1pt solid #bdc3c7;
  padding: 12pt 16pt;
  margin: 12pt 0 20pt 0;
  page-break-after: always;
}
.toc h2 {
  border: none;
  padding: 0;
  margin: 0 0 8pt 0;
  font-size: 14pt;
}
.toc ul {
  list-style: none;
  margin: 4pt 0;
  padding-left: 0;
}
.toc ul ul {
  padding-left: 14pt;
  font-size: 9.5pt;
}
.toc a {
  color: #2c3e50;
  text-decoration: none;
}
.toc li { margin: 3pt 0; }

.cover {
  text-align: center;
  margin: 60pt 0 40pt 0;
}
.cover h1 {
  font-size: 24pt;
  border: none;
  margin-bottom: 6pt;
}
.cover .subtitle {
  font-size: 12pt;
  color: #7f8c8d;
  font-style: italic;
}
.cover .meta {
  font-size: 10pt;
  color: #95a5a6;
  margin-top: 20pt;
}
"""

COVER_HTML = """
<div class="cover">
  <h1>OTC Derivatives Compliance Engine</h1>
  <div class="subtitle">Technical and Regulatory Report</div>
  <div class="meta">NTU MH6822 RegTech &mdash; Homework 2</div>
</div>
"""


# Heading anchor patterns produced by markdown's `toc` extension
# (header text "## 4. Module 4" becomes id="4-module-4")
def _wrap_html(body_html: str, toc_html: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        "<html>\n<head>\n"
        f"<meta charset='utf-8'/>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n<body>\n"
        f"{COVER_HTML}"
        f"<div class='toc'><h2>Table of Contents</h2>{toc_html}</div>\n"
        f"{body_html}\n"
        "</body>\n</html>"
    )


_HEADING_RE = re.compile(
    r'<h(?P<lvl>[1-6])\s+id="(?P<id>[^"]+)">(?P<rest>.*?)</h(?P=lvl)>',
    flags=re.DOTALL,
)


def _add_pdf_anchors(html: str) -> str:
    """
    Inject `<a name="...">` markers and `<pdf:outline>` tags around each
    heading. xhtml2pdf uses `name` attributes (not `id`) to resolve internal
    `<a href="#...">` links into clickable PDF link annotations, and uses
    `pdf:outline` tags to populate the PDF bookmarks panel.
    """
    def repl(m: re.Match) -> str:
        lvl = int(m.group("lvl"))
        anchor = m.group("id")
        rest = m.group("rest")
        # Strip any nested HTML in the heading text for the outline label.
        outline_label = re.sub(r"<[^>]+>", "", rest).strip()
        return (
            f'<a name="{anchor}"></a>'
            f'<h{lvl} id="{anchor}">'
            f'<pdf:outline name="{outline_label}" level="{lvl-1}">{rest}</pdf:outline>'
            f'</h{lvl}>'
        )

    return _HEADING_RE.sub(repl, html)


def build(src: Path, out: Path) -> None:
    md_text = src.read_text(encoding="utf-8")

    # Drop the H1 title from the markdown because the cover page already
    # carries it — keeps the body cleaner.
    md_text = re.sub(r"^# .+\n", "", md_text, count=1)

    md = markdown.Markdown(
        extensions=["extra", "tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={
            "toc": {"toc_depth": "2-3", "permalink": False},
        },
    )
    body_html = md.convert(md_text)
    toc_html = md.toc

    # Make internal links and PDF bookmarks work.
    body_html = _add_pdf_anchors(body_html)

    full_html = _wrap_html(body_html, toc_html)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        result = pisa.CreatePDF(full_html, dest=f, encoding="utf-8")

    if result.err:
        raise RuntimeError(f"PDF generation failed with {result.err} errors")

    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build an interactive PDF of the report")
    ap.add_argument("--input", default="src/technical_regulatory_report.md")
    ap.add_argument("--output", default="output/technical_regulatory_report.pdf")
    args = ap.parse_args(argv)

    build(Path(args.input), Path(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
