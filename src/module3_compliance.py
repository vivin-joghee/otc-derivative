"""
Module 3: Multi-Jurisdictional Compliance Checker.

For every trade, evaluates compliance under CFTC and MAS:
  - validates LEIs (ISO 7064 MOD 97-10) and UTI (ISO 23897)
  - checks each regime's required-field set is present and well-formed
  - applies the jurisdictional asymmetry rule for prediction contracts
    (T026-T028): CFTC-regulated DCM -> CONDITIONAL; offshore -> NOT_APPLICABLE
    on CFTC; MAS treats event contracts as out-of-scope -> NOT_APPLICABLE.

Output: output/compliance_report.json with one nested record per trade.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pycountry
from stdnum import lei as stdnum_lei
from stdnum.exceptions import ValidationError as StdnumValidationError

# Allow `from module1_parser import ...` whether run as a script or imported.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from module1_parser import ParsedTrade, parse_trades_file  # noqa: E402


# --- constants ----------------------------------------------------------

# Per the brief: "NEW, MODIFY, etc." — accept the common Reg-45 / EMIR action types.
ACTION_TYPE_VALUES: frozenset[str] = frozenset(
    {"NEW", "MODIFY", "CANCEL", "CORRECT", "TERMINATE", "REVIVE"}
)

CFTC_REQUIRED_FIELDS: tuple[str, ...] = (
    "uti", "upi", "reporting_counterparty_lei", "other_counterparty_lei",
    "execution_timestamp", "effective_date", "maturity_date",
    "notional_currency", "notional_amount", "action_type", "cleared",
)

MAS_REQUIRED_FIELDS: tuple[str, ...] = CFTC_REQUIRED_FIELDS + (
    "collateral_portfolio_code", "initial_margin_posted", "variation_margin_posted",
)

_ISO8601_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LEI_FORMAT_RE = re.compile(r"^[A-Z0-9]{20}$")  # syntactic shape only
_UTI_NAMESPACE_RE = re.compile(r"^[A-Z0-9]{20}$")
_UTI_SUFFIX_RE = re.compile(r"^[A-Z0-9-]*$")


# --- LEI -----------------------------------------------------------------

def compute_lei_check_digits(body: str) -> str:
    """
    ISO 7064 MOD 97-10 check digits for an LEI body (18 chars). Returns a
    two-character zero-padded string. Kept for educational transparency
    alongside the stdnum-based validate_lei() below.
    """
    numeric_chars: list[str] = []
    for c in body:
        if c.isdigit():
            numeric_chars.append(c)
        elif "A" <= c <= "Z":
            numeric_chars.append(str(ord(c) - ord("A") + 10))
        else:
            raise ValueError(f"invalid LEI body character: {c!r}")
    numeric_chars.append("00")
    n = int("".join(numeric_chars))
    return f"{98 - (n % 97):02d}"


def validate_lei(lei: Optional[str]) -> tuple[bool, str]:
    """
    Validate a 20-char LEI per ISO 17442 + ISO 7064 MOD 97-10 checksum.
    Returns (is_valid, error_message). Empty error when valid.
    Uses python-stdnum for the canonical implementation.
    """
    if lei is None:
        return False, "missing"
    if not isinstance(lei, str):
        return False, f"expected string, got {type(lei).__name__}"
    try:
        stdnum_lei.validate(lei)
        return True, ""
    except StdnumValidationError as exc:
        return False, f"{type(exc).__name__}: {exc}"


# --- UTI -----------------------------------------------------------------

def validate_uti(uti: Optional[str], reporting_lei: Optional[str]) -> tuple[bool, str]:
    """
    ISO 23897 UTI:
      - total length <= 52
      - first 20 chars are a syntactically valid LEI shape
      - first 20 chars equal the reporting counterparty's LEI
      - suffix (chars 21+) contains only [A-Z0-9-]
    """
    if uti is None:
        return False, "missing"
    if not isinstance(uti, str):
        return False, f"expected string, got {type(uti).__name__}"
    if len(uti) > 52:
        return False, f"length {len(uti)} > 52 (ISO 23897 max)"
    if len(uti) < 20:
        return False, f"length {len(uti)} < 20 (must contain namespace LEI)"
    namespace = uti[:20]
    if not _UTI_NAMESPACE_RE.match(namespace):
        return False, f"namespace {namespace!r} is not 20 alphanumeric uppercase chars"
    if isinstance(reporting_lei, str) and namespace != reporting_lei:
        return False, (
            f"namespace {namespace!r} does not match reporting_counterparty_lei "
            f"{reporting_lei!r}"
        )
    suffix = uti[20:]
    if suffix and not _UTI_SUFFIX_RE.match(suffix):
        return False, f"suffix {suffix!r} contains characters outside [A-Z0-9-]"
    return True, ""


# --- field-level validators ---------------------------------------------

def _check_iso8601_utc(name: str, value: Any, errors: list[str]) -> None:
    if value is None:
        errors.append(f"{name}: missing/null")
        return
    if not isinstance(value, str) or not _ISO8601_UTC_RE.match(value):
        errors.append(f"{name}: not ISO 8601 UTC ({value!r})")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{name}: not a valid datetime ({value!r})")


def _check_iso_date(name: str, value: Any, errors: list[str]) -> None:
    if value is None:
        errors.append(f"{name}: missing/null")
        return
    if not isinstance(value, str) or not _ISO_DATE_RE.match(value):
        errors.append(f"{name}: not a YYYY-MM-DD date ({value!r})")
        return
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        errors.append(f"{name}: not a valid calendar date ({value!r})")


def _check_currency(name: str, value: Any, errors: list[str]) -> None:
    if value is None:
        errors.append(f"{name}: missing/null")
        return
    if not isinstance(value, str) or len(value) != 3:
        errors.append(f"{name}: not a 3-letter ISO 4217 code ({value!r})")
        return
    if pycountry.currencies.get(alpha_3=value) is None:
        errors.append(f"{name}: not a recognised ISO 4217 currency ({value!r})")


def _check_positive_number(name: str, value: Any, errors: list[str]) -> None:
    if value is None:
        errors.append(f"{name}: missing/null")
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{name}: not numeric ({type(value).__name__})")
        return
    if value <= 0:
        errors.append(f"{name}: must be > 0 (got {value})")


def _check_action_type(value: Any, errors: list[str]) -> None:
    if value is None:
        errors.append("action_type: missing/null")
        return
    if not isinstance(value, str) or value not in ACTION_TYPE_VALUES:
        errors.append(f"action_type: not in {sorted(ACTION_TYPE_VALUES)} ({value!r})")


def _check_cleared(value: Any, errors: list[str]) -> None:
    if value is None:
        errors.append("cleared: missing/null")
        return
    if not isinstance(value, bool):
        errors.append(f"cleared: not boolean ({type(value).__name__})")


def _check_collateral_portfolio_code(value: Any, errors: list[str]) -> None:
    if value is None:
        errors.append("collateral_portfolio_code: missing/null")
        return
    if not isinstance(value, str) or not value.strip():
        errors.append(f"collateral_portfolio_code: not a non-empty string ({value!r})")


def _check_initial_margin(value: Any, errors: list[str]) -> None:
    if value is None:
        errors.append("initial_margin_posted: missing/null")
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"initial_margin_posted: not numeric ({type(value).__name__})")
        return
    if value < 0:
        errors.append(f"initial_margin_posted: must be >= 0 (got {value})")


def _check_variation_margin(value: Any, errors: list[str]) -> None:
    # Variation margin can legitimately be negative (mark-to-market movement).
    if value is None:
        errors.append("variation_margin_posted: missing/null")
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"variation_margin_posted: not numeric ({type(value).__name__})")


def _check_upi_present(upi_result: dict | None, errors: list[str]) -> None:
    """
    UPI is treated as present iff Module 2 produced a non-null upi_code.
    For NOVEL trades (NO_PRODUCT_DEFINITION) and unmatched conventional
    trades, the code is null and this fails.
    """
    if upi_result is None or upi_result.get("upi_code") is None:
        errors.append("upi: missing/null (Module 2 did not assign a UPI)")


def _check_lei_pair(raw_trade: dict, errors: list[str],
                    lei_results: dict[str, dict]) -> None:
    """Per-LEI validation, recording per-counterparty result for the top-level block."""
    for fname in ("reporting_counterparty_lei", "other_counterparty_lei"):
        value = raw_trade.get(fname)
        ok, err = validate_lei(value)
        lei_results[fname] = {"value": value, "valid": ok, "error": err if err else None}
        if not ok:
            errors.append(f"{fname}: invalid LEI ({err})")


def _check_uti_field(raw_trade: dict, errors: list[str], uti_result: dict) -> None:
    value = raw_trade.get("uti")
    reporting_lei = raw_trade.get("reporting_counterparty_lei")
    ok, err = validate_uti(value, reporting_lei)
    uti_result["value"] = value
    uti_result["valid"] = ok
    uti_result["error"] = err if err else None
    if not ok:
        errors.append(f"uti: invalid UTI ({err})")


# --- ComplianceResult ----------------------------------------------------

@dataclass
class ComplianceResult:
    status: str
    field_errors: list[str] = field(default_factory=list)
    applicability_note: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- per-regime entry points --------------------------------------------

_NOVEL_CFTC_NOTE_DCM = (
    "Prediction contract on a CFTC-regulated DCM: in-scope but classification "
    "uncertain pending CFTC ANPR 91 FR 12516. Reporting status CONDITIONAL — "
    "would only become a clean COMPLIANT once formal classification is finalised."
)
_NOVEL_CFTC_NOTE_OFFSHORE = (
    "Prediction contract executed on an offshore unregulated venue (not a CFTC "
    "DCM): outside CFTC reporting scope. Status NOT_APPLICABLE."
)
_NOVEL_MAS_NOTE = (
    "Event/prediction contract: not classified as an OTC derivative under MAS "
    "trade reporting rules. Status NOT_APPLICABLE."
)


def _validate_common_fields(raw_trade: dict, errors: list[str],
                            lei_results: dict, uti_result: dict,
                            upi_result: dict | None) -> None:
    """
    Validates the 11 fields common to CFTC and MAS. Mutates the passed-in
    `errors`, `lei_results`, and `uti_result` containers.
    """
    _check_uti_field(raw_trade, errors, uti_result)
    _check_upi_present(upi_result, errors)
    _check_lei_pair(raw_trade, errors, lei_results)
    _check_iso8601_utc("execution_timestamp", raw_trade.get("execution_timestamp"), errors)
    _check_iso_date("effective_date", raw_trade.get("effective_date"), errors)
    _check_iso_date("maturity_date", raw_trade.get("maturity_date"), errors)
    _check_currency("notional_currency", raw_trade.get("notional_currency"), errors)
    _check_positive_number("notional_amount", raw_trade.get("notional_amount"), errors)
    _check_action_type(raw_trade.get("action_type"), errors)
    _check_cleared(raw_trade.get("cleared"), errors)


def check_cftc_compliance(parsed_trade: ParsedTrade, upi_result: dict | None,
                          raw_trade: dict,
                          lei_results: dict | None = None,
                          uti_result: dict | None = None) -> ComplianceResult:
    """
    CFTC compliance evaluation. Mutates lei_results / uti_result so the caller
    can reuse them in the per-trade record (avoids duplicating identifier
    validation across regimes).
    """
    if lei_results is None:
        lei_results = {}
    if uti_result is None:
        uti_result = {}

    if parsed_trade.classification_flag == "NOVEL_INSTRUMENT_NO_TAXONOMY":
        platform_type = (raw_trade.get("platform_type") or "")
        if "CFTC" in platform_type or "DCM" in platform_type:
            return ComplianceResult(
                status="CONDITIONAL",
                field_errors=[],
                applicability_note=_NOVEL_CFTC_NOTE_DCM,
            )
        return ComplianceResult(
            status="NOT_APPLICABLE",
            field_errors=[],
            applicability_note=_NOVEL_CFTC_NOTE_OFFSHORE,
        )

    errors: list[str] = []
    _validate_common_fields(raw_trade, errors, lei_results, uti_result, upi_result)
    status = "COMPLIANT" if not errors else "NONCOMPLIANT"
    return ComplianceResult(status=status, field_errors=errors)


def check_mas_compliance(parsed_trade: ParsedTrade, upi_result: dict | None,
                         raw_trade: dict,
                         lei_results: dict | None = None,
                         uti_result: dict | None = None) -> ComplianceResult:
    """
    MAS compliance evaluation. MAS additionally requires the three collateral /
    margin fields (which CFTC does not).
    """
    if lei_results is None:
        lei_results = {}
    if uti_result is None:
        uti_result = {}

    if parsed_trade.classification_flag == "NOVEL_INSTRUMENT_NO_TAXONOMY":
        return ComplianceResult(
            status="NOT_APPLICABLE",
            field_errors=[],
            applicability_note=_NOVEL_MAS_NOTE,
        )

    errors: list[str] = []
    _validate_common_fields(raw_trade, errors, lei_results, uti_result, upi_result)
    _check_collateral_portfolio_code(raw_trade.get("collateral_portfolio_code"), errors)
    _check_initial_margin(raw_trade.get("initial_margin_posted"), errors)
    _check_variation_margin(raw_trade.get("variation_margin_posted"), errors)
    status = "COMPLIANT" if not errors else "NONCOMPLIANT"
    return ComplianceResult(status=status, field_errors=errors)


# --- top-level orchestration --------------------------------------------

def evaluate_trade(parsed_trade: ParsedTrade, upi_result: dict | None,
                   raw_trade: dict) -> dict[str, Any]:
    """
    Build the full per-trade compliance record. LEI and UTI validation are
    performed once and surfaced at the top level (regime-agnostic), then
    each regime contributes its own status + field_errors block.
    """
    lei_results: dict[str, dict] = {}
    uti_result: dict[str, Any] = {}

    cftc = check_cftc_compliance(parsed_trade, upi_result, raw_trade, lei_results, uti_result)
    # Run MAS with fresh per-regime error containers but reuse identifier results.
    mas_lei: dict = {}
    mas_uti: dict = {}
    mas = check_mas_compliance(parsed_trade, upi_result, raw_trade, mas_lei, mas_uti)

    # If CFTC was the applicability path (NOVEL), lei_results / uti_result may
    # be empty. Run the identifier checks regardless so the top-level block is
    # always populated for transparency (per design choice 4).
    if not lei_results:
        _check_lei_pair(raw_trade, [], lei_results)
    if not uti_result:
        _check_uti_field(raw_trade, [], uti_result)

    return {
        "trade_id": parsed_trade.trade_id,
        "classification_flag": parsed_trade.classification_flag,
        "regimes": {"CFTC": cftc.to_dict(), "MAS": mas.to_dict()},
        "lei_validations": lei_results,
        "uti_validation": uti_result,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Module 3: compliance check (CFTC, MAS)")
    ap.add_argument("--trades", default="data/trades.json")
    ap.add_argument("--upi-lookup", default="output/upi_lookup.json")
    ap.add_argument("--output", default="output/compliance_report.json")
    args = ap.parse_args(argv)

    raw_trades = json.loads(Path(args.trades).read_text(encoding="utf-8"))
    raw_by_id = {t.get("trade_id"): t for t in raw_trades if isinstance(t, dict)}

    upi_records = json.loads(Path(args.upi_lookup).read_text(encoding="utf-8"))
    upi_by_id = {r["trade_id"]: r for r in upi_records}

    parsed = parse_trades_file(args.trades)

    out = [
        evaluate_trade(p, upi_by_id.get(p.trade_id), raw_by_id.get(p.trade_id, {}))
        for p in parsed
    ]

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")

    cftc_status: dict[str, int] = {}
    mas_status: dict[str, int] = {}
    n_lei_invalid = n_uti_invalid = 0
    for r in out:
        cftc_status[r["regimes"]["CFTC"]["status"]] = cftc_status.get(
            r["regimes"]["CFTC"]["status"], 0) + 1
        mas_status[r["regimes"]["MAS"]["status"]] = mas_status.get(
            r["regimes"]["MAS"]["status"], 0) + 1
        if any(not v.get("valid") for v in r["lei_validations"].values()):
            n_lei_invalid += 1
        if not r["uti_validation"].get("valid"):
            n_uti_invalid += 1

    print(f"Compliance report: {len(out)} trades -> {args.output}")
    print(f"  CFTC status:                     {cftc_status}")
    print(f"  MAS  status:                     {mas_status}")
    print(f"  trades with >=1 invalid LEI:     {n_lei_invalid}")
    print(f"  trades with invalid UTI:         {n_uti_invalid}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
