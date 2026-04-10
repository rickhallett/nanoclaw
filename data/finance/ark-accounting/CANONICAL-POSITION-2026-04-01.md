# Canonical Financial Position
**As of: 2026-04-01**
**Status: CURRENT -- this is the single source of truth**

All prior spreadsheet data (raw_sheet.json, debts.csv, cost_items.csv, balance_updates_staging.csv, assets_working.csv) is HISTORIC. Reference this file first. Update this file when numbers change. Do not reconstruct from the spreadsheets.

---

## Liquid

| Account | Balance |
|---------|---------|
| Barclays current | 1,047.74 |
| Monzo Business | 4,426.52 |
| Barclays Savings | 0.56 |
| PS5 sale (received) | 350.00 |
| **Total cash** | **5,824.82** |

Pending:
- Aurora R9 eBay sale: ~400 (not yet listed)

Projected liquid after all sales: ~6,224

## Debt

| Creditor | Balance | APR (est) | Monthly interest | Min payment | Notes |
|----------|---------|-----------|-----------------|-------------|-------|
| Virgin credit card | 11,546.23 | ~35% | ~337 | 45.49 | PROMO EXPIRED (assumed). Min does not cover interest. Will be forced up by lender. Highest-risk line. |
| Iwoca loan | 6,231.28 | ~37% | ~194 (Apr/May) | 193.83 (Apr), 187.57 (May) | Interest-only until June. Jumps to 622.19/mo from June (P+I). See iwoca_schedule.csv for full amort. |
| MBNA Loan 2 | 5,289.53 | ~15% | ~66 | UNKNOWN | Payment schedule unknown. Gap in data. Confirm. |
| AMEX credit card | ~3,120 | ~23% | ~60 | UNKNOWN | 64GB mini returned (-869). M5 return CANCELLED (keeping as primary machine). |
| MBNA credit card | 3,701.45 | ~22% | ~68 | UNKNOWN | Revolving. |
| Capital On Tap | 3,425.69 | ~27% | ~77 | 336.52 | Business credit card. Min confirmed from 18 Mar 2026 statement. |
| M3 Max (Klarna) | 441.78 | 0% | 0 | 160.00 | Nearly done. ~3 payments left. |
| **Total debt** | **~32,372** (post-returns) | | **~775/mo** | | |

## Hardware Decisions (committed 2026-04-01)

| Item | Action | Value | Status |
|------|--------|-------|--------|
| PS5 | SOLD | 350 cash | Done |
| 64GB mini (Amazon) | RETURNED | -869 off AMEX | Done. |
| M5 MacBook Air (Amazon) | KEEPING | -- | X1 Carbon wifi/BT unreliable on Arch. M5 is primary machine. 1,384 stays on AMEX. |
| Aurora R9 | SELL (eBay) | ~475 asking | Listed 2026-04-02. Collection only. |
| ThinkPad X1 Carbon 9th Gen | SELL (eBay) | ~480 asking | Listed 2026-04-02. Was daily driver. |
| ThinkPad X230 i5 16GB | SELL (eBay) | ~170 asking | Listed 2026-04-02. |
| Nipogi 32GB mini | SELL (eBay) | ~365 asking | Listed 2026-04-02. Was desktop dev server. |
| Lenovo Legion Y27q-25 240Hz | SELL (eBay) | ~200 asking | Listed 2026-04-02. Collection only. |
| Mac Mini 5 (2011) | SELL (eBay) | ~70 asking | Listed 2026-04-02. |

Total eBay asking: ~1,760. Realistic net after fees/negotiation: ~1,300.
Total swing from hardware: ~1,619 (revised down from ~3,003 -- M5 return cancelled)

## Monthly Burn (actual)

### Living: ~994/mo

| Category | Monthly |
|----------|---------|
| Food | 450.00 |
| Supplements | 110.00 |
| Pharmaceuticals | 200.00 |
| Prescription | 11.45 |
| EE contract | 42.20 |
| Broadband | 29.13 |
| iPhone device | 24.10 |
| Cursor | 20.00 |
| Spotify | 16.99 |
| YouTube Premium | 15.99 |
| Google One | 14.00 |
| Setapp | 11.56 |
| Prescription cert (NHSBSA) | 11.45 |
| iCloud+ | 8.99 |
| Prime | 8.99 |
| Indemnity insurance | 6.57 |
| AppleCare+ | 4.99 |
| 1Password | 3.65 |
| HBI | 2.00 |
| PayPal misc | 1.99 |
| **Living total** | **~994** |

