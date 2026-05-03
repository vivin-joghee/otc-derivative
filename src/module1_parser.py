"""
Module 1: Trade Parser and Instrument Classifier.

Reads `trades.json` and produces one structured `ParsedTrade` per record
containing the asset class, instrument type, use case, classification flag,
collected parse errors, and a small set of universally relevant fields lifted
into `classified_fields` for downstream modules (UPI lookup, compliance check).

Per the assignment, the parser must never crash on malformed input — every
trade must yield an output record regardless of data quality.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ANNA-DSB UPI library covers exactly these five OTC asset classes.
CONVENTIONAL_ASSET_CLASSES: frozenset[str] = frozenset(
    {"Rates", "Credit", "FX", "Equity", "Commodities"}
)

# Asset classes deliberately outside the ANNA-DSB taxonomy (prediction / event
# contracts). Listed explicitly so that an unknown asset class still falls
# through to CLASSIFICATION_AMBIGUOUS rather than being silently labelled novel.
NOVEL_ASSET_CLASSES: frozenset[str] = frozenset({"EventContract"})


# Strict ISO 8601 UTC instant: YYYY-MM-DDTHH:MM:SS[.fff]Z
_ISO8601_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


def _is_valid_iso_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not _ISO8601_UTC_RE.match(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _is_valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


@dataclass
class ParsedTrade:
    trade_id: str | None
    parse_status: str  # SUCCESS | PARTIAL | FAILED
    asset_class: str | None
    instrument_type: str | None
    use_case: str | None
    classification_flag: str
    parse_errors: list[str] = field(default_factory=list)
    classified_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_instrument(trade: dict) -> str:
    """
    Determine the regulatory taxonomy classification flag for a trade.
    Returns: CONVENTIONAL_DERIVATIVE | NOVEL_INSTRUMENT_NO_TAXONOMY | CLASSIFICATION_AMBIGUOUS
    """
    asset_class = trade.get("asset_class")
    if not isinstance(asset_class, str) or not asset_class.strip():
        return "CLASSIFICATION_AMBIGUOUS"
    if asset_class in CONVENTIONAL_ASSET_CLASSES:
        return "CONVENTIONAL_DERIVATIVE"
    if asset_class in NOVEL_ASSET_CLASSES:
        return "NOVEL_INSTRUMENT_NO_TAXONOMY"
    return "CLASSIFICATION_AMBIGUOUS"


def parse_trade(trade: dict) -> ParsedTrade:
    """
    Parse a single raw trade dict into a ParsedTrade record.
    Never raises — malformed input is captured in `parse_errors`.
    """
    if not isinstance(trade, dict):
        return ParsedTrade(
            trade_id=None,
            parse_status="FAILED",
            asset_class=None,
            instrument_type=None,
            use_case=None,
            classification_flag="CLASSIFICATION_AMBIGUOUS",
            parse_errors=["trade record is not a JSON object"],
        )

    errors: list[str] = []

    trade_id_raw = trade.get("trade_id")
    trade_id = trade_id_raw if isinstance(trade_id_raw, str) and trade_id_raw.strip() else None
    if trade_id is None:
        errors.append("missing or invalid field: trade_id")

    # Step 1: extract taxonomic fields ---------------------------------------
    asset_class = trade.get("asset_class")
    instrument_type = trade.get("instrument_type")
    use_case = trade.get("use_case")

    for name, value in (
        ("asset_class", asset_class),
        ("instrument_type", instrument_type),
        ("use_case", use_case),
    ):
        if value is None:
            errors.append(f"missing field: {name}")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"invalid field: {name} is not a non-empty string")

    # Step 2: classification flag --------------------------------------------
    classification_flag = classify_instrument(trade)
    if classification_flag == "CLASSIFICATION_AMBIGUOUS" and isinstance(asset_class, str):
        if asset_class.strip() and asset_class not in CONVENTIONAL_ASSET_CLASSES \
                and asset_class not in NOVEL_ASSET_CLASSES:
            errors.append(
                f"unknown asset_class {asset_class!r} — outside ANNA-DSB library "
                f"and not a recognised novel-instrument class"
            )

    is_novel = classification_flag == "NOVEL_INSTRUMENT_NO_TAXONOMY"

    # Step 3: execution_timestamp (ISO 8601 UTC) -----------------------------
    exec_ts = trade.get("execution_timestamp")
    if exec_ts is None:
        errors.append("missing field: execution_timestamp")
    elif not _is_valid_iso_utc_timestamp(exec_ts):
        errors.append(
            f"invalid execution_timestamp: {exec_ts!r} is not ISO 8601 UTC "
            f"(expected YYYY-MM-DDTHH:MM:SSZ)"
        )

    # Step 4: effective_date and maturity_date -------------------------------
    # Event contracts legitimately omit effective_date / maturity_date and use
    # `settlement_date` instead — don't penalise them for the absence.
    eff_date = trade.get("effective_date")
    if eff_date is None:
        if not is_novel:
            errors.append("missing field: effective_date")
    elif not _is_valid_iso_date(eff_date):
        errors.append(
            f"invalid effective_date: {eff_date!r} is not a valid YYYY-MM-DD date"
        )

    mat_date = trade.get("maturity_date")
    if mat_date is None:
        if not is_novel and not trade.get("settlement_date"):
            errors.append("missing field: maturity_date")
    elif not _is_valid_iso_date(mat_date):
        errors.append(
            f"invalid maturity_date: {mat_date!r} is not a valid YYYY-MM-DD date"
        )

    # Step 5: parse_status ---------------------------------------------------
    if classification_flag == "CLASSIFICATION_AMBIGUOUS":
        parse_status = "FAILED"
    elif errors:
        parse_status = "PARTIAL"
    else:
        parse_status = "SUCCESS"

    classified_fields: dict[str, Any] = {
        "notional_currency": trade.get("notional_currency"),
        "notional_amount": trade.get("notional_amount"),
        "cleared": trade.get("cleared"),
        "uti": trade.get("uti"),
    }

    return ParsedTrade(
        trade_id=trade_id,
        parse_status=parse_status,
        asset_class=asset_class if isinstance(asset_class, str) else None,
        instrument_type=instrument_type if isinstance(instrument_type, str) else None,
        use_case=use_case if isinstance(use_case, str) else None,
        classification_flag=classification_flag,
        parse_errors=errors,
        classified_fields=classified_fields,
    )


def parse_trades_file(path: str | Path) -> list[ParsedTrade]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: top-level JSON must be an array of trades")
    return [parse_trade(t) for t in raw]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Module 1: parse trades.json")
    ap.add_argument("--input", default="data/trades.json")
    ap.add_argument("--output", default="output/parsed_trades.json")
    args = ap.parse_args(argv)

    parsed = parse_trades_file(args.input)
    out = [p.to_dict() for p in parsed]

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")

    by_status: dict[str, int] = {}
    by_flag: dict[str, int] = {}
    for p in parsed:
        by_status[p.parse_status] = by_status.get(p.parse_status, 0) + 1
        by_flag[p.classification_flag] = by_flag.get(p.classification_flag, 0) + 1

    print(f"Parsed {len(parsed)} trades -> {args.output}")
    print(f"  parse_status:        {by_status}")
    print(f"  classification_flag: {by_flag}")
    for p in parsed:
        if p.parse_errors:
            print(f"  - {p.trade_id}: {p.parse_status}  errors={p.parse_errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
