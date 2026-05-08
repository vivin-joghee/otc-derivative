# OTC Derivatives Compliance Engine

NTU MH6822 RegTech — Homework 2 implementation.

This repo currently contains **Module 1** (Trade Parser & Instrument Classifier),
**Module 2** (UPI Lookup Engine), **Module 3** (Multi-Jurisdictional
Compliance Checker — CFTC + MAS), and **Module 5** (Compliance Dashboard,
bonus). Module 4 is the written report and lives outside this repo.

## Layout

```
data/
  trades.json                 # 28 sample trades provided by the assignment
  product_definitions/        # ANNA-DSB repo (gitignored — clone separately)
stubs/
  module1_parser.py           # original assignment-website stubs
  module2_upi_lookup.py
  module3_compliance.py
src/
  module1_parser.py           # implementations
  module2_upi_lookup.py
  module3_compliance.py
  dashboard.py                # Module 5 — Flask app
  templates/
    dashboard.html            #     Jinja2 template
output/
  parsed_trades.json          # Module 1 output
  upi_lookup.json             # Module 2 output
  compliance_report.json      # Module 3 output
  dashboard.html              # Module 5 static snapshot (regenerated)
requirements.txt              # python-stdnum, pycountry, flask, plotly
```

## Setup

1. Python 3.10+.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Clone the ANNA-DSB product definitions library into `data/product_definitions/`:
   ```
   git clone https://github.com/ANNA-DSB/Product-Definitions.git data/product_definitions
   ```

## Run

```
python src/module1_parser.py    --input data/trades.json   --output output/parsed_trades.json
python src/module2_upi_lookup.py --trades data/trades.json --library data/product_definitions --output output/upi_lookup.json
python src/module3_compliance.py --trades data/trades.json --upi-lookup output/upi_lookup.json --output output/compliance_report.json
```

Module 5 dashboard (Flask):
```
python src/dashboard.py                           # serves at http://127.0.0.1:5000/
python src/dashboard.py --snapshot output/dashboard.html   # render once, no server
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

## Module 3 — Compliance Checker (CFTC + MAS)

Validates each trade against the required-field set for two regimes plus
ISO 7064 MOD 97-10 LEI checksum and ISO 23897 UTI format. MAS adds three
fields CFTC does not require: `collateral_portfolio_code`,
`initial_margin_posted`, `variation_margin_posted` (a value of `0` is fine
— it's the `null` that fails).

LEI validation uses `python-stdnum` (`stdnum.lei.validate`). A
`compute_lei_check_digits()` helper is also kept in the source for
educational transparency. Currency validation uses `pycountry` (covers XAU).

**Result distribution:**

| Regime | COMPLIANT | NONCOMPLIANT | CONDITIONAL | NOT_APPLICABLE |
|---|---|---|---|---|
| CFTC | 1 (T017) | 24 | 2 (T026, T028 on Kalshi DCM) | 1 (T027 offshore) |
| MAS | 0 | 25 | 0 | 3 (T026–T028) |

**Why so few COMPLIANT?** The dataset was constructed with deliberate data-
quality issues. Of the eight distinct counterparty LEIs in `trades.json`,
**three fail ISO 7064 MOD 97-10** — `2138002TXD6KSZ3V5X27`,
`9695009AXSRNHZE85Y20`, `4R3ZURLYISNNNMHMK608`. Only **3 conventional
trades** have both counterparties' LEIs valid (T013, T017, T021), and
T013/T021 fail other field checks (date-only `execution_timestamp`,
`maturity_date: "9999-99-99"`). T017 is the lone CFTC pass; for MAS it
fails because `collateral_portfolio_code` / `initial_margin_posted` /
`variation_margin_posted` are explicit `null`. The marker hint
"test LEIs are not all real; that is part of the exercise" is the
intended teaching outcome — the engine catches it.

**Jurisdictional asymmetry for prediction contracts (T026–T028):**
- T026 (Kalshi, CFTC DCM, `CorporateTreasury` reporting party)
  → CFTC: CONDITIONAL (in-scope but classification awaits ANPR 91 FR 12516)
  → MAS: NOT_APPLICABLE
- T027 (Polymarket, offshore VPN-accessed)
  → CFTC: NOT_APPLICABLE (off-shore venue, not a CFTC DCM)
  → MAS: NOT_APPLICABLE
- T028 (Kalshi, CFTC DCM, EU FinTech)
  → CFTC: CONDITIONAL
  → MAS: NOT_APPLICABLE

**Audit trail** — every required field appears in the per-regime
`field_validations` block as `{value, valid, error}`, regardless of whether
it passed or failed. NOVEL trades still get the full validations populated
even though their status is set by the applicability rule, so the report
makes clear *why* the trade isn't reportable cleanly (e.g. T026 shows
`effective_date: missing/null` because event contracts use `settlement_date`
instead — informative, but doesn't drive the CONDITIONAL status).

## Module 5 — Dashboard (bonus)

A small Flask app that loads `output/compliance_report.json` plus
`data/trades.json` and renders four required charts plus the written
interpretation:

1. **Portfolio compliance heatmap** — 28 trades × 2 regimes, colour-coded
   by status (green / red / amber / gray), with hover tooltips listing the
   failed-field names and the applicability note for CONDITIONAL /
   NOT_APPLICABLE cells.
2. **Field-level failure-frequency** horizontal bar — counts how many times
   each required field failed validation, summed across all 28 trades and
   both regimes (so NOVEL field-absences are visible alongside the LEI
   checksum failures).
3. **Asset-class status breakdown** — stacked bar per asset class, side-by-
   side per regime; EventContract is included so the visual contrast with
   conventional asset classes is explicit.
4. **Classification frontier panel** — a plain HTML table covering T026,
   T027, T028 with platform, platform_type, CFTC + MAS status, and the
   trade description.

Run `python src/dashboard.py` to start the Flask dev server at
http://127.0.0.1:5000/, or `python src/dashboard.py --snapshot
output/dashboard.html` to render once to a static file (the same file is
committed so the dashboard is browseable without running anything).

## Acknowledgement

This implementation was developed with AI assistance for ANNA-DSB schema
exploration, design discussions (matching strategy, status semantics,
validation scope), and code review. Final design decisions, the alias-free
heuristic-matching approach, and all integration with the assignment brief
were author-driven.
