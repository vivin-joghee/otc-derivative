"""
Module 5: Compliance Dashboard (Flask).

Loads `output/compliance_report.json` (Module 3) plus `data/trades.json`
(for asset-class and platform metadata) and renders four required charts:

  1. Portfolio compliance heatmap (28 trades x 2 regimes)
  2. Field-level failure-frequency horizontal bar chart
  3. Asset-class status breakdown, side-by-side per regime
  4. Classification frontier panel for the three NOVEL trades (T026-T028)

Run with `python src/dashboard.py` to start the Flask dev server, or with
`--snapshot output/dashboard.html` to render once and exit (useful for
committing a static copy).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from flask import Flask, render_template
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots


# Compliance status palette (green / red / amber / gray).
STATUS_COLORS: dict[str, str] = {
    "COMPLIANT":      "#2ECC71",
    "NONCOMPLIANT":   "#E74C3C",
    "CONDITIONAL":    "#F39C12",
    "NOT_APPLICABLE": "#95A5A6",
}
STATUS_ORDER: list[str] = ["COMPLIANT", "NONCOMPLIANT", "CONDITIONAL", "NOT_APPLICABLE"]
STATUS_TO_INT: dict[str, int] = {s: i for i, s in enumerate(STATUS_ORDER)}


# --- data loading -------------------------------------------------------

def load_data(report_path: str | Path, trades_path: str | Path) -> list[dict]:
    """Merge compliance report rows with raw-trade metadata (asset_class etc.)."""
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    trades = json.loads(Path(trades_path).read_text(encoding="utf-8"))
    trades_by_id = {t["trade_id"]: t for t in trades if isinstance(t, dict)}

    enriched: list[dict] = []
    for r in report:
        raw = trades_by_id.get(r["trade_id"], {})
        enriched.append({
            **r,
            "asset_class": raw.get("asset_class"),
            "instrument_type": raw.get("instrument_type"),
            "use_case": raw.get("use_case"),
            "platform": raw.get("platform"),
            "platform_type": raw.get("platform_type"),
            "description": raw.get("description"),
        })
    return enriched


# --- chart 1: heatmap ---------------------------------------------------

def _discrete_colorscale(n: int) -> list[list]:
    """Build a step-colorscale that maps integer values 0..n-1 to STATUS_COLORS."""
    out: list[list] = []
    for i, status in enumerate(STATUS_ORDER[:n]):
        color = STATUS_COLORS[status]
        # Two stops at each step produce sharp boundaries (no gradient).
        out.append([i / n,                  color])
        out.append([(i + 1) / n - 1e-6,     color])
    return out


def build_heatmap(enriched: list[dict]) -> go.Figure:
    regimes = ["CFTC", "MAS"]
    trade_ids = [r["trade_id"] for r in enriched]

    z: list[list[int]] = []
    cell_text: list[list[str]] = []
    hover: list[list[str]] = []

    for r in enriched:
        z_row, t_row, h_row = [], [], []
        for regime in regimes:
            block = r["regimes"][regime]
            status = block["status"]
            z_row.append(STATUS_TO_INT[status])
            t_row.append(status)
            failed = [
                fname for fname, fv in block["field_validations"].items()
                if not fv["valid"]
            ]
            tip = f"<b>{r['trade_id']} / {regime}</b><br>Status: <b>{status}</b>"
            if failed:
                tip += "<br>Failed fields: " + ", ".join(failed)
            note = block.get("applicability_note")
            if note:
                tip += f"<br><i>{note[:140]}{'...' if len(note) > 140 else ''}</i>"
            h_row.append(tip)
        z.append(z_row)
        cell_text.append(t_row)
        hover.append(h_row)

    n = len(STATUS_ORDER)
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=regimes,
        y=trade_ids,
        text=cell_text,
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertext=hover,
        hovertemplate="%{hovertext}<extra></extra>",
        colorscale=_discrete_colorscale(n),
        zmin=0,
        zmax=n - 1,
        showscale=False,
        xgap=2,
        ygap=2,
    ))
    fig.update_layout(
        title="Portfolio Compliance Heatmap",
        xaxis_title="Regime",
        yaxis_title="Trade ID",
        yaxis=dict(autorange="reversed"),  # T001 at top
        height=900,
        plot_bgcolor="white",
        margin=dict(l=80, r=40, t=60, b=60),
    )
    return fig


# --- chart 2: error frequency -------------------------------------------

def build_error_frequency(enriched: list[dict]) -> go.Figure | None:
    counter: Counter = Counter()
    for r in enriched:
        for regime in ("CFTC", "MAS"):
            for fname, fv in r["regimes"][regime]["field_validations"].items():
                if not fv["valid"]:
                    counter[fname] += 1
    if not counter:
        return None

    items = sorted(counter.items(), key=lambda kv: kv[1])  # ascending => largest at top
    fields = [k for k, _ in items]
    counts = [v for _, v in items]

    fig = go.Figure(data=go.Bar(
        x=counts,
        y=fields,
        orientation="h",
        marker=dict(color=STATUS_COLORS["NONCOMPLIANT"]),
        text=counts,
        textposition="outside",
        hovertemplate="%{y}: %{x} failures<extra></extra>",
    ))
    fig.update_layout(
        title="Field-Level Failure Frequency (28 trades x 2 regimes)",
        xaxis_title="Number of failures",
        yaxis_title="",
        height=520,
        plot_bgcolor="white",
        margin=dict(l=200, r=60, t=60, b=60),
    )
    return fig


# --- chart 3: asset class breakdown -------------------------------------

def build_asset_class(enriched: list[dict]) -> go.Figure:
    counts: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for r in enriched:
        ac = r.get("asset_class") or "Unknown"
        for regime in ("CFTC", "MAS"):
            counts[ac][regime][r["regimes"][regime]["status"]] += 1

    asset_classes = sorted(counts.keys())

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("CFTC", "MAS"),
        shared_yaxes=True,
        horizontal_spacing=0.08,
    )

    for col, regime in enumerate(("CFTC", "MAS"), start=1):
        for status in STATUS_ORDER:
            ys = [counts[ac][regime][status] for ac in asset_classes]
            if not any(ys):
                continue
            fig.add_trace(
                go.Bar(
                    name=status,
                    x=asset_classes,
                    y=ys,
                    marker_color=STATUS_COLORS[status],
                    legendgroup=status,
                    showlegend=(col == 1),
                    hovertemplate=(
                        f"%{{x}} ({regime})<br>{status}: %{{y}} trade(s)<extra></extra>"
                    ),
                ),
                row=1, col=col,
            )

    fig.update_layout(
        barmode="stack",
        title="Asset Class Status Breakdown",
        height=460,
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        margin=dict(l=60, r=40, t=80, b=80),
    )
    fig.update_yaxes(title_text="Trade count", row=1, col=1)
    return fig


# --- summary + novel panel ----------------------------------------------

def build_summary(enriched: list[dict]) -> dict[str, Any]:
    cftc = Counter(r["regimes"]["CFTC"]["status"] for r in enriched)
    mas = Counter(r["regimes"]["MAS"]["status"] for r in enriched)
    return {"total": len(enriched), "cftc": dict(cftc), "mas": dict(mas)}


def build_novel_panel(enriched: list[dict]) -> list[dict]:
    return [
        {
            "trade_id": r["trade_id"],
            "platform": r.get("platform") or "—",
            "platform_type": r.get("platform_type") or "—",
            "cftc_status": r["regimes"]["CFTC"]["status"],
            "mas_status": r["regimes"]["MAS"]["status"],
            "description": r.get("description") or "",
        }
        for r in enriched
        if r["classification_flag"] == "NOVEL_INSTRUMENT_NO_TAXONOMY"
    ]


# --- Flask app ----------------------------------------------------------

app = Flask(__name__, template_folder=str(Path(__file__).resolve().parent / "templates"))


def _config_paths(report: str = "output/compliance_report.json",
                  trades: str = "data/trades.json") -> None:
    app.config["REPORT_PATH"] = report
    app.config["TRADES_PATH"] = trades


def _load_for_request() -> list[dict]:
    return load_data(
        app.config.get("REPORT_PATH", "output/compliance_report.json"),
        app.config.get("TRADES_PATH", "data/trades.json"),
    )


@app.route("/")
def dashboard():
    enriched = _load_for_request()
    figs = {
        "heatmap": build_heatmap(enriched),
        "errors": build_error_frequency(enriched),
        "asset_class": build_asset_class(enriched),
    }
    figs_html = {
        k: pio.to_html(v, include_plotlyjs=False, full_html=False, div_id=f"chart-{k}")
        for k, v in figs.items() if v is not None
    }
    return render_template(
        "dashboard.html",
        figures=figs_html,
        summary=build_summary(enriched),
        novel=build_novel_panel(enriched),
        status_order=STATUS_ORDER,
    )


# --- CLI ----------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Module 5: compliance dashboard (Flask)")
    ap.add_argument("--report", default="output/compliance_report.json")
    ap.add_argument("--trades", default="data/trades.json")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument(
        "--snapshot",
        help="Render the dashboard once to this path and exit (no server).",
    )
    args = ap.parse_args(argv)

    _config_paths(args.report, args.trades)

    if args.snapshot:
        with app.test_client() as client:
            resp = client.get("/")
            out = Path(args.snapshot)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(resp.get_data(as_text=True), encoding="utf-8")
            print(f"Snapshot written to {out}")
        return 0

    print(f"Compliance dashboard at http://{args.host}:{args.port}/")
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
