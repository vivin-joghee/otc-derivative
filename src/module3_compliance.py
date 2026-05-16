"""
Module 3: Multi-Jurisdictional Compliance Checker.

For every trade, evaluates compliance under CFTC and MAS:
  - validates every required field with a {value, valid, error} record,
    so passes are visible alongside failures (full audit trail)
  - validates LEIs (ISO 7064 MOD 97-10) and UTI (ISO 23897)
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
from typing import Any, Callable, Optional

import pycountry
from stdnum import lei as stdnum_lei
from stdnum.exceptions import ValidationError as StdnumValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from module1_parser import ParsedTrade, parse_trades_file  # noqa: E402


# --- constants ----------------------------------------------------------

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
_UTI_NAMESPACE_RE = re.compile(r"^[A-Z0-9]{20}$")
_UTI_SUFFIX_RE = re.compile(r"^[A-Z0-9-]*$")


# --- LEI -----------------------------------------------------------------

def compute_lei_check_digits(body: str) -> str:
    """ISO 7064 MOD 97-10 check digits for an LEI body (18 chars)."""
    chars: list[str] = []
    for c in body:
        if c.isdigit():
            chars.append(c)
        elif "A" <= c <= "Z":
            chars.append(str(ord(c) - ord("A") + 10))
        else:
            raise ValueError(f"invalid LEI body character: {c!r}")
    chars.append("00")
    n = int("".join(chars))
    return f"{98 - (n % 97):02d}"


def validate_lei(lei: Optional[str]) -> tuple[bool, str]:
    """20-char LEI per ISO 17442 + ISO 7064 MOD 97-10 (via python-stdnum)."""
    if lei is None:
        return False, "missing/null"
    if not isinstance(lei, str):
        return False, f"expected string, got {type(lei).__name__}"
    try:
        stdnum_lei.validate(lei)
        return True, ""
    except StdnumValidationError as exc:
        return False, f"{type(exc).__name__}: {exc}"


# --- UTI -----------------------------------------------------------------

def validate_uti(uti: Optional[str], reporting_lei: Optional[str]) -> tuple[bool, str]:
    """ISO 23897 UTI: <=52 chars; first 20 = reporting LEI shape; suffix [A-Z0-9-]."""
    if uti is None:
        return False, "missing/null"
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


# --- field-level validators (pure: value -> (valid, error)) -------------

def _validate_iso8601_utc(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, "missing/null"
    if not isinstance(value, str):
        return False, f"expected string, got {type(value).__name__}"
    if not _ISO8601_UTC_RE.match(value):
        return False, f"not ISO 8601 UTC ({value!r}); expected YYYY-MM-DDTHH:MM:SSZ"
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True, ""
    except ValueError:
        return False, f"not a valid datetime ({value!r})"


def _validate_iso_date(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, "missing/null"
    if not isinstance(value, str):
        return False, f"expected string, got {type(value).__name__}"
    if not _ISO_DATE_RE.match(value):
        return False, f"not YYYY-MM-DD ({value!r})"
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, f"not a valid calendar date ({value!r})"


def _validate_currency(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, "missing/null"
    if not isinstance(value, str) or len(value) != 3:
        return False, f"not a 3-letter ISO 4217 code ({value!r})"
    if pycountry.currencies.get(alpha_3=value) is None:
        return False, f"not a recognised ISO 4217 currency ({value!r})"
    return True, ""


def _validate_positive_number(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, "missing/null"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False, f"not numeric ({type(value).__name__})"
    if value <= 0:
        return False, f"must be > 0 (got {value})"
    return True, ""


def _validate_action_type(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, "missing/null"
    if not isinstance(value, str):
        return False, f"expected string, got {type(value).__name__}"
    if value not in ACTION_TYPE_VALUES:
        return False, f"not in {sorted(ACTION_TYPE_VALUES)} ({value!r})"
    return True, ""


def _validate_cleared(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, "missing/null"
    if not isinstance(value, bool):
        return False, f"not boolean ({type(value).__name__})"
    return True, ""


def _validate_collateral_portfolio_code(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, "missing/null"
    if not isinstance(value, str) or not value.strip():
        return False, f"not a non-empty string ({value!r})"
    return True, ""


def _validate_initial_margin(value: Any) -> tuple[bool, str]:
    if value is None:
        return False, "missing/null"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False, f"not numeric ({type(value).__name__})"
    if value < 0:
        return False, f"must be >= 0 (got {value})"
    return True, ""


def _validate_variation_margin(value: Any) -> tuple[bool, str]:
    # Variation margin can legitimately be negative (mark-to-market movement).
    if value is None:
        return False, "missing/null"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False, f"not numeric ({type(value).__name__})"
    return True, ""


# --- check-runner helpers (build per-field {value, valid, error} records) -

def _record(value: Any, validator: Callable[[Any], tuple[bool, str]]) -> dict[str, Any]:
    valid, err = validator(value)
    return {"value": value, "valid": valid, "error": err if err else None}


def _record_uti(uti: Any, reporting_lei: Any) -> dict[str, Any]:
    valid, err = validate_uti(uti, reporting_lei)
    return {"value": uti, "valid": valid, "error": err if err else None}


def _record_upi(upi_result: dict | None) -> dict[str, Any]:
    """
    UPI is treated as 'present' iff Module 2 produced a non-null upi_code.
    NOVEL trades and unmatched conventional trades will have upi_code=None.
    """
    value = (upi_result or {}).get("upi_code")
    if value is None:
        return {
            "value": None,
            "valid": False,
            "error": "missing/null (Module 2 did not assign a UPI)",
        }
    return {"value": value, "valid": True, "error": None}


# --- ComplianceResult ----------------------------------------------------

@dataclass
class ComplianceResult:
    status: str                                    # COMPLIANT | NONCOMPLIANT | CONDITIONAL | NOT_APPLICABLE
    applicability_note: Optional[str] = None
    field_validations: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- per-regime entry points --------------------------------------------

_NOVEL_CFTC_NOTE_DCM = (
    "Prediction contract on a CFTC-regulated DCM: in-scope but classification "
    "uncertain pending CFTC ANPR 91 FR 12516. Status CONDITIONAL — would only "
    "become COMPLIANT once formal classification is finalised. Field "
    "validations are still reported below for transparency."
)
_NOVEL_CFTC_NOTE_OFFSHORE = (
    "Prediction contract executed on an offshore unregulated venue (not a CFTC "
    "DCM): outside CFTC reporting scope. Status NOT_APPLICABLE. Field "
    "validations are still reported below for transparency."
)
_NOVEL_MAS_NOTE = (
    "Event/prediction contract: not classified as an OTC derivative under MAS "
    "trade reporting rules. Status NOT_APPLICABLE. Field validations are still "
    "reported below for transparency."
)


def _build_common_field_validations(raw_trade: dict,
                                    upi_result: dict | None) -> dict[str, dict]:
    """The 11 fields required by both CFTC and MAS."""
    return {
        "uti": _record_uti(raw_trade.get("uti"), raw_trade.get("reporting_counterparty_lei")),
        "upi": _record_upi(upi_result),
        "reporting_counterparty_lei": _record(raw_trade.get("reporting_counterparty_lei"), validate_lei),
        "other_counterparty_lei": _record(raw_trade.get("other_counterparty_lei"), validate_lei),
        "execution_timestamp": _record(raw_trade.get("execution_timestamp"), _validate_iso8601_utc),
        "effective_date": _record(raw_trade.get("effective_date"), _validate_iso_date),
        "maturity_date": _record(raw_trade.get("maturity_date"), _validate_iso_date),
        "notional_currency": _record(raw_trade.get("notional_currency"), _validate_currency),
        "notional_amount": _record(raw_trade.get("notional_amount"), _validate_positive_number),
        "action_type": _record(raw_trade.get("action_type"), _validate_action_type),
        "cleared": _record(raw_trade.get("cleared"), _validate_cleared),
    }


def check_cftc_compliance(parsed_trade: ParsedTrade,
                          upi_result: dict | None,
                          raw_trade: dict) -> ComplianceResult:
    """
    EventContract on CFTC DCM -> CONDITIONAL.
    EventContract elsewhere   -> NOT_APPLICABLE.
    Conventional derivative   -> COMPLIANT iff every field passes, else NONCOMPLIANT.
    """
    fv = _build_common_field_validations(raw_trade, upi_result)

    if parsed_trade.classification_flag == "NOVEL_INSTRUMENT_NO_TAXONOMY":
        platform_type = (raw_trade.get("platform_type") or "")
        if "CFTC" in platform_type or "DCM" in platform_type:
            return ComplianceResult(
                status="CONDITIONAL",
                applicability_note=_NOVEL_CFTC_NOTE_DCM,
                field_validations=fv,
            )
        return ComplianceResult(
            status="NOT_APPLICABLE",
            applicability_note=_NOVEL_CFTC_NOTE_OFFSHORE,
            field_validations=fv,
        )

    status = "COMPLIANT" if all(v["valid"] for v in fv.values()) else "NONCOMPLIANT"
    return ComplianceResult(status=status, field_validations=fv)


def check_mas_compliance(parsed_trade: ParsedTrade,
                         upi_result: dict | None,
                         raw_trade: dict) -> ComplianceResult:
    """
    EventContract -> NOT_APPLICABLE (out of MAS scope).
    Conventional derivative -> COMPLIANT iff every field passes, else NONCOMPLIANT.
    MAS additionally requires the three collateral / margin fields (a value of
    zero is fine; null is what fails).
    """
    fv = _build_common_field_validations(raw_trade, upi_result)
    fv["collateral_portfolio_code"] = _record(
        raw_trade.get("collateral_portfolio_code"), _validate_collateral_portfolio_code,
    )
    fv["initial_margin_posted"] = _record(
        raw_trade.get("initial_margin_posted"), _validate_initial_margin,
    )
    fv["variation_margin_posted"] = _record(
        raw_trade.get("variation_margin_posted"), _validate_variation_margin,
    )

    if parsed_trade.classification_flag == "NOVEL_INSTRUMENT_NO_TAXONOMY":
        return ComplianceResult(
            status="NOT_APPLICABLE",
            applicability_note=_NOVEL_MAS_NOTE,
            field_validations=fv,
        )

    status = "COMPLIANT" if all(v["valid"] for v in fv.values()) else "NONCOMPLIANT"
    return ComplianceResult(status=status, field_validations=fv)


# --- top-level orchestration --------------------------------------------

def evaluate_trade(parsed_trade: ParsedTrade,
                   upi_result: dict | None,
                   raw_trade: dict) -> dict[str, Any]:
    cftc = check_cftc_compliance(parsed_trade, upi_result, raw_trade)
    mas = check_mas_compliance(parsed_trade, upi_result, raw_trade)
    return {
        "trade_id": parsed_trade.trade_id,
        "classification_flag": parsed_trade.classification_flag,
        "regimes": {"CFTC": cftc.to_dict(), "MAS": mas.to_dict()},
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
        cftc_fv = r["regimes"]["CFTC"]["field_validations"]
        if not cftc_fv["reporting_counterparty_lei"]["valid"] or \
           not cftc_fv["other_counterparty_lei"]["valid"]:
            n_lei_invalid += 1
        if not cftc_fv["uti"]["valid"]:
            n_uti_invalid += 1

    print(f"Compliance report: {len(out)} trades -> {args.output}")
    print(f"  CFTC status:                     {cftc_status}")
    print(f"  MAS  status:                     {mas_status}")
    print(f"  trades with >=1 invalid LEI:     {n_lei_invalid}")
    print(f"  trades with invalid UTI:         {n_uti_invalid}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Module 3 validation completed.

Multi-jurisdictional compliance checker executed successfully and generated structured output under `output/compliance_report.json`.

Validation observations:

* CFTC and MAS reporting logic executed as expected
* T026 and T028 correctly returned `CONDITIONAL` under CFTC
* T027 correctly returned `NOT_APPLICABLE` under CFTC
* T026–T028 correctly returned `NOT_APPLICABLE` under MAS
* LEI and UTI validation checks triggered correctly for malformed records
* Structured field-level audit records generated consistently across all trades

No major validation concerns noted at this juncture.
"""
