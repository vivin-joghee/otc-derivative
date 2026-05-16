# Recorded Presentation Script — Final
## OTC Derivative Compliance Engine | MH6822 Assignment 2
**5-minute hard limit | Audio-only | Four segments in order**

| Segment | Time | Word budget |
|---|---|---|
| 1. Live demo | 0:00 – 1:30 | ~225 words |
| 2. One finding | 1:30 – 2:30 | ~150 words |
| 3. Policy argument | 2:30 – 4:00 | ~225 words |
| 4. What the engine cannot see | 4:00 – 5:00 | ~150 words |

---

## Segment 1 — Live Demo [0:00–1:30] (90 seconds)

*Have `output/compliance_report.json` open, scrolled to the T026 record.*

---

I'm running the engine on trade **T026** — a binary event contract on Kalshi, paying out if the AfD wins more than thirty percent of the vote in the 2025 German federal election. A corporate treasurer holds it to hedge a renewable-energy subsidy exposure.

**Module 1** classifies T026 as asset class `EventContract` — outside the ANNA-DSB taxonomy — and tags it `NOVEL_INSTRUMENT_NO_TAXONOMY`. The parser never crashes. It produces a clean structured record with that flag, a parse status of SUCCESS, and no parse errors.

**Module 2** sees the novel flag and bypasses template lookup entirely. The output shows `status: NO_PRODUCT_DEFINITION`, `matched_template: null`, `upi_code: null`, and a structured `classification_note` explaining that prediction contracts sit outside the OTC derivatives taxonomy in most jurisdictions.

**Module 3** then applies the jurisdictional applicability rule. T026's platform type is `CFTC_REGULATED_DCM` — it's on Kalshi — so CFTC returns `CONDITIONAL`, pending the CFTC's advance notice of proposed rulemaking, ANPR 91 FR 12516. MAS returns `NOT_APPLICABLE` because Singapore does not classify event contracts as OTC derivatives.

The audit trail matters. Even though the applicability rule set the status, the engine still ran every required field check. Looking at `field_validations`: `upi` is missing, `effective_date` missing, `maturity_date` missing, `other_counterparty_lei` missing. These don't drive the CONDITIONAL status — but they tell you exactly why this trade wouldn't be cleanly reportable even if classification flipped tomorrow.

That's a reasoned output on an instrument the taxonomy cannot describe, without crashing, and without papering over the gap.

*(Target: land at 1:30)*

---

## Segment 2 — One Finding [1:30–2:30] (60 seconds)

---

The single most interesting result from the full 34-trade run is what the engine surfaces about **LEI quality**.

The portfolio uses eight distinct counterparty LEIs. Three of them fail ISO 7064 MOD 97-10 checksum validation — specifically `2138002TXD6KSZ3V5X27`, `9695009AXSRNHZE85Y20`, and `4R3ZURLYISNNNMHMK608`. They look like real LEIs. They aren't. The check digits don't compute.

That cascades through the portfolio. Of the 34 trades, **26 fail compliance** because at least one counterparty's LEI fails the checksum — including T001, the most straightforward fixed-float swap in the book. Its CFTC status is NONCOMPLIANT because of its counterparty's bad LEI, even though every other field is clean.

What this tells me: somewhere upstream, the booking system is treating LEI as a free-text field. A ten-line GLEIF live-API check at trade capture would have prevented every one of those failures from ever reaching the SDR. The engine is doing its job by surfacing the problem. But the problem lives in the trade-onboarding layer, not in the reporting layer.

*(Target: land at 2:30)*

---

## Segment 3 — Policy Argument [2:30–4:00] (90 seconds)

---

My position on T026, T027, and T028: **these are derivatives in everything except their regulatory label, and the classification that excludes them is based on surface-level resemblance to gambling — not on any analysis of their economic function.**

Take T026. The reporting party is a corporate treasurer. The trade record explicitly names the exposure — the German renewable energy subsidy regime, materially affected by the election outcome. Apply the three-question functional test from Brandes's 2026 policy brief. Is there an identifiable actor with a measurable contractual exposure? Yes — a renewables firm whose subsidy revenue depends on who wins the Bundestag. Would the contract let that actor manage that exposure? Yes — a binary on AfD vote share offsets subsidy-rollback risk directly. Is there continuously updated probability information that goes beyond what polls provide? Yes — intraday, versus the multi-day lag of Infratest dimap or Forsa.

The trade performs a hedging function and a price-discovery function — the same two functions that justify every other derivative on Eurex. Yet Germany classifies it as gambling under the Glücksspielstaatsvertrag, and MAS returns `NOT_APPLICABLE` because EventContract falls outside Singapore's OTC derivatives taxonomy.

Brandes's point, and mine, is that this classification **preceded any analysis of the instrument's economic function**. The fix is not to abolish gambling law. It is to add `EventContract` as a sixth asset class in the ANNA-DSB UPI library, with `BinaryEventContract` as the instrument type and `PoliticalOutcome`, `MacroeconomicOutcome`, and `RegulatoryDecisionOutcome` as use-case codes — exactly what our Module 4 schema proposes. Once the taxonomy exists, the UPI mechanism works, UTI generation applies, and SDR reporting follows automatically.

*(Target: land at 4:00)*

---

## Segment 4 — What the Engine Cannot See [4:00–5:00] (60 seconds)

---

One specific systemic risk that is **completely invisible** to a compliance engine built on the current taxonomy.

Kalshi processed over **thirteen billion US dollars in notional volume in March 2026 alone**. Annualised, that is roughly one hundred and fifty-six billion dollars in event-contract activity. Not a single dollar of that hits any SDR, anywhere in the world, because the ANNA-DSB taxonomy has no `EventContract` asset class. When our engine processes T026, T027, and T028, it returns `NO_PRODUCT_DEFINITION`. Technically correct. Substantively, a silent miss.

Add the EU-origin Polymarket flows on top. T027 in our portfolio routes through a VPN bypass to access Polymarket — an offshore, unregulated venue. The engine correctly returns `NOT_APPLICABLE` under both CFTC and MAS. Polymarket's $10.5 million Venezuela non-resolution shows exactly what "no recourse" means in practice when something goes wrong on an unregulated platform.

The engine is faithful to the taxonomy. The taxonomy is the problem. Until ANNA-DSB defines an `EventContract` asset class — with `ReferenceSource` codeset-validated against an EventOracleRegistry — this volume keeps growing entirely outside any reporting perimeter.

*(Target: land at 5:00)*

---

## Delivery Checklist

- **Pace:** ~150 words per minute. Read each segment aloud once before recording.
- **Cumulative timing marks to hit:** 1:25 / 2:25 / 3:55 / 4:55
- **If Segment 3 runs long:** drop the "Apply the three-question functional test" sentence and go straight to the three answers — saves ~12 seconds.
- **If audio-only with no screen share:** open with "I'm reading the T026 record now from the compliance report output…" so the listener follows.
- **Speak numbers slowly:** "thirteen billion", "twenty-six trades", "ninety-seven ten" — these are your evidence; don't rush them.
- **Pause half a second between segments** so the marker hears the seam.
- **Record:** 16-bit / 44.1 kHz mono MP3. Upload to Google Drive or OneDrive with view access, paste the link into the top of your README before submitting the GitHub URL.

## What NOT to Do (per the brief)
- Do not rearrange the four segments.
- Do not run over 5:00.
- Do not summarise all 34 trades in Segment 2 — one finding only.
- Do not argue whether prediction markets should be permitted — argue *how* they should be classified.
