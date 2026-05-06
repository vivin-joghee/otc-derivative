# OTC Derivatives Compliance Engine

NTU MH6822 RegTech — Homework 2 implementation.

This repo currently contains **Module 1** (Trade Parser & Instrument Classifier)
and **Module 2** (UPI Lookup Engine). Modules 3, 4, and 5 are still to come.

## Layout

```
data/
  trades.json                 # 28 sample trades provided by the assignment
  product_definitions/        # ANNA-DSB repo (gitignored — clone separately)
stubs/
  module1_parser.py           # original assignment-website stubs
  module2_upi_lookup.py
src/
  module1_parser.py           # implementation
  module2_upi_lookup.py
output/
  parsed_trades.json          # Module 1 output
  upi_lookup.json             # Module 2 output
```

## Setup

1. Python 3.10+ (no third-party dependencies for Modules 1–2 — pure stdlib).
2. Clone the ANNA-DSB product definitions library into `data/product_definitions/`:
   ```
   git clone https://github.com/ANNA-DSB/Product-Definitions.git data/product_definitions
   ```

## Run

```
python src/module1_parser.py   --input data/trades.json --output output/parsed_trades.json
python src/module2_upi_lookup.py --trades data/trades.json --library data/product_definitions --output output/upi_lookup.json
```

## Module 1 — Trade Parser

Reads `trades.json` and produces a `ParsedTrade` per record with `asset_class`,
`instrument_type`, `use_case`, a classification flag, and any parse errors.

- 28/28 trades parse without crashing
- 25 `CONVENTIONAL_DERIVATIVE`, 3 `NOVEL_INSTRUMENT_NO_TAXONOMY` (T026, T027, T028)
- 2 `PARTIAL` records: T013 (date-only `execution_timestamp` rejected as not
  ISO 8601 UTC) and T021 (`maturity_date: "9999-99-99"` rejected as invalid date)

## Module 2 — UPI Lookup

For each trade, locates the matching ANNA-DSB product template and validates
attribute values against the template's codesets.

- 25 `FOUND`, 3 `NO_PRODUCT_DEFINITION` (T026–T028)
- Of the 25 found: 11 exact filename matches, 14 heuristic matches (the trade's
  `use_case` doesn't appear verbatim in the library's 143 templates, so a
  token-overlap heuristic picks the closest stem; the chosen template name
  appears in `classification_note` so the marker can review).
- Validation surfaces:
  - T005 `GBP-LIBOR-BBA` → **warning** (LIBOR cessation, June 2023)
  - T006 `EUR-ESTR` (leg 2), T018 `EUR-ESTR` → error (rate is real but absent
    from the FpmlRatesReferenceRate codeset)
  - T009 `INVALID_CCY` → error
  - T013 `GBP-RPI` → error (FPML codeset has it as `UK-RPI`; the trade uses
    a non-FPML, currency-prefixed name)

`upi_code` is a **deterministic 12-char base32 mock** (uppercase alphanumeric,
ISIN-shaped) derived from the matched template plus the trade's UPI-defining
attributes (currency, reference rate, term, underlier, etc. — but *not*
notional amount, dates, or counterparty LEIs, which don't affect UPI
identity). Two trades with the same product type produce the same code; any
attribute change produces a different code. Real UPIs are 20-char strings
issued by the ANNA-DSB live API at registration and aren't extractable from
the cloned product-definition repo (the templates are JSON Schemas, not
records). NOVEL trades and unmatched conventional trades keep `upi_code: null`.

## Acknowledgement

This implementation was developed with AI assistance for ANNA-DSB schema
exploration, design discussions (matching strategy, status semantics,
validation scope), and code review. Final design decisions, the alias-free
heuristic-matching approach, and all integration with the assignment brief
were author-driven.