### Debt service: ~1,286/mo (current, pre-June)

| Creditor | Payment | Type |
|----------|---------|------|
| Capital On Tap | 336.52 | Min (P+I) |
| MBNA Loan 1 | 305.00 | Min (P+I) |
| Iwoca (Apr/May) | 193.83 | Interest only |
| Klarna M3 Max | 160.00 | Principal only (0%) |
| Virgin | 45.49 | Min (does NOT cover interest) |
| MBNA Loan 2 | ? | UNKNOWN |
| AMEX | ? | UNKNOWN |
| **Debt service total** | **~1,286** (known) | |

### Total burn: ~2,280/mo (current, pre-June)

### June step-up: Iwoca jumps from ~194 to 622/mo
- Debt service rises to ~1,714/mo
- Total burn rises to ~2,708/mo

## Interest Summary

| Creditor | Monthly interest |
|----------|-----------------|
| Virgin (35%) | ~337 |
| Iwoca (37%) | ~194 |
| Capital On Tap (27%) | ~77 |
| MBNA credit card (22%) | ~68 |
| MBNA Loan 2 (15%) | ~66 |
| AMEX (23%) | ~33 |
| Klarna | 0 |
| **Total interest** | **~775/mo** |

Of the ~2,280/mo going out, 775 is pure interest. Money on fire.

## Runway

| Scenario | Months | Date |
|----------|--------|------|
| To buffer floor (3k) at current burn | ~2.1 | Mid-June 2026 |
| To buffer floor at June burn (2,708) | ~1.0 from June | Mid-July 2026 |
| To zero at current burn | ~3.9 | Late July 2026 |

June is the wall. Iwoca step-up changes the maths.

## The Conversation (parent briefing)

"Right now I'm spending about 2,300 a month. 1,000 is living costs. 1,300 is debt payments. Of that 1,300, about 775 is pure interest.

In June it gets worse. Iwoca repayments jump from 194 to 622. Monthly burn goes to 2,700.

I've sold the PS5, I'm returning the new machines to Amazon, and listing the gaming PC. That clears about 3,000. I'm keeping a laptop and a desktop -- both already paid for.

At current cash of 5,800, that's about two months before I hit my safety buffer. Without income by June, the maths stops working.

I'm interviewing at Neo4j. Pipeline is active."

## Outstanding Data Gaps

1. **MBNA Loan 2**: payment schedule, minimum, current status
2. **AMEX minimum**: what is the actual min payment post-returns?
3. **Virgin promo**: assumed expired at 35%. Confirm actual rate.
4. **MBNA credit card minimum**: unknown

Fill these and update this file. Do not go back to the spreadsheets.

---

*Previous data sources (raw_sheet.json, debts.csv, cost_items.csv, balance_updates_staging.csv, assets_working.csv, debts_working.csv) are HISTORIC as of this date. They may contain stale balances and incomplete debt entries. This file supersedes all of them.*

---

## StepChange Assessment (2026-04-07)

Completed online StepChange debt assessment. Results:

### Recommended

- **Payment Suspension** — voluntary agreement with creditors to pause non-priority debt payments for a short period. Recommended option.

### Available but not recommended

- **DRO (Debt Relief Order)** — available. Writes off all debts after 12-month moratorium. 90 fee. StepChange did not recommend; specific objection unknown. To be clarified via follow-up call.
- **Bankruptcy** — available. Writes off all debts. 680 fee. Not recommended by StepChange.

### Not available

- **DMP** — no surplus in budget
- **IVA** — creditors unlikely to accept (paying too little)
- **Settlement offers** — asset value too low
- **Monthly payment arrangement** — no surplus in budget
- **Administration order** — debt too high, no CCJ, no surplus

### Mental health disclosure

