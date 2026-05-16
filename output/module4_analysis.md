# Module 4 — Classification Analysis: Prediction Contracts and the Reporting Frontier

This section answers the four sub-tasks of Module 4 against the three event-contract trades in the portfolio (T026–T028). Citations are inline-APA; the references block sits at the end.

---

## 4A. Economic Function Test

Brandes (2026) argues that a prediction contract must be evaluated by its economic function — hedging, price discovery, risk transfer — *before* being assigned to a regulatory category. Applying his three-question test to the three event-contract trades:

**T026 — CorporateTreasury on AfD vote share ≥ 30 %, Kalshi. Underlying exposure to the German renewable energy subsidy regime is credible; EEG policy is materially contingent on coalition composition. The binary offsets subsidy-rollback risk no listed European derivative covers, and intraday Kalshi pricing provides informational value beyond Infratest dimap or Forsa polling cadence. All three questions are satisfied

**T027 — AssetManager_EU on US CPI ≥ 3 % Q3 2026, Polymarket. USD bond duration is a calculable inflation exposure; a YES payout partially offsets real yield compression. Polymarket CPI markets have demonstrated informational value beyond Bloomberg consensus. However, access_method: VPN_BYPASS_GGL_BLOCK records deliberate circumvention of access restrictions by an EU-regulated entity, rendering the contract unenforceable as a hedge under any EMIR-consistent framework. Q2 fails on legal enforceability grounds

**T028 — FinTechFirm_EU on ESMA AI Act Annex III classification, Kalshi. Compliance costs are contractually contingent on a single binary decision; the contract structure mirrors the exposure precisely. Cleared, UTI-assigned, and legally coherent. All three questions are satisfied.

**Conclusion.**  T026 and T028 satisfy the test. T027 fails solely on enforceability; its economic logic is otherwise sound.

---

## 4B. What Would a UPI Look Like? (Schema proposal for T028)

The ANNA-DSB UPI library currently recognises five asset classes; event contracts would require a sixth. T028 is used as the basis for the proposed schema.
For standard derivatives, ReferenceRate and NotionalCurrency identify what is referenced and when payment triggers. For event contracts the analogues are EventType and ReferenceSource — identifying what is observed and which authority resolves it — and EventThreshold identifying when payment triggers. ReferenceSource is the most critical attribute, playing the same anchoring role as FpmlRatesReferenceRate, validated against a named EventOracleRegistry rather than free text. ContractSize and SettlementDate are additionally required as UPI-defining attributes, the latter bounded at five years post-execution to limit long-tail political uncertainty. DeliveryType is CASH unconditionally.
Four validation constraints apply: EventDescription must be 20–500 characters referencing a specific, observable, time-bounded outcome; ReferenceSource must match the EventOracleRegistry codeset; SettlementDate must not exceed five years from execution; and JurisdictionOfEvent must correspond to the ReferenceSource jurisdiction.

{
  "AssetClass": "EventContract",
  "InstrumentType": "BinaryEventContract",
  "UseCase": "RegulatoryDecisionOutcome",
  "Level": "UPI",
  "Attributes": {
    "EventDescription":    { "type": "string", "minLength": 20, "maxLength": 500 },
    "EventType":           { "type": "string", "enum": [
                             "ELECTION_OUTCOME", "MACROECONOMIC_THRESHOLD",
                             "REGULATORY_DECISION", "JUDICIAL_DECISION"] },
    "JurisdictionOfEvent": { "type": "string", "codeset": "ISO3166CountryCode" },
    "ReferenceSource":     { "type": "string", "codeset": "EventOracleRegistry" },
    "SettlementCurrency":  { "type": "string", "codeset": "ISOCurrencyCode" },
    "ContractSize":        { "type": "number", "minimum": 0 },
    "SettlementDate":      { "type": "string", "format": "date",
                             "constraint": "<=5Y from execution" },
    "DeliveryType":        { "type": "string", "enum": ["CASH"] }
  }
}

## 4C. Jurisdictional Arbitrage and Regulatory Design

