# Module 4 — Classification Analysis: Prediction Contracts and the Reporting Frontier

This section answers the four sub-tasks of Module 4 against the three event-contract trades in the portfolio (T026–T028). Citations are inline-APA; the references block sits at the end.

---

## 4A. Economic Function Test

Brandes (2026) argues that a prediction contract must be evaluated by its economic function — hedging, price discovery, risk transfer — *before* being assigned to a regulatory category. Applying his three-question test to the three event-contract trades:

**T026 — `CorporateTreasury` on AfD vote share ≥ 30 % in the 2025 Bundestagswahl, Kalshi.** The trade names *"German renewable energy subsidy regime materially affected by election outcome"* — Brandes's (2026) Sachsen-Anhalt wind-energy archetype. The binary offsets subsidy-rollback risk no listed European derivative covers; market-implied probability updates intraday, while Infratest dimap / Forsa publish with multi-day lag (Brandes 2026).

**T027 — `AssetManager_EU` on US CPI ≥ 3 % Q3 2026, Polymarket via `VPN_BYPASS_GGL_BLOCK`.** USD-denominated bond duration is a measurable inflation exposure; the trade flags `HEDGING_SPECULATIVE_MIXED`, consistent with Brandes's (2026) observation that thin offshore markets blur the two motives. Continuously priced CPI probability has no opinion-poll substitute.

**T028 — `FinTechFirm_EU` on ESMA approval of AI Act Annex III high-risk classification for credit scoring, Kalshi.** Compliance costs are contractually contingent on the decision — the cleanest hedging case, with no polling substitute for regulatory-decision probability.

**Conclusion.** All three trades perform a hedging or price-discovery function analogous to recognised derivatives. Their EU treatment as gambling (Glücksspielstaatsvertrag 2021 in Germany; equivalent national frameworks elsewhere) is what Brandes (2026) calls a "surface-level resemblance" decision — taken before the economic function was evaluated. MAS's `NOT_APPLICABLE` status is a different rationale — the contracts simply fall outside the Singapore OTC derivatives taxonomy — but the upstream cause is the same classification gap, not a deliberate policy determination that political risk should remain unhedgeable.

---

## 4B. What Would a UPI Look Like? (Schema proposal for T026)

**AssetClass / InstrumentType / UseCase.** `EventContract` / `BinaryEventContract` / `PoliticalOutcome`. The asset class is new and would sit alongside the existing five in the ANNA-DSB UPI library.

**Identifying attributes — analogues of `NotionalCurrency` and `ReferenceRate`.** For event contracts the UPI must encode *what is being predicted*, not *what underlies a cash flow stream*. The proposed UPI-defining attributes are:

- `EventDescription` — a free-text but tightly bounded statement of the outcome
- `EventType` — enum (`ELECTION_OUTCOME`, `MACROECONOMIC_THRESHOLD`, `REGULATORY_DECISION`, `JUDICIAL_DECISION`)
- `JurisdictionOfEvent` — ISO 3166-1 country code of the underlying authority
- `SettlementCurrency` — ISO 4217 (including stable-coin sub-codeset if those are admitted as a separate enumeration)
- `ContractSize` — payout per contract
- `SettlementDate` — bounded by event-resolution date
- `ReferenceSource` — the named oracle that resolves the outcome (e.g., Bundeswahlleiterin for German elections, BLS for CPI, ESMA for regulatory decisions). Codeset-validated against an `EventOracleRegistry`.
- `DeliveryType` — always `CASH`. No event admits physical settlement.

**Validation constraints.** `EventDescription` 20–500 characters and must reference a specific, observable, time-bounded outcome; `ReferenceSource` constrained to a registered-oracle codeset analogous to `FpmlRatesReferenceRate`; `SettlementDate` ≤ 5 years post-execution to bound long-tail political uncertainty.

```json
{
  "AssetClass": "EventContract",
  "InstrumentType": "BinaryEventContract",
  "UseCase": "PoliticalOutcome",
  "Level": "UPI",
  "UPI": "<mock-12-char-code>",
  "Attributes": {
    "EventDescription":    { "type": "string", "minLength": 20, "maxLength": 500 },
    "EventType":           { "type": "string", "enum": [
        "ELECTION_OUTCOME", "MACROECONOMIC_THRESHOLD",
        "REGULATORY_DECISION", "JUDICIAL_DECISION"
    ]},
    "JurisdictionOfEvent": { "type": "string", "codeset": "ISO3166CountryCode" },
    "SettlementCurrency":  { "type": "string", "codeset": "ISOCurrencyCode" },
    "ContractSize":        { "type": "number", "minimum": 0 },
    "SettlementDate":      { "type": "string", "format": "date" },
    "ReferenceSource":     { "type": "string", "codeset": "EventOracleRegistry" },
    "DeliveryType":        { "type": "string", "enum": ["CASH"] }
  }
}
```

---

## 4C. Jurisdictional Arbitrage and Regulatory Design