StepChange flagged mental health pathway. Diagnosed: bipolar type II NOS (cyclothymia), GAD with compulsive traits. Medications: fluoxetine 40mg OD, lamotrigine 200mg, pregabalin 300mg BD. Mental Health Breathing Space (statutory, not voluntary) may be available — requires mental health professional certification. Materially different from payment suspension: creditors legally required to freeze interest/charges/enforcement for 30 days, renewable indefinitely during treatment.

### Agreed decision sequence (2026-04-07)

1. **Immediate:** Call StepChange mental health line (0333 252 4124). Ask two questions: (a) does Mental Health Breathing Space apply, (b) does mental health context change DRO recommendation.
2. **Primary play:** Mental Health Breathing Space. If granted, burn drops from ~2,280/mo to ~994/mo (living only). Runway extends to ~5 months from today.
3. **Backstop:** Bankruptcy. File BEFORE June if Breathing Space fails or creditors refuse. Iwoca step-up in June adds 428/mo — filing before June means never paying it.
4. **Employment remains the structural exit** but is not the plan. It is the upside scenario.

### Bankruptcy scenario analysis

| Factor | Detail |
|--------|--------|
| Cost | 680 (affordable from current liquid) |
| Debt eliminated | ~32,000 |
| Interest eliminated | 775/mo permanently |
| Post-bankruptcy burn | ~994/mo (living only) |
| Runway post-bankruptcy to floor | ~2.4 months from ~5,370 |
| Runway post-bankruptcy to zero | ~5.4 months |
| Credit impact | 6 years on file. Prior bankruptcy on record. |
| Employment impact | Cannot be company director during bankruptcy. Target roles (senior full-stack, remote) almost certainly unaffected. |
| Asset risk | Trustee reviews assets. M5 MacBook likely exempt as work tool. Cash above "reasonable needs" may be claimed. |
| What it does not cost | Skills, pipeline, agency prospects, earning ability, MacBook (probably) |

### Key insight

At 146 applications with no offer, probability of employment within runway is uncertain. Every day without income costs 76/day burn + 26/day pure interest = 102/day to preserve a credit score not needed for stated life trajectory (digital nomad, no mortgage, agency via business account). The arithmetic favours insolvency over hope.

## StepChange Call with Conner (2026-04-07, 19:50)

Recording transcribed: `/tmp/stepchange-transcript/19-50-57.txt`

### Bankruptcy — answers received

1. Family paying bills directly on your behalf during bankruptcy: OR has no claim. Money paid into YOUR account: must be negotiated with OR.
2. Surplus income threshold for IPA: must be negotiated with OR. StepChange cannot advise on specifics.
3. DRO and IPA risk: same answer — StepChange cannot confirm whether DRO carries same IPA exposure.
4. Mental Health Breathing Space: effectively unavailable for this situation. Requires crisis-level MH presentation. Not pursued.

### Decision: Payment Suspension

Proceeding with payment suspension. Mechanism:
- Download Personal Action Plan PDF from StepChange dashboard
- Email to all creditors
- Request 6-12 month suspension of payments
- Voluntary on creditor side, but StepChange backing gives weight
- Freezes collections, further processing, and interest accrual (if creditor agrees)

### Collections escalation ladder (from Conner, A-Z)

1. 1-3 missed payments: letters and reminders
2. Creditor sells debt to collection company + default notice (6 years on credit file, 14 days to respond)
3. Collection companies: easier to deal with — debt bought cheap, accept small payments for long periods, all profit
4. If no arrangement: pre-action protocol letter → County Court Judgement (6 years on credit file)
5. Beyond CCJ: attachment of earnings, bailiffs, charging orders on property (N/A — no property owned)

### Fallback if suspension expires without income

- Offer £1/month goodwill gesture to each creditor
- Creditors may sell debt to collection companies at that point
- Collection companies negotiate from a weaker position (bought debt at discount)
- Reassess insolvency options from a position with no surplus income for OR to claim

### Next actions

