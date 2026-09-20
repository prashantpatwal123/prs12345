# ₹10K Monthly Capital Multiplier — Operating Runbook

This file is the contract. Any session picking up this repo reads this first and
follows it exactly. It encodes the owner's rules, not the agent's preferences.

Owner contributes **₹10,000 of fresh capital per month**. Objective: maximum
risk-adjusted capital growth, with active search for asymmetric opportunities.
Not guaranteed returns. Not a forced doubling on a deadline.

---

## 0. Environment constraints — read before wasting time

Verified on 2026-09-20 in the Claude Code remote container:

| Capability | Status |
|---|---|
| Groww account access | **None.** No connector exists. Portfolio is maintained here manually. |
| `WebFetch` | **Blocked** for every domain by the egress proxy, including BSE, NSE, SEBI, company IR, and Wikipedia. |
| `curl` / direct HTTP | **Blocked.** Returns `HTTP 403 on CONNECT tunnel`. |
| `WebSearch` | **Works.** This is the only external data channel. |
| Container persistence | **None.** Reclaimed after inactivity. Anything not committed and pushed is lost. |
| Scheduled wake-ups | **Works** via `mcp__Claude_Code_Remote__create_trigger`. |

Consequences that must be stated in every report, not quietly ignored:

- The owner's instruction to prefer NSE / BSE / SEBI / annual reports /
  quarterly filings / credit-rating reports **cannot be honoured.** Everything
  runs on search-index extracts.
- Search indexes have produced hard factual errors in this project: a silver
  price off by 2.4x, a P/B quoted as both 163.83 and 2.06, a share count off by
  2x that inverted a P/E from 13x to 24x. **Always cross-check a number against
  a second independent source before acting on it.** Where two sources conflict,
  say so and use the more conservative figure.
- No figure from this system is an execution-grade number. The owner verifies on
  their own terminal before placing any order.

## 1. Hard prohibitions

Never place an order, buy, sell, transfer money, or change account or security
settings. There is no mechanism to do so here and there must not be. The agent
researches and reports. **The owner makes every transaction decision.**

## 2. Files

| File | Purpose |
|---|---|
| `contributions.csv` | Fresh capital in. One row per ₹10,000. |
| `transactions.csv` | Every buy and sell, with charges. Owner updates after each trade. |
| `holdings.csv` | Current positions and operational status. |
| `tracker.py` | Computes invested, value, cash, P&L, capital multiple, XIRR. Run it; never do this arithmetic by hand. |
| `THESIS.md` | One thesis block per holding. The reason the position exists. |
| `RESEARCH-LOG.md` | Candidates examined and rejected, with dates and reasons. Prevents re-litigating settled questions. |

Run `python3 portfolio/tracker.py` for the numbers. Ignore XIRR until the
portfolio is ~12 months old — over short periods it annualises noise into
absurd figures and means nothing.

## 3. Daily scan (trading-day mornings, pre-open)

Indian market opens 09:15 IST. Skip weekends and NSE holidays.

**Engine A — portfolio monitor.** For every position: latest price, previous
close, average cost, P&L in ₹ and %, 52-week position, unusual volume. Then look
for anything that could change the *thesis*: filings, results, order wins or
losses, promoter and insider transactions, bulk/block deals, rating changes,
debt changes, management commentary, regulation, commodity moves, sector and
macro developments.

**Price movement alone is never a thesis change.** Do not manufacture
significance from ordinary fluctuation.

**Engine B — opportunity radar.** Scan across Nifty 50, Next 50, midcaps,
smallcaps, liquid microcaps, PSUs, turnarounds, special situations, demergers,
temporary distress, cyclical recoveries. Looking for: earnings acceleration,
large order wins, capacity coming online, debt reduction, promoter buying,
institutional accumulation, margin expansion, FCF inflection, asset
monetisation, restructuring, regulatory resolution, temporary overreaction,
undervalued assets, cash-rich balance sheets, business transformation.

Report an Engine B candidate **only if it is genuinely compelling.** An empty
radar is a valid and common result. Never fill the slot to look productive.

## 4. Position status

Exactly one of: `HOLD` · `WATCH CLOSELY` · `REVIEW FOR REDUCTION` ·
`EXIT THESIS TRIGGERED`.

Never change status because a different stock rose faster. Any change must name
the specific evidence that caused it, and that evidence goes in `THESIS.md`
under the position's change log.

## 5. Multibagger test — mandatory arithmetic

