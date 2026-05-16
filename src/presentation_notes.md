# Recorded Presentation Script — Final
## OTC Derivative Compliance Engine | MH6822 Assignment 2
**5-minute hard limit | Audio-only | Four segments in order**

| Segment | Time | Word budget |
|---------|------|-------------|
| 1. Live demo | 0:00 – 1:30 | ~200 words |
| 2. One finding | 1:30 – 2:30 | ~130 words |
| 3. Policy argument | 2:30 – 4:00 | ~200 words |
| 4. What the engine cannot see | 4:00 – 5:00 | ~130 words |

---

## Segment 1 — Live Demo [0:00–1:30]

*Have `output/compliance_report.json` open, scrolled to the T026 record.*

---

We are running the engine on trade T026 — a binary event contract on Kalshi, paying out if a far-right party wins more than thirty percent of the vote in the 2025 German federal election. A corporate treasurer holds it to hedge a renewable energy subsidy exposure.

Module 1 classifies T026 as asset class EventContract wghich is outside the ANNA-DSB taxonomy — and flags it NOVEL INSTRUMENT, NO TAXONOMY. The parser does not crash. It produces a clean structured record with that flag and no parse errors.

Module 2 sees the novel flag and skips template lookup. The output shows NO PRODUCT DEFINITION, no matched template, no UPI code.

Module 3 applies the jurisdictional rule. T026 is on Kalshi, a CFTC-regulated exchange, so CFTC returns CONDITIONAL — pending the regulator's proposed rulemaking on prediction markets. MAS returns NOT APPLICABLE because Singapore does not classify event contracts as OTC derivatives.

Even with that CONDITIONAL status, the engine still ran every field check. If UPI missing, effective date missing, maturity date missing or counterparty identifier missing. These do not change the status — but they show exactly why this trade would not be cleanly reportable even if classification changed tomorrow.

That is a reasoned output on an instrument the taxonomy cannot describe, without crashing, and without hiding the gap.

*(Target: land at 1:30)*

---

## Segment 2 — One Finding [1:30–2:30]

---

The single most interesting result from the full 34-trade run is what the engine surfaces about counterparty identifier quality.

The portfolio uses eight distinct Legal Entity Identifiers. Three of them fail ISO checksum validation. They look like real identifiers — they are not. The check digits do not compute.

That cascades through the portfolio. Of 34 trades, 26 fail compliance because at least one counterparty identifier is invalid which includes T001, the most straightforward interest rate swap in the book. NONCOMPLIANT because of one bad counterparty code, even though every other field is clean.

What this tells us is that the booking system is treating the legal entity identifier as a free-text field. A simple live validation check at trade capture would have prevented every one of those failures from reaching the regulator. The engine surfaces the problem — but the problem lives in the onboarding layer, not the reporting layer.

*(Target: land at 2:30)*

---

## Segment 3 — Policy Argument [2:30–4:00]

---

Our position on T026, T027, and T028: these are derivatives in everything except their regulatory label. The classification that excludes them is based on what they look like, not on what they actually do economically.

Take T026. The reporting party is a corporate treasurer with a named exposure — a renewable energy subsidy regime that depends on the election outcome. Three questions. Is there an identifiable party with a real exposure? Yes. Does the contract let them manage it? Yes — a binary on election vote share offsets the subsidy risk directly. Is there continuously updated market pricing beyond opinion polls? Yes — intraday, versus the multi-day lag of traditional polling firms.

The trade performs a hedging function and a price-discovery function — the same two functions that justify every other derivative on a regulated exchange. Yet Germany treats it as illegal gambling under national gaming law, and MAS returns NOT APPLICABLE because EventContract falls outside Singapore's taxonomy.

The classification came before any analysis of the economic function. The fix is taxonomic. Add EventContract as a sixth asset class in the ANNA-DSB library, with BinaryEventContract as the instrument type and use-case codes for political, macroeconomic, and regulatory outcomes. Once the taxonomy exists, UPI assignment works, and regulator reporting follows automatically.

*(Target: land at 4:00)*

---

## Segment 4 — What the Engine Cannot See [4:00–5:00]

---

One systemic risk that is completely invisible to a compliance engine built on the current taxonomy.

Kalshi processed over thirteen billion US dollars in notional volume in March 2026 alone — roughly one hundred and fifty-six billion annualised. Not a single dollar hits any trade repository because the taxonomy has no EventContract asset class. When our engine processes T026, T027, and T028, it returns NO PRODUCT DEFINITION. Technically correct. Substantively a silent miss.

T027 in our portfolio routes through a VPN bypass to an offshore, unregulated platform. The engine returns NOT APPLICABLE under both CFTC and MAS. A previous incident on that same platform — a ten-point-five million dollar contract that failed to resolve — shows exactly what no recourse means outside any regulatory perimeter.

The engine is faithful to the taxonomy. The taxonomy is the problem.

*(Target: land at 5:00)*

---

## Delivery Notes

- **Pace:** ~150 words per minute. Do a full read-through before recording.
- **Cumulative marks to hit:** 1:25 / 2:25 / 3:55 / 4:55
- **If Segment 3 runs long:** drop the three-question breakdown, state the conclusion directly — saves 10 seconds.
- **Speak numbers slowly:** "thirteen billion", "twenty-six trades", "thirty percent."
- **Pause between segments** so the marker hears the seam.
