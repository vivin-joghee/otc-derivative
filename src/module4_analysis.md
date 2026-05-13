# Module 4 — Classification Analysis: Prediction Contracts and the Reporting Frontier

This section answers the four sub-tasks of Module 4 against the three event-contract trades in the portfolio (T026–T028). Citations are inline-APA; the references block sits at the end.

---

## 4A. Economic Function Test

Brandes (2026) argues that a prediction contract must be evaluated by its economic function — hedging, price discovery, risk transfer — *before* being assigned to a regulatory category. Applying his three-question test to the three event-contract trades:

**T026 — `CorporateTreasury` (LEI `5493001KJTIIGC8Y1R12`) on AfD vote share ≥ 30 % in the 2025 Bundestagswahl, Kalshi.**
(1) *Identifiable actor with measurable exposure?* Yes. The trade record names *"German renewable energy subsidy regime materially affected by election outcome"* — directly mirroring Brandes's (2026) Sachsen-Anhalt wind-energy archetype, where state-level renewable policy is a quantifiable financial risk. (2) *Hedging utility?* Yes. A binary on AfD vote share offsets subsidy-rollback risk that no listed European derivative covers; the firm "can vote… cannot hedge" (Brandes 2026). (3) *Price discovery beyond polls?* Yes. Market-implied probability updates intraday, whereas Infratest dimap / Forsa publish with multi-day lag (Brandes 2026).

**T027 — `AssetManager_EU` (LEI `VGRQXHF3J8VDLUA7XE92`) on US CPI ≥ 3 % Q3 2026, Polymarket via `VPN_BYPASS_GGL_BLOCK`.** (1) Yes — a USD-denominated bond portfolio carries measurable duration / inflation exposure. (2) Yes, though the trade record itself flags the position as `HEDGING_SPECULATIVE_MIXED`, consistent with Brandes's (2026) observation that thin offshore markets blur the two motives. (3) Yes — continuously priced CPI probability has no opinion-poll substitute.

**T028 — `FinTechFirm_EU` (LEI `9695009AXSRNHZE85Y20`) on ESMA approval of AI Act Annex III high-risk classification for credit scoring, Kalshi.** (1) Yes; the firm's "credit scoring product compliance costs are contingent on this classification decision" — exposure is contractual. (2) Yes; this is the cleanest hedging case in the portfolio because the resolving decision has direct, named-firm impact. (3) Yes — regulatory-decision probability has no polling equivalent.

**Conclusion.** All three trades perform a hedging or price-discovery function analogous to recognised derivatives. Their MAS / EMIR classification as gambling is what Brandes (2026) calls a "surface-level resemblance" decision — taken before the economic function was evaluated, and now suppressing the function rather than regulating it.

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
  "$schema": "http://json-schema.org/draft-04/schema#",
  "title": "EventContract.BinaryEventContract.PoliticalOutcome.UPI.V1",
  "type": "object",
  "properties": {
    "Header": {
      "type": "object",
      "properties": {
        "AssetClass":     { "type": "string", "enum": ["EventContract"] },
        "InstrumentType": { "type": "string", "enum": ["BinaryEventContract"] },
        "UseCase":        { "type": "string", "enum": [
            "PoliticalOutcome", "MacroeconomicOutcome",
            "RegulatoryDecisionOutcome", "JudicialOutcome"
        ]},
        "Level":          { "type": "string", "enum": ["UPI"] }
      },
      "required": ["AssetClass", "InstrumentType", "UseCase", "Level"]
    },
    "Attributes": {
      "type": "object",
      "properties": {
        "EventDescription":    { "type": "string", "minLength": 20, "maxLength": 500 },
        "EventType":           { "type": "string", "enum": [
            "ELECTION_OUTCOME", "MACROECONOMIC_THRESHOLD",
            "REGULATORY_DECISION", "JUDICIAL_DECISION"
        ]},
        "JurisdictionOfEvent": { "$ref": "../../codesets/ISO3166CountryCode.json" },
        "SettlementCurrency":  { "$ref": "../../codesets/ISOCurrencyCode.json" },
        "ContractSize":        { "type": "number", "minimum": 0 },
        "SettlementDate":      { "type": "string", "format": "date" },
        "ReferenceSource":     { "$ref": "../../codesets/EventOracleRegistry.json" },
        "DeliveryType":        { "type": "string", "enum": ["CASH"] }
      },
      "required": [
        "EventDescription", "EventType", "JurisdictionOfEvent",
        "SettlementCurrency", "ContractSize", "SettlementDate",
        "ReferenceSource", "DeliveryType"
      ]
    }
  }
}
```

---

## 4C. Jurisdictional Arbitrage and Regulatory Design

**(1) Beneficiaries and the harmed.** T026's `CorporateTreasury` benefits from US regulatory clarity — Kalshi is a CFTC-regulated DCM (CFTC 2026), so subsidy-rollback risk is lawfully hedged. T027's `AssetManager_EU` is harmed twice: accessing Polymarket via `VPN_BYPASS_GGL_BLOCK` forfeits consumer protection — Brandes (2026) cites Polymarket's $10.5 M Venezuela non-resolution as the relevant precedent — and EU systemic-risk regulators get no SDR visibility into the resulting exposure. The losers are EU regulators (ESMA, the GGL), EU tax authorities, and the EU firms forced offshore. Brandes's (2026) framing holds: *"the prohibition's primary effect is not the elimination of prediction market participation but the elimination of regulatory oversight over that participation."*

**(2) Two of Brandes's five framework elements, operationalised for RegTech.**

*Contract Scope Limitations.* Brandes (2026) proposes "permitting contracts where identifiable actors bear event-contingent financial exposure, and restricting contracts where no such exposure exists." Concretely: collect trade-level `event_type`, `jurisdiction_of_event`, and an `economic_function_test_score` per Cassar's (2026) "prediction test"; validation rejects contracts whose `event_type` is not in the venue's licensed scope (entertainment, celebrity behaviour). Reporting infrastructure: a jurisdiction-stamped event-classification feed at the SDR, queryable by ESMA and national competent authorities.

*Market Integrity Supervision.* Brandes (2026) calls for "surveillance obligations equivalent to those imposed on regulated trading venues under MAR." Operationally: collect full L2 order books and trade tape per contract, plus oracle-attestation hashes at resolution. Validation: MAR-equivalent abnormal-volume and pricing alerts, indexed especially to the days immediately preceding resolution (where the manipulation incentive is highest). Reporting: sub-second surveillance feed to ESMA, mirroring the MiFIR transaction-reporting and MAR (Regulation (EU) 596/2014) obligations already imposed on MiFID II venues.

**(3) Changes to the reporting stack under an EMIR-aligned framework.** *ANNA-DSB library:* new `EventContract` asset class plus codesets for `EventType`, `JurisdictionOfEvent`, `EventOracleRegistry`. *UTI generation rules:* the ISO 23897 shape is preserved but the namespace LEI must be that of the DCM or resolving oracle — event contracts frequently have only one named legal party (T026 and T028 have `other_counterparty_lei: null`), breaking the bilateral-LEI assumption in current guidance. *SDR infrastructure:* lifecycle action types `RESOLVED_YES` / `RESOLVED_NO` and a new `oracle_attestation_hash` field that anchors each resolution to a verifiable cryptographic statement, removing the DCM's unilateral authority.

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
