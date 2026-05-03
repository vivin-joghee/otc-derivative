"""
Module 2 stub (as provided on the assignment website).
Three functions to complete: find_product_template, validate_attributes, lookup_upi.
"""

from typing import Optional


def find_product_template(
    asset_class: str, instrument_type: str, use_case: str
) -> Optional[dict]:
    """
    Search the ANNA-DSB product definition library for a matching template.
    Hint: Path.glob("*.json") on the asset_class subdirectory,
    then match on instrument_type and use_case in the filename stem.
    """
    # TODO: implement
    raise NotImplementedError


def validate_attributes(trade: dict, template: dict) -> tuple[list, list]:
    """
    Validate trade attributes against template constraints.
    Returns (errors, warnings).
    Checks: currency (ISO 4217), reference rate (codeset), term unit,
    term value range, debt seniority, delivery type.
    Deprecated LIBOR rates -> warnings, not errors.
    """
    errors, warnings = [], []
    # Partially implemented in the stub file: currency and rate checks are stubs
    # TODO: complete all validation checks
    return errors, warnings


def lookup_upi(parsed_trade):
    """
    Full UPI lookup flow:
      NOVEL_INSTRUMENT_NO_TAXONOMY -> NO_PRODUCT_DEFINITION (with note)
      No matching template found   -> NOT_FOUND
      Template found, errors       -> INVALID_ATTRIBUTES
      Template found, no errors    -> FOUND
    """
    # TODO: implement
    raise NotImplementedError
