"""
Generate a Word document (.docx) of `src/technical_regulatory_report.md`.

Uses pandoc (bundled via `pypandoc-binary`) to convert the Markdown
source into a styled .docx with:
  - Heading styles (Heading 1 / 2 / 3) that Word will treat as navigation
    points
  - A clickable Table of Contents at the top
  - Markdown tables rendered as Word tables
  - Inline code and fenced code blocks rendered in monospace
  - External URLs in the References block as clickable hyperlinks

Usage:
    python scripts/build_report_docx.py
        # writes output/technical_regulatory_report.docx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pypandoc


def build(src: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)

    extra_args = [
        "--standalone",
        "--toc",
        "--toc-depth=3",
        "--from=markdown+pipe_tables+fenced_code_blocks+autolink_bare_uris",
    ]

    pypandoc.convert_file(
        source_file=str(src),
        to="docx",
        outputfile=str(out),
        extra_args=extra_args,
    )

    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build a Word document of the report")
    ap.add_argument("--input", default="src/technical_regulatory_report.md")
    ap.add_argument("--output", default="output/technical_regulatory_report.docx")
    args = ap.parse_args(argv)

    build(Path(args.input), Path(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