Nothing is called a potential 2× without this bridge shown in full:

```
current market cap · current PAT · current P/E
expected PAT in 2–3 years · defensible future P/E
implied market cap = expected PAT × future P/E
implied price = implied market cap ÷ share count
```

Then state what specifically must happen for the expected PAT and the future
P/E, separately. **"It traded there before" is not a thesis and is banned as a
primary argument.** A multiple above a company's own historical range needs an
explicit reason, not optimism.

Share count is the most common source of error. Derive it two ways — market cap
÷ price, and PAT ÷ EPS — and reconcile before trusting any per-share figure.

## 6. Quality filter for new positions

Revenue growth · PAT growth · operating cash flow · free cash flow · ROE ·
ROCE · debt · interest coverage · promoter holding · promoter pledge ·
institutional ownership · dilution history · receivables · auditor changes ·
related-party transactions · credit ratings · management guidance.

Note honestly which of these could not be verified. Auditor changes and
related-party transactions are effectively unverifiable in this environment —
say so rather than implying a clean check.

Reject on sight: a low P/E on peak or expiring earnings; a low P/B justified by
a low ROE; a low share *price* mistaken for a low *valuation*; interest coverage
under ~2x dressed up as a growth story.

## 7. Rotation engine

Do **not** propose A → B on momentum. Propose a rotation review only when one of
these holds:

1. A's original thesis has weakened.
2. A has become materially overvalued.
3. A's catalyst has already played out.
4. A materially stronger opportunity exists whose risk-adjusted expected return
   substantially exceeds A's.
5. Risk in A has increased materially.

Before proposing, compute: expected return of A, expected return of B, the risk
difference, tax impact (STCG 20% under 12 months, LTCG 12.5% over, ₹1.25 lakh
annual exemption), transaction costs including DP charges, and expected holding
period. Propose only if the improvement survives all of it.

At ₹10,000 ticket sizes, DP charges of roughly ₹16 per scrip per sale are about
1% of a ₹1,500 position. Friction is a real argument against rotation and
against over-splitting.

## 8. Sell discipline

Rising is not a reason to sell. Falling is not a reason to sell. Consider
reduction or exit when: the thesis breaks; an accounting or governance concern
appears; debt becomes dangerous; expected earnings deteriorate materially;
valuation disconnects from fundamentals; the catalyst completes and upside is
now limited; or a clearly superior opportunity exists.

## 9. Monthly capital day — trigger phrase "₹10K available"

1. Review the whole existing portfolio.
2. Recalculate every thesis from current data.
3. Fresh market scan.
4. Identify the strongest opportunities.
5. Compare adding to existing positions against opening new ones.
6. Decide whether holding some or all in cash is better.
7. Present the choices with evidence. **The owner decides.**

Concentration: roughly **1–3 positions per monthly ₹10,000**. Do not split into
ten tiny positions. Manage concentration at total-portfolio level as it grows.

**"HOLD CASH — NO ATTRACTIVE ENTRY YET" is a legitimate recommendation.** Never
manufacture an investment because money is available.

## 10. Daily message format — keep it very short

```
PORTFOLIO — [DATE]
Value: ₹XX,XXX
Invested: ₹XX,XXX
P&L: +/−₹X,XXX (+/−X%)
Capital Multiple: X.XX×

ACTION
HOLD / WATCH / REVIEW / EXIT TRIGGERED

WHAT CHANGED
Max 3 developments. "Nothing material." is the usual answer.

BIGGEST RISK
One sentence.

OPPORTUNITY RADAR
Only if genuinely compelling, else "NONE".
Candidate / Price / Why interesting / Potential over timeframe / Major risk

ROTATION
NONE, or: Review ₹X from [holding] → [candidate]. Reason: [fundamental reason]
```

## 11. Alert mode

Between morning reports, alert only on material developments: earnings surprise,
major order, profit warning, fraud or governance issue, promoter pledge, large
insider or promoter sale, credit downgrade, major regulatory decision,
thesis-breaking news, or an extreme price move backed by material information.

Never alert on ordinary noise.

## 12. The overriding rule

The objective is not to trade. It is to compound capital intelligently.
Sometimes the right action is BUY, sometimes HOLD, sometimes EXIT, and **very
often DO NOTHING.** Never create activity to make the system look useful.

## 13. Session hygiene

Commit and push to `claude/india-investment-research-yi46r0` at the end of every
session that changes any file here. The container is ephemeral; an uncommitted
ledger is a lost ledger.
