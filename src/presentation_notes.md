# Recorded Presentation — Speaker Notes

Audio-only MP3, **5-minute hard limit**, four segments in order. Pace ≈ 150 wpm; each segment's word budget is sized for the allotted time. Have `output/compliance_report_all.json` open during Segment 1 so you can read off T026 verbatim.

| Segment | Time | Word budget |
|---|---|---|
| 1. Live demo | 90 sec | ~225 words |
| 2. One finding | 60 sec | ~150 words |
| 3. Policy argument | 90 sec | ~225 words |
| 4. What the engine cannot see | 60 sec | ~150 words |
| **Total** | **5:00** | **~750 words** |

---

## Segment 1 — Live demo (90 sec)

**On-screen prep:** have `output/compliance_report_all.json` open, scrolled to the T026 record. If you can do screen-capture, also have `output/upi_lookup_all.json` available; otherwise narrate from the compliance report.

**Speak (paced for 90 sec):**

> I'm running the engine on trade T026 — a binary event contract on Kalshi, paying one US dollar if the AfD wins more than thirty percent of the vote in the 2025 German federal election. A corporate treasurer holds it to hedge a renewable-energy subsidy exposure.
>
> Module 1 classifies T026 as asset class `EventContract` — outside the ANNA-DSB taxonomy — and tags it `NOVEL_INSTRUMENT_NO_TAXONOMY`. No crash. Clean flag.
>
> Module 2 sees the novel flag and bypasses template lookup. Status `NO_PRODUCT_DEFINITION`, `matched_template: null`, `upi_code: null`, plus a structured `classification_note` explaining that prediction contracts sit outside the OTC derivatives taxonomy.
>
> Module 3 then applies the jurisdictional applicability rule. Platform type is `CFTC_REGULATED_DCM`, so CFTC returns `CONDITIONAL` — pending the CFTC's ANPR 91 FR 12516. MAS returns `NOT_APPLICABLE` — Singapore doesn't classify event contracts as OTC derivatives.
>
> The audit trail matters. Even though the applicability rule set the status, the engine still ran every required field check — `field_validations` shows `upi: missing`, `effective_date: missing`, `maturity_date: missing`, `other_counterparty_lei: missing`. These don't drive the status, but they tell you *why* the trade wouldn't be cleanly reportable even if classification flipped tomorrow.
>
> That's a reasoned status on an instrument the taxonomy can't describe, without crashing and without papering over the gap.

*(~210 words. Target landing: 1:30.)*

---

## Segment 2 — One finding (60 sec)

**Speak:**

> The single most interesting result from the full 34-trade run is what the engine surfaces about LEI quality.
>
> The portfolio uses eight distinct counterparty LEIs. **Three of them fail ISO 7064 MOD 97-10** — specifically, `2138002TXD6KSZ3V5X27`, `9695009AXSRNHZE85Y20`, and `4R3ZURLYISNNNMHMK608`. They look like real LEIs. They aren't. The check digits don't compute.
>
> That cascades through the portfolio. Of thirty-four trades, **twenty-six** fail compliance because at least one counterparty's LEI fails the checksum. Even T001 — the spec example trade — comes back NONCOMPLIANT, because its counterparty LEI is one of the three bad ones.
>
> What it tells me: somewhere upstream, the booking system is treating LEI as a free-text field. A ten-line GLEIF live-API check at trade capture would have prevented every one of those failures from reaching the SDR. The engine is doing its job by surfacing the problem — but the problem is in the trade-onboarding layer, not the reporting layer.

*(~155 words. Target landing: 2:30.)*

---

## Segment 3 — Policy argument (90 sec)

**Speak:**

> My position on T026, T027, and T028: **these are derivatives in everything except their regulatory label, and the prohibition that classifies them as gambling in Europe is an oversight, not a policy decision.**
>
> Take T026. The reporting party is a corporate treasurer. The trade record names the exposure — "German renewable energy subsidy regime materially affected by election outcome." Apply Brandes's three-question test from his 2026 policy brief. Identifiable actor with measurable contractual exposure? Yes — a renewables firm whose subsidy regime depends on the election. Would the contract let that actor manage the exposure? Yes — a binary on AfD vote share offsets subsidy-rollback risk. Continuously updated probability information beyond polls? Yes — intraday, instead of multi-day Infratest dimap or Forsa lags.
>
> The trade performs a hedging function and a price-discovery function — the two functions that justify every other derivative on Eurex.
>
> But our engine returns MAS `NOT_APPLICABLE`, and Germany treats it as illegal gambling under the Glücksspielstaatsvertrag. Brandes's strongest argument: this classification *preceded any analysis of the instrument's economic function*. Quote: "They can vote. They cannot hedge."
>
> The fix is not abolishing gambling law. It's recognising that some instruments classified as gambling are performing functions gambling law was never designed to prohibit. Regulate them. Don't ban them.

*(~210 words. Target landing: 4:00.)*

---

## Segment 4 — What the engine cannot see (60 sec)

**Speak:**

> One specific systemic risk that is **completely invisible** to a compliance engine built on the current taxonomy.
>
> Kalshi processed over **thirteen billion US dollars in notional volume in March 2026 alone**. Annualised, that's roughly one hundred and fifty-six billion US dollars in event-contract activity. **Not a single dollar of that volume hits any SDR**, anywhere in the world, because the ANNA-DSB taxonomy contains no `EventContract` asset class. When our engine processes T026, T027, T028 — and our new T034 — it returns `NO_PRODUCT_DEFINITION`. Technically correct. Substantively, a silent miss.
>
> Plus the EU-origin Polymarket flows: T027 in our portfolio routes through VPN bypass to access an offshore platform. Brandes cites Polymarket's $10.5 million Venezuela non-resolution as the precedent for what "no recourse" actually means in practice.
>
> The engine is faithful to the taxonomy. The taxonomy is the problem. Until ANNA-DSB defines an `EventContract` asset class — which is exactly the schema we propose in Section 4B — this volume continues to grow outside any reporting perimeter.

*(~165 words. Target landing: 5:00.)*

---

## Delivery checklist

- **Record at 16-bit / 44.1 kHz mono MP3.** Quality is fine; file size stays small.
- **Speak from notes, don't read.** Mark stresses on numbers and trade IDs.
- **Pause between segments** — half-second beat — so the marker can hear the seams.
- **Time yourself once before the take.** Aim for 1:25 / 2:25 / 3:55 / 4:55 cumulative marks.
- **If you run long in Segment 3**, drop the "is the strongest reason" parenthetical and the "Brandes's argument" attribution clause — saves ~10 seconds.
- **If audio-only, no screen share**, narrate the demo in present tense ("I'm reading the T026 record now…") so the marker hears the action rather than missing it.
- **Submission:** MP3 or MP4. Upload to your team's Google Drive / OneDrive; paste the share link into the README, top of the file, before submitting the GitHub URL to the lecturer.

## What NOT to do (per the brief)

- Don't rearrange the four segments — strict order.
- Don't run over 5:00 — automatic penalty.
- Don't summarise all 34 trades in Segment 2 — pick one finding only.
- Don't argue "should they be permitted or not" in Segment 3 — Brandes already grants regulation. Argue *how* they should be classified.
