"""
Module 3 stub (as provided on the assignment website).
Functions to complete: validate_lei, validate_uti,
check_cftc_compliance, check_emir_compliance.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ComplianceResult:
    status: str                # COMPLIANT | NONCOMPLIANT | CONDITIONAL | NOT_APPLICABLE
    field_errors: list
    applicability_note: Optional[str] = None


def compute_lei_check_digits(body: str) -> str:
    """
    ISO 7064 MOD 97-10 check-digit computation for an LEI body (18 chars).
    Returns a two-character zero-padded string.
    """
    # Convert each character to its numeric value:
    #   digits 0-9 -> stay
    #   letters A-Z -> 10-35
    numeric = ""
    for c in body:
        if c.isdigit():
            numeric += c
        elif "A" <= c <= "Z":
            numeric += str(ord(c) - ord("A") + 10)
        else:
            raise ValueError(f"invalid LEI body character: {c!r}")
    numeric += "00"
    n = int(numeric)
    check = 98 - (n % 97)
    return f"{check:02d}"


def validate_lei(lei: Optional[str]) -> tuple[bool, str]:
    """
    Validate an LEI string. Returns (is_valid, error_message).
    The check digit logic is nearly complete in the stub.
    You need to call compute_lei_check_digits(lei[:18]) and
    compare the result with lei[18:].

    Shortcut: from stdnum.iso import lei; lei.validate(value)
    """
    # TODO: implement
    raise NotImplementedError


def validate_uti(uti: Optional[str], reporting_lei: Optional[str]) -> tuple[bool, str]:
    """
    Validate a UTI string. Returns (is_valid, error_message).
    Rules: max 52 chars, first 20 = valid LEI namespace = reporting_lei,
    suffix = uppercase alphanumeric and hyphens only.
    """
    # TODO: implement
    raise NotImplementedError


def check_cftc_compliance(parsed_trade, upi_result, raw_trade) -> ComplianceResult:
    """
    EventContract on CFTC DCM -> CONDITIONAL with explanatory note.
    Conventional derivative -> validate all CDE + CFTC fields,
    validate UTI and both LEIs, return COMPLIANT or NONCOMPLIANT.
    """
    # TODO: implement
    raise NotImplementedError


def check_emir_compliance(parsed_trade, upi_result, raw_trade) -> ComplianceResult:
    """
    EventContract -> NOT_APPLICABLE (GlüStV 2021 gambling classification).
    Conventional derivative -> validate all CDE + EMIR fields including
    collateral fields (required even when margin is zero).
    """
    # TODO: implement
    raise NotImplementedError
