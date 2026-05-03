"""
Module 1 stub (as provided on the assignment website).
The timestamp regex and date validator are fully implemented;
classify_instrument() and parse_trade() must be completed.
"""

CONVENTIONAL_ASSET_CLASSES = {"Rates", "Credit", "FX", "Equity", "Commodities"}
NOVEL_ASSET_CLASSES = {"EventContract"}


def classify_instrument(trade: dict) -> str:
    """
    Determine the regulatory taxonomy classification flag for a trade.
    Returns: CONVENTIONAL_DERIVATIVE | NOVEL_INSTRUMENT_NO_TAXONOMY | CLASSIFICATION_AMBIGUOUS
    """
    asset_class = trade.get("asset_class")
    if asset_class is None:
        return "CLASSIFICATION_AMBIGUOUS"
    if asset_class in CONVENTIONAL_ASSET_CLASSES:
        return "CONVENTIONAL_DERIVATIVE"
    if asset_class in NOVEL_ASSET_CLASSES:
        return "NOVEL_INSTRUMENT_NO_TAXONOMY"
    # TODO: handle additional unknown asset classes
    return "CLASSIFICATION_AMBIGUOUS"


def parse_trade(trade: dict):
    """
    Parse a single raw trade dict.
    Steps:
      1. Extract asset_class, instrument_type, use_case
      2. Call classify_instrument()
      3. Validate execution_timestamp (ISO 8601 UTC required)
      4. Validate effective_date and maturity_date
      5. Collect all errors; set parse_status to SUCCESS / PARTIAL / FAILED
    """
    errors: list[str] = []
    # TODO: implement all five steps above
    raise NotImplementedError