**(1) Beneficiaries and the harmed.** T026's `CorporateTreasury` benefits from US regulatory clarity — Kalshi is a CFTC-regulated DCM (CFTC 2026). T028's `FinTechFirm_EU` uses the same Kalshi venue to hedge an exposure whose economic function sits inside the EU regulatory perimeter; ESMA, the resolving authority, has no visibility into hedging that anticipates its own decision. T027's `AssetManager_EU` is harmed twice over: accessing Polymarket via `VPN_BYPASS_GGL_BLOCK` forfeits consumer protection (Brandes 2026 cites Polymarket's $10.5 M Venezuela non-resolution), and EU systemic-risk regulators get no SDR visibility. Structural losers: EU supervisors, tax authorities, and EU firms forced offshore — *"the prohibition's primary effect is … the elimination of regulatory oversight over that participation"* (Brandes 2026).

**(2) Two of Brandes's five framework elements, operationalised for RegTech.**

*Contract Scope Limitations* (Brandes 2026): permit contracts where identifiable actors bear event-contingent exposure; restrict where none exists. Data: trade-level `event_type`, `jurisdiction_of_event`, and an `economic_function_test_score` per Cassar's (2026) "prediction test." Validation: reject contracts whose event type falls outside the venue's licensed scope. Reporting: jurisdiction-stamped event-classification feed at the SDR.

*Market Integrity Supervision* (Brandes 2026, calling for "surveillance obligations equivalent to those imposed on regulated trading venues under MAR"). Data: L2 order books, trade tape, oracle-attestation hashes. Validation: MAR-equivalent abnormal-volume and pricing alerts, indexed to days approaching resolution. Reporting: sub-second surveillance feed to ESMA, mirroring MiFIR and MAR (Regulation (EU) 596/2014).

**(3) Changes to the reporting stack under an EMIR-aligned framework.** *ANNA-DSB library:* new `EventContract` asset class plus codesets for `EventType`, `JurisdictionOfEvent`, `EventOracleRegistry`. *UTI generation rules:* the ISO 23897 shape is preserved; for venue-traded event contracts the DCM remains the UTI generator, consistent with current exchange-traded practice on Kalshi. The single-party problem (T026 and T028 have `other_counterparty_lei: null`) is resolved by treating the DCM as the reporting party of record rather than re-engineering the namespace — current guidance simply needs an explicit carve-out for single-named-party venue trades. *SDR infrastructure:* dedicated event-contract fields — `event_resolution_source`, `event_outcome_realisation`, `oracle_attestation_hash` — plus lifecycle action types `RESOLVED_YES` / `RESOLVED_NO` that replace the bilateral termination flow. The oracle hash anchors each resolution to a verifiable cryptographic statement, removing the DCM's unilateral authority over outcome determination without entangling the UTI namespace.

---

## 4D. Reflection on Engine Limits

The engine surfaces LEI checksum failures and missing CDE fields. What it cannot see is structurally invisible: Kalshi's ~$13 B March 2026 notional (Brandes 2026; Diercks, Katz & Wright 2026) — roughly $156 B annualised — sits outside any SDR because the ANNA-DSB taxonomy has no `EventContract` asset class. EU-origin Polymarket flows via VPN are equally invisible. The engine reports these as `NO_PRODUCT_DEFINITION` / `NOT_APPLICABLE` — technically correct, substantively a silent miss.

UPI absence is itself a risk signal, not an exemption. A reported trade with no UPI should auto-flag for SDR review, much as MiFIR flags instrument-identifier resolution failures. The current architecture treats classification gaps as silence; a richer framework treats them as observable signal.

Two priorities if advising CFTC on ANPR 91 FR 12516 (CFTC 2026): (i) define `EventContract` in ANNA-DSB with the §4B schema so DCMs and SDRs share an identifier model from day one; (ii) require `oracle_attestation_hash` and `event_outcome_realisation` in SDR data standards at resolution, making post-event integrity auditable without granting the venue unilateral authority.

---

## References

Brandes, A. (2026). *The Unhedgeable State: Political Risk, Prediction Markets, and the Gap in Europe's Risk Management Architecture*. Policy Brief, April 2026.

Cassar, T. (2026). *Regulating Prediction Markets in Europe Requires a 'Prediction Test'*. Oxford Business Law Blog, 31 March 2026.

Commodity Futures Trading Commission [CFTC]. (2026). *Advance Notice of Proposed Rulemaking: Prediction Markets*. 91 FR 12516, RIN 3038-AF65, 16 March 2026.

Diercks, A. M., Katz, J. D., & Wright, J. H. (2026). *Kalshi and the Rise of Macro Markets*. NBER Working Paper No. 34702 / Federal Reserve Board FEDS 2026-010.

Glücksspielstaatsvertrag 2021 (GlüStV 2021). *Staatsvertrag zur Neuregulierung des Glücksspielwesens in Deutschland*, in force 1 July 2021.

Regulation (EU) No 596/2014 of the European Parliament and of the Council (MAR). *Official Journal of the European Union*, L 173, 12 June 2014.

Directive 2014/65/EU of the European Parliament and of the Council (MiFID II). *Official Journal of the European Union*, L 173, 12 June 2014.