1. The Arbitrage and Its Beneficiaries
The gap is structural: Kalshi operates as a CFTC-regulated DCM, making political and macroeconomic event contracts legally tradeable for US persons, while EU member states classify identical instruments as gambling under national frameworks including the Glücksspielstaatsvertrag. The beneficiaries are Kalshi and Polymarket, which capture liquidity from EU participants their regulators cannot serve; and sophisticated EU actors including the AssetManager_EU in T027 and FinTechFirm_EU in T028, who access genuine hedging instruments unavailable domestically. The harmed parties are the same EU participants: T027's AssetManager_EU accesses Polymarket via VPN_BYPASS_GGL_BLOCK, forfeiting EMIR protections, clearing, and legal enforceability of what is otherwise a legitimate inflation hedge. Retail EU participants on offshore platforms bear the full counterparty and platform risk with no recourse.

2. RegTech Implementation: Operator Neutrality and Position Limits
Operator neutrality requires that platform operators cannot hold proprietary positions in contracts they list. Implementation demands real-time position reporting against a central registry, with validation logic flagging any operator LEI appearing on both sides of a trade record — the same mechanism as existing systematic internaliser flags under MiFID II.
Position limits require per-participant exposure caps calibrated to verifiable economic interest. The concrete mechanism is a notional-to-exposure ratio check at order submission: the reporting infrastructure must cross-reference the submitting LEI against a declared underlying exposure register, rejecting orders where notional exceeds a defined multiple of documented exposure.

3. Reporting Stack Changes
ANNA-DSB requires a new EventContract asset class with ReferenceSource and EventOracleRegistry codesets. UTI generation rules must accommodate non-ISIN underliers, replacing the current instrument-reference prefix with an EventID namespace. SDR infrastructure requires new ingestion fields for EventDeadline, ResolutionSource, and ThresholdType, with validation rejecting past-dated event deadlines at submission.

---

## 4D. Reflection on Engine Limits

The compliance engine surfaces LEI checksum failures and missing CDE fields. What it cannot see is structurally invisible: Kalshi's approximately USD 13 billion March 2026 monthly notional sits entirely outside any SDR because the ANNA-DSB taxonomy contains no EventContract asset class. EU-origin Polymarket flows, exemplified by T027's VPN_BYPASS_GGL_BLOCK access, are equally invisible. The engine returns NO_PRODUCT_DEFINITION for all three trades — technically correct, substantively a silent miss on what annualises to approximately USD 156 billion in unmonitored notional. 

UPI absence is a risk signal, not an exemption. A reported trade carrying no UPI should auto-flag for SDR review, as MiFIR flags instrument-identifier resolution failures. The current architecture treats classification gaps as silence; a well-designed framework treats them as observable indicators of regulatory perimeter failure.
If advising the CFTC on ANPR 91 FR 12516, two changes would be prioritised. First, define EventContract in the ANNA-DSB library using the schema proposed in 4B, so DCMs and SDRs share a common identifier model from implementation. Second, require oracle_attestation_hash and event_outcome_realisation fields in SDR data standards at contract resolution, making post-event settlement integrity auditable without granting any single venue unilateral authority over outcome determination

---

## References

Brandes, A. (2026). *The Unhedgeable State: Political Risk, Prediction Markets, and the Gap in Europe's Risk Management Architecture*. Policy Brief, April 2026.

Cassar, T. (2026). *Regulating Prediction Markets in Europe Requires a 'Prediction Test'*. Oxford Business Law Blog, 31 March 2026.

Commodity Futures Trading Commission [CFTC]. (2026). *Advance Notice of Proposed Rulemaking: Prediction Markets*. 91 FR 12516, RIN 3038-AF65, 16 March 2026.

Diewrcks, A. M., Katz, J. D., & Wright, J. H. (2026). *Kalshi and the Rise of Macro Markets*. NBER Working Paper No. 34702 / Federal Reserve Board FEDS 2026-010.

Glücksspielstaatsvertrag 2021 (GlüStV 2021). *Staatsvertrag zur Neuregulierung des Glücksspielwesens in Deutschland*, in force 1 July 2021.

Regulation (EU) No 596/2014 of the European Parliament and of the Council (MAR). *Official Journal of the European Union*, L 173, 12 June 2014.

Directive 2014/65/EU of the European Parliament and of the Council (MiFID II). *Official Journal of the European Union*, L 173, 12 June 2014.