1. Download Personal Action Plan PDF from StepChange dashboard — TONIGHT
2. Email PDF to all creditors — TOMORROW
3. If income arrives during suspension: call StepChange, redo budget, assess long-term solutions
4. If no income by suspension end: £1/month offers, let process run, reassess insolvency
5. Conner offered follow-up calls as needed: 0800 048 1004

---

## Canonical B: Bankruptcy Architecture (2026-04-10)

**Status: UNDER CONSIDERATION — nothing decided. Requires IP consultation before action.**

### Thesis

File bankruptcy before June (dodge Iwoca step-up). Eliminate ~32k debt. Survive 12-month bankruptcy period at or below assessed needs threshold. Discharge clean. No IPA.

Credit rating sacrifice is assessed as irrelevant to stated trajectory (digital nomad, no mortgage, agency via business account).

### Needs threshold engineering

The OR assesses income against "reasonable domestic needs" using Common Financial Statement guidelines. If no surplus exists, no IPA is imposed. The strategy depends on legitimately raising assessed needs to a liveable figure:

| Expense | Monthly | Basis |
|---------|---------|-------|
| Living (food, meds, bills, subs) | ~994 | Current canonical burn minus debt service |
| Rent to parents | ~400-500 | Parents have genuine financial needs; adult child paying rent is recognised expense |
| Car (lease, insurance, fuel) | ~300-500 | Rural area, no public transport, needed for work and social independence |
| **Assessed needs (target)** | **~1,700-2,000** | |

At ~2,000/mo needs, earnings up to ~28-30k salary produce zero surplus. No surplus = no IPA.

### Earning during bankruptcy

- Employment and self-employment are both permitted during bankruptcy.
- Cannot be a company director — sole trader only (no Ltd).
- Self-employment: legitimate business expenses (compute, software, hosting) reduce assessable income before surplus calculation.
- Contractor model: company pays e.g. 2,500/mo, minus 500/mo business costs = 2,000/mo personal income = at threshold.
- Companies do not credit-check contractors. The bankruptcy is operationally invisible to clients.
- "Senior full-stack at sub-market rate" is an absurd bargain for the buyer. The pitch works.

### Family rent — risk factors

- OR scrutinises payments to "connected persons" (family).
- Rent must be genuine, at or below market rate, and not a mechanism to absorb surplus.
- Parents' own financial need is documentable and strengthens the case.
- This is the highest-risk element of the architecture. IP must confirm.

### Agency pilots during bankruptcy window

- Aura + Zodiac.fm pilots: ~500/mo combined revenue, ~24/mo compute cost.
- Sub-threshold income. Portfolio-building, not cash-flow play.
- Sole trader permitted. Business expenses further reduce assessable income.
- Post-discharge (month 13+): pivot to full-rate clients (1k setup + 1k/mo retainer). No OR involvement.

### Sequence (proposed, pending IP validation)

1. IP consultation this week — confirm needs assessment, IPA trigger point, family rent treatment, self-employment rules
2. If architecture holds: file bankruptcy before June (avoid Iwoca 622/mo step-up)
3. 12-month window: agency pilots + sub-threshold contracting + portfolio building
4. Month 13: discharge. Earn freely. Scale agency. Take full-rate roles.

### vs Canonical A (Payment Suspension)

| Factor | Suspension | Bankruptcy |
|--------|-----------|-----------|
| Debt eliminated | No — deferred | Yes — written off |
| Interest | May continue accruing | Eliminated |
| OR involvement | None | Yes — 12-month oversight |
| Earning restriction | None | Must stay below needs threshold |
| Cost | 0 | 680 |
| Credit impact | Defaults (6 years) | Bankruptcy (6 years) |
| Iwoca June step-up | Still due unless creditor agrees | Never paid |
| Risk | Creditors may refuse suspension | OR may impose IPA if income exceeds needs |

### Open questions for IP

1. Realistic needs assessment for: rural, living with parents, car needed for work — what figure will the OR accept?
2. At what income does IPA typically trigger given those needs?
3. Family rent: what amount is defensible without challenge?
4. Self-employment: how are business expenses treated in surplus calculation?
5. Timing: any advantage to filing before vs after payment suspension emails are sent?
6. DRO (90 fee, same write-off): does it carry the same IPA exposure? StepChange couldn't answer this.
