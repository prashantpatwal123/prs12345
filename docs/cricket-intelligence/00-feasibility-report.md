# Consumer Cricket Intelligence Platform — Feasibility & Design Report

**Status:** Phase 0 deliverable (feasibility sprint). No production code yet. Awaiting approval.
**Date:** 2026-10-03
**Working name:** *Crease* (placeholder only; not a recommendation)

> **How to read this.** Every feature is tagged with a feasibility class:
>
> | Class | Meaning |
> |---|---|
> | **A** | Feasible now with free/open data |
> | **B** | Feasible with derived processing/modelling on top of open data (plus small, legitimately curated reference data) |
> | **C** | Requires commercial/licensed data |
> | **D** | Experimental / research |
>
> Every visual element is tagged with a provenance class: **OBSERVED · DERIVED · RECONSTRUCTED · MODELLED · ILLUSTRATIVE**.
>
> **Verification note.** cricsheet.org was blocked by this sandbox's network proxy, so Cricsheet details below come from prior knowledge of its published format and are flagged *verify*. Vendor prices come from public listings found during this sprint and will change; treat them as order-of-magnitude.

---

## Executive summary (one page)

1. **The open-data foundation is strong for "what happened", and empty for "where/how it happened".** Cricsheet gives us ball-by-ball event data for tens of thousands of matches: batter, bowler, non-striker, runs, extras, wicket kind, fielders, DRS reviews, replacements, targets and powerplays. It has **no line, length, speed, pitch coordinates, shot type, shot direction, fielder positions or bat contact.**
2. That means **pitch maps, wagon wheels, Shot Lab, Edge Map and true delivery replays are class C (licensed tracking or commentary data) or D (computer vision).** No open dataset legitimately provides them.
3. Even so, the open data supports a product deeper than anything consumers have today: complete **batter × bowler matchups**, **dismissal DNA**, **context and pressure analytics**, **win-probability and next-ball models**, a **records engine with arbitrary queries**, a **historical "What Happens Next?" game**, and a **natural-language query layer**. All of these come from facts we actually hold.
4. **Graphics are still central to the MVP.** They work through *law-constrained reconstruction*: the Laws of Cricket turn event facts into geometric constraints. Bowled means the ball hit the stumps. LBW means it did not pitch outside leg. Stumped means the keeper broke the wicket with the batter out of the crease. A caught dismissal with the keeper named means the ball went behind. The engine draws only what those facts imply, and draws every unknown visibly as unknown.
5. **The moat isn't raw data.** It is the canonical event store with provenance, the derived context features, the honest visual grammar, the calibrated models, the NL→query layer, and the user prediction graph (Cricket IQ).
6. **Recommended MVP:** a mobile-first web app (PWA) covering T20 and ODI, men's and women's, built entirely on A/B features. It has Player Intelligence, Dismissal DNA, "How He Gets Out", the Matchup Lab, Situation Maps (replacing pitch maps), Records Explorer, Delivery Explorer, an Innings Lab, a daily historical *What Happens Next?* game, and a constrained Ask Cricket. Estimated infrastructure cost is **under US$50/month** at beta scale, and most of that is LLM spend.
7. **First milestone (M1, about 3 weeks):** ingest Cricsheet into a provenance-aware canonical store, reconcile it, curate player attributes, and ship one vertical slice: a batter's Dismissal DNA, "How He Gets Out" and the matchup view, drilling down to individual deliveries.

---

## 1. Product thesis

**Cricket fans generate questions faster than any product answers them.** Every ball raises a "why": why does he keep nicking off, why bowl him now, can this chase still be won. Today fans get one of two things. Score apps give them *what* (scores, commentary text, flat career tables). Broadcasters give them *why*, but only as a passive moment the director chooses, built on tracking data the fan can never query.

**Thesis:** a product that lets fans *ask* and *see* the answer, and drill from a headline number down to the individual deliveries behind it, will create a new habit. That habit is checking cricket intelligence the way people check scores. A game loop (predict → reveal → learn → Cricket IQ) turns the habit into retention.

**Three bets:**
1. **Drill-down beats dashboards.** NUMBER → PATTERN → VISUAL → DELIVERY is the core interaction, and every screen has to support it.
2. **Honesty is a feature.** Provenance badges and sample sizes build the trust that broadcaster graphics and AI stat-bots lack. In a market full of hallucinated stats, "every number is traceable" is a differentiator.
3. **Prediction as learning, not gambling.** Fans already make predictions in their heads. Scoring those predictions fairly against a calibrated model makes them better observers, and gives us a proprietary dataset no vendor can sell.

---

## 2. Competitive landscape

| Product | Category | What it does well | What it lacks (our opening) |
|---|---|---|---|
| **ESPNcricinfo** (+ Statsguru) | Editorial + stats | Deepest public stats archive, ball-by-ball commentary, query builder, some wagon wheels/pitch maps on major matches, forecaster/win-prob | Statsguru is a 2005-era form UI; little drill-down to deliveries; visuals are per-match, not per-player-pattern; no game loop |
| **Cricbuzz** | Live scores + news | Fast live scores, commentary, huge Indian reach | Shallow analytics; little visual intelligence |
| **CricViz app** | Analytics | WinViz, PredictViz, PitchViz; built on a professional tracking-derived database; official data partner to ECB and Cricket Australia; supplies most Test nations | Consumer app is a companion to B2B business; limited exploratory drill-down; pro data not open to third parties |
| **Official board / league apps** (ICC, IPL, BCCI, ECB, CA) | Official | Rights to video highlights and sometimes tracking graphics | Rights-locked, competition-specific, not cross-competition intelligence |
| **Broadcast graphics** (Hawk-Eye/Sony, broadcaster analytics) | TV | Ball tracking at ~mm precision, beautiful 3D | Passive; not queryable; not available to fans after the moment |
| **CREX / Cricket Exchange, Fancode, Sportskeeda** | Fast scores / media | Speed, notifications | Same commodity data; little analysis |
| **Fantasy platforms** (Dream11 etc.) | Fantasy | Huge engagement | Built around money contests (now heavily restricted in India under the 2025 online-gaming law); stats are shallow and fantasy-oriented |
| **CricHeroes, PitchVision, StanceBeam** | Grassroots / coaching | Amateur scoring, academy video, bat sensors | Not elite cricket; different audience |
| **Hobbyist sites on Cricsheet** (CricMetric, HowSTAT, Kaggle notebooks, Substack analysts) | Niche analytics | Deep, honest, nerdy | Poor UX, no mobile, no visuals, no game loop |
| **Generic AI chatbots** | Q&A | Natural language | Invent statistics; no traceability |
| **Cricket video games** (Cricket 24 etc.) | Entertainment | 3D cricket scenes | Illustrative only; not real data |

**Read of the market:** nobody combines (a) delivery-level drill-down, (b) consumer-grade visual design, (c) honest provenance, (d) a non-monetary prediction game, and (e) natural-language querying. Each exists alone somewhere. The combination doesn't.

## 3. What existing products already do (so we don't rebuild commodity)

- **Commodity (don't compete):** live scores, scorecards, news, text commentary, fixtures, rankings, video highlights.
- **Partially solved:** career stats with filters (Statsguru), win probability (Cricinfo, CricViz), basic wagon wheels and pitch maps on single matches (Cricinfo, broadcasters).
- **Unsolved for consumers:** cross-match pattern drill-down, honest weakness detection with significance, matchup labs with type-level matchups, delivery-level explorers, situation and pressure analytics, NL queries that return verifiable answers, fair prediction games with calibration feedback.

## 4. What would genuinely differentiate us

1. **The drill-down spine.** Any aggregate, anywhere, opens to the deliveries behind it.
2. **Evidence cards instead of opinions.** "Dismissal rate vs left-arm pace is 1.7× baseline (n=412 balls, 90% CI 1.2–2.3×, shrunk estimate 1.5×)."
3. **Honest visual grammar.** A consistent visual language for observed, derived, reconstructed, modelled and illustrative elements. Ours would be the first consumer product to have one.
4. **Situation intelligence.** Context-aware stats such as "with 40+ needed off the last 3 overs" or "first 10 balls of an innings", which most fans can't get anywhere today.
5. **What Happens Next?** A daily historical prediction puzzle, scored against a calibrated model.
6. **Cricket IQ.** A personal record of what the user perceives well and badly.
7. **Ask Cricket that can't lie.** Every number in an answer is mechanically checked against a query result.

---

## 5. Data-source investigation

### 5.1 Open / free sources

| Source | What it is | Coverage | Licence | Notes |
|---|---|---|---|---|
| **Cricsheet** (cricsheet.org) | Ball-by-ball match data, JSON/YAML/CSV | Men's & women's Tests, ODIs, T20Is, and many leagues (IPL, BBL, WBBL, PSL, CPL, SA20, ILT20, The Hundred, WPL, county/domestic competitions, etc.). On the order of 20k matches (*verify*). Coverage starts in the mid-2000s for most internationals; **older matches are absent or incomplete** | Open Data Commons Attribution licence (*verify exact version*); attribution required | **Our foundation.** Also publishes a **People Register** (people.csv / names.csv) that maps each player to identifiers on ESPNcricinfo, Cricbuzz, CricketArchive, etc. That register is the join key for any future licensed data |
| **Wikidata** | Structured facts | Partial player metadata (dates of birth, nationality, sometimes batting hand / bowling style) | CC0 | Useful seed for player attributes; must be validated |
| **Kaggle / GitHub derivatives** | Mostly Cricsheet re-packaged, some scraped | Varies | Often unclear or inherits scraping problems | **Avoid** unless provenance and licence are clean |
| **Weather archives** (e.g., Open-Meteo historical, NOAA) | Hourly weather by lat/long | Global, decades | Open (check per source) | Lets us add match-day conditions (B) |
| **Venue geodata** (OpenStreetMap) | Ground locations, boundary geometry roughly | Global | ODbL | Venue normalization, maps; boundary dimensions are approximate |
| **Academic CV datasets** (CricShot10, CBSId, FPV/ball-delivery segmentation) | Labelled clips/images for shot classification research | Small (hundreds–thousands of clips) | Research licences; underlying broadcast footage rights are unclear | Useful for research spikes only, not production |

### 5.2 Commercial APIs (scores, ball-by-ball, commentary)

| Provider | What's offered | Indicative price (public, 2026) | Live? | Key licensing question |
|---|---|---|---|---|
| **Sportmonks Cricket** | Fixtures, scorecards, ball-by-ball across 130+ leagues | Free tier (3 leagues, 180 req/h); Major ~€25–29/mo (20 leagues); World ~€69/mo; Enterprise on request | Yes (<15s claimed) | Storage/derivation rights for building a historical analytical DB; check field depth (does ball-by-ball include commentary/shot/direction?) |
| **EntitySport** | Scorecards, ball-by-ball, fantasy points, **commentary tiers** | Starter $150/mo; Pro $250/mo; Elite $450/mo; Commentary tiers $250–$500+/mo | Yes | Commentary text is the potential route to **shot / line / length via NLP**; we would need explicit rights to store the text and derive data from it |
| **Roanuz Cricket API** | Live scores, ball-by-ball, fantasy | Tiered / on request | Yes | As above |
| **CricketData.org (CricAPI)** | Lightweight scores API | Free tier + low-cost paid | Yes | Depth is limited; fine for live scores |
| **Goalserve** | Feed-style data | Published price list | Yes | As above |
| **Sportradar** | Official/enterprise feeds | Enterprise (high five to six figures/yr, estimate) | Yes, low latency | Betting-oriented; heavy contracts |
| **Cricbuzz / ESPNcricinfo** | Consumer sites | — | — | **Do not scrape.** Their terms prohibit it. Any data use requires a commercial agreement |

### 5.3 Professional tracking / scouting data

| Provider | What | Access |
|---|---|---|
| **Hawk-Eye (Sony)** | Multi-camera ball tracking (release, pitch point, speed, swing, seam deviation, bounce, impact, predicted path), increasingly skeletal/player tracking | Owned/controlled by boards and broadcasters; not sold to consumer start-ups in practice |
| **CricViz** | Tracking-derived database with line/length/shot/control, plus a pro analyst layer; official partner to ECB and Cricket Australia | B2B licensing, enterprise pricing; possible partner at a later stage |
| **Opta / Stats Perform**, other scouting vendors | Manually coded event data (shot type, length, line, direction, control) | Enterprise |
| **Board-run data programmes** | Data centralisation (e.g., Cricket Australia + CricViz) | Rights sit with boards |

**Conclusion:** line, length, speed, shot and direction exist commercially, but they sit behind enterprise contracts held by boards and B2B vendors. For a near-zero-capital start, assume **no access**, design the architecture so these fields can drop in later, and run one low-cost experiment: licensed commentary + NLP (§11).

---

## 6. Data capability matrix

Legend. *Reliability:* H/M/L. *MVP usable:* ✅ yes · 🟡 partial/derived · ❌ no. *Vis possible:* what can be **factually** drawn.

| Data field | Best low-cost source | Coverage | Historical depth | Live? | Licence | Cost | Reliability | MVP usable? | Visualization possible (factual) |
|---|---|---|---|---|---|---|---|---|---|
| Match (teams, date, venue, result, toss, officials, PoM) | Cricsheet | Intl + major leagues, M & W | ~mid-2000s→now (varies by format) | No | Open, attribution | Free | H | ✅ | Match cards, timelines |
| Innings (team, target, declared, forfeited, penalty runs) | Cricsheet | as above | as above | No | Open | Free | H | ✅ | Worm, Manhattan |
| Over / ball sequence | Cricsheet | as above | as above | No | Open | Free | H | ✅ | Over-by-over timelines |
| Batter / bowler / non-striker per ball | Cricsheet | as above | as above | No | Open | Free | H | ✅ | Matchup grids |
| Runs (batter, extras, total, non-boundary flag) | Cricsheet | as above | as above | No | Open | Free | H | ✅ | Scoring sequences |
| Extras breakdown (wides, no-balls, byes, leg-byes, penalty) | Cricsheet | as above | as above | No | Open | Free | H | ✅ | Discipline charts |
| Wicket (player out, kind) | Cricsheet | as above | as above | No | Open | Free | H | ✅ | Dismissal DNA, law-constrained scenes |
| Fielder(s) involved, substitute flag | Cricsheet | as above | as above | No | Open | Free | H (M for older) | ✅ | Fielder-attributed dismissals |
| **Caught behind** (catcher = designated keeper) | Derived: Cricsheet fielder + keeper identification | as above | as above | No | Open | Free | M–H (keeper must be inferred; see §16) | 🟡 DERIVED | "Behind the stumps" route |
| Slip / gully / point / deep catch position | Licensed commentary (NLP) or pro data | — | — | — | Commercial | $$–$$$$ | L–M (NLP) / H (pro) | ❌ | Only with C data |
| DRS reviews (by, decision, umpire's call) | Cricsheet (recent matches) | Partial | Recent years | No | Open | Free | M–H | ✅ | Review timelines; LBW constraint hints |
| Replacements (impact player, concussion) | Cricsheet | Recent | Recent | No | Open | Free | H | ✅ | XI tracking |
| Powerplays | Cricsheet | Limited-overs | Recent | No | Open | Free | H | ✅ | Phase overlays |
| Playing XI | Cricsheet | as above | as above | No | Open | Free | H | ✅ | Team sheets |
| Batting hand | Curated reference (Wikidata seed + manual verification) | Top ~3–5k players first | Static | — | CC0 / own curation | Labour | M→H after curation | 🟡 | vs LHB/RHB splits |
| Bowling style (RF, RFM, LFM, SLA, LB, OB, LWS…) | Curated reference | as above | Static (can change over a career) | — | own curation | Labour | M→H | 🟡 | vs bowler-type splits |
| Player role / wicketkeeper flag per match | Derived (stumpings, byes, known keepers) + curation | as above | as above | — | own | Labour | M | 🟡 | Keeper attribution |
| Shot type | Licensed commentary NLP / pro coding / CV | — | — | — | Commercial | $$+ | L–M (NLP), H (pro) | ❌ | Shot Lab needs C/D |
| Shot direction / wagon wheel | Pro data / some API tiers (verify) | Major matches | Varies | Yes (pro) | Commercial | $$$ | H (pro) | ❌ | Wagon wheel needs C |
| Line | Pro tracking/coding; commentary NLP (coarse) | — | — | — | Commercial | $$–$$$$ | L–M (NLP coarse buckets) / H (tracking) | ❌ | Pitch map needs C |
| Length | as Line | — | — | — | Commercial | as above | as above | ❌ | as above |
| Speed | Tracking; sometimes in commentary/broadcast | Major matches | Recent | Yes (pro) | Commercial | $$$ | H (tracking) | ❌ | Speed bands need C |
| Pitch coordinates | Tracking | Major matches | Recent | Yes | Commercial | $$$$ | H | ❌ | C |
| Ball trajectory, swing, seam, spin, bounce | Tracking (Hawk-Eye-class) | Major matches | Recent | Yes | Rights-locked | $$$$$ | H | ❌ | C (likely unobtainable early) |
| Bat contact / edge zone | Not commercially standard; inferable only coarsely ("edged") from commentary | — | — | — | — | — | L | ❌ | D (edge *event* coarse via NLP = C) |
| Bat path, stance, foot movement, batter position | Player/skeletal tracking or CV | Elite, sparse | Very recent | — | Rights-locked | $$$$$ | M | ❌ | D |
| Field placement / fielder coordinates | Pro data / broadcast graphics | Sparse | Recent | — | Commercial | $$$$ | M–H | ❌ | C/D |
| Weather | Open-Meteo / NOAA historical | Global | Decades | Forecast yes | Open | Free | M (point-of-ground approximation) | ✅ B | Conditions overlays |
| Pitch report / surface | Editorial text only | — | — | — | Copyrighted | — | L | ❌ | Avoid; can model "venue behaviour" from scoring instead (B) |
| Commentary text | Licensed API commentary tiers | Major matches | Varies | Yes | Commercial (store/derive rights critical) | $250–500+/mo | M | ❌ (Phase 2 spike) | Source for NLP-derived shot/line/length |
| Live ball-by-ball events | Sportmonks / EntitySport / Roanuz | Major comps | — | Yes (~seconds) | Commercial | €29–$500/mo | H | ❌ (post-MVP) | Live second screen |

**What the matrix decides:** every graphic we can call *factual* in the MVP is built from event outcomes (who, when, how many, how out, by whom, in what situation). Spatial "where on the pitch" graphics are either deferred (C), or drawn as law-constrained reconstructions that show only implied facts and visibly mark the unknowns.

---

## 7. What open/free data gives us

From Cricsheet plus small curated reference data, we can compute:

- **All standard batting/bowling/fielding aggregates**: runs, balls, average, SR, 50/100/150/200, ducks, HS, 4s, 6s, not outs, overs, maidens, wickets, economy, average, SR, 4W/5W/10W, catches, stumpings, run-out involvement. Caveat: these cover *our* ball-by-ball coverage. Players whose careers predate it will show partial careers, and the UI must say so (§29).
- **All filters** in the brief: year, season, series/tournament, team, opposition, venue, country, home/away/neutral (derived from venue country + team), batting position (derived from order of appearance), innings, match result, phase, captaincy (Cricsheet doesn't mark captains consistently; curation needed, B), bowler type and batter hand (curated, B).
- **Matchups**: exact batter vs bowler at ball level, plus batter vs bowler-type and bowler vs batter-hand (B).
- **Dismissal DNA**: kind, bowler, bowler type, phase, ball-of-innings, match situation, fielder, keeper-involvement (derived), substitute catches, run-out roles (who was run out, striker vs non-striker).
- **Context engine (limited overs)**: score, wickets, current/required run rate, target, balls remaining, partnership, chasing/setting, knockout/final (from event metadata + curation), powerplay.
- **Context engine (Tests)**: innings number, lead/deficit, fourth-innings target, overs since new ball (a proxy for ball age; the second new ball is inferable at ~80+ overs but not exactly known, so it's DERIVED with uncertainty). Day and session are **not reliably available** from Cricsheet (no timestamps), so they're only estimable from over counts (low reliability, ILLUSTRATIVE/DERIVED-L).
- **Pressure metrics**: dot-ball sequences, balls since last boundary, required-rate deltas, win-probability leverage.
- **Models**: win probability, next-ball outcome distribution, projected totals, partnership hazard, dismissal-type hazard.
- **Records**: essentially any aggregate record expressible as filter + group + metric + threshold.

## 8. What requires paid/licensed data

- Line, length, speed, pitch coordinates, trajectory, swing/seam/spin, bounce → **tracking (C, likely enterprise)**.
- Shot type, shot direction, control/false-shot, edge events, catch position (slip/gully/deep) → **pro coded data (C) or licensed commentary + NLP (C, lower cost, lower accuracy)**.
- Live data (second screen) → **live API (C, roughly €29–$500/mo for mainstream feeds)**.
- Player photos, team logos, video → **image/video licensing (C)**. Logos are trademarks; don't use them without permission.
- Complete historical careers for pre-coverage eras → **licensed scorecard-level data (C)**, or a carefully built scorecard dataset from licensed sources.

## 9. Graphical features feasible with open data (A/B)

| Graphic | Class | Provenance | Notes |
|---|---|---|---|
| **"How He Gets Out" dismissal route map** (bowled, LBW, stumped, run out, caught-by-keeper, caught-and-bowled, caught-in-field [position unknown], hit wicket, other) | B | OBSERVED (kind, fielder) + DERIVED (keeper role) | Caught-in-field shown as a *ring zone* ("in the field"), never a specific position |
| **Law-constrained dismissal scene** | B | RECONSTRUCTED (law-constrained) | Bowled: ball arrives at stumps. LBW: pitched not outside leg, impact zone in line *unless* no-shot exception. Stumped: batter out of crease, keeper takes ball. Line/length unknown → rendered as uncertainty envelope, labelled |
| **Situation maps** (over × wickets, required-rate × balls-left, ball-of-innings) as heatmaps | A/B | OBSERVED / DERIVED | Our honest substitute for pitch maps in MVP |
| **Matchup grid / matchup timeline** | A | OBSERVED | Each cell clicks through to deliveries |
| **Dismissal DNA radial / sunburst** | A/B | OBSERVED/DERIVED | Kind → bowler type → phase → deliveries |
| **Innings worm, Manhattan, partnership bars, win-prob curve** | A/B | OBSERVED / MODELLED | WP curve labelled MODELLED with model version |
| **Ball-sequence "strip"** (every ball as a glyph: dot, 1, 2, 4, 6, W, extras) | A | OBSERVED | Great for "Innings Lab" and delivery explorer |
| **Form charts / career arcs** with uncertainty bands | B | DERIVED/MODELLED | Rolling, shrunk rates |
| **Bowler "phase fingerprint"** (where in the innings he bowls & his outcomes) | A/B | OBSERVED | Replaces "where he bowls on the pitch" for MVP |
| **Fielder involvement map by role** (keeper, bowler, fielders) | B | DERIVED | No coordinates |
| **Prediction reveal animations** | A/B | MODELLED + OBSERVED | Model probability bars → actual outcome |
| **Concept explainers** (what is a yorker, what is LBW) | A | ILLUSTRATIVE | Watermarked ILLUSTRATION |

## 10. Graphical features that require tracking (or other C/D) data

| Graphic | Needs |
|---|---|
| Pitch map / pitch heatmap / line × length engine | Line, length (coordinates ideally) → C |
| Bowler map from batter's view | Pitch coordinates + arrival → C |
| Wagon wheel 2.0 / field map / scoring zones | Shot direction (+ distance) → C |
| Shot Lab & Graphical Shot Explorer | Shot type (+ direction, line, length) → C (coarse via NLP) |
| Bat contact / edge map | Contact zone → D (not standard even in pro data) |
| Delivery replay with real trajectory | Tracking → C (rights-locked) |
| Stance, trigger, foot movement, bat path | Skeletal tracking / CV → D |
| Fielder positions / catch locations | Pro field data / CV → C/D |
| Speed bands (135+ km/h filters) | Speed → C |
| Swing / seam / spin filters | Tracking → C |

## 11. Are shot-level analytics realistically obtainable?

- **Open data:** No. Cricsheet has no shot field.
- **Licensed commentary + NLP (C, lower cost):** **Plausible but needs testing.** Commentary often includes phrases like "drives through cover", "pulls to deep square", "edges to second slip", "full outside off". A classifier could extract:
  - shot family (drive / cut / pull-hook / sweep family / flick-glance / defence / leave / lofted / reverse / ramp)
  - direction sector (off side / on side / straight / behind square / fine)
  - catch position (keeper / slip cordon / gully / point / cover / mid-off / mid-on / midwicket / square / fine / deep)
  - edge event ("edged", "thick edge", "top edge")
  - coarse length (full / good / short / yorker / bouncer) and line (outside off / straight / leg)

  **Caveats:** commentary is selective (dot balls often get "no run"), inconsistent across writers and providers, and editorial, not measured. Every extracted value is **DERIVED (from text)** with a confidence score and classifier version, and the UI shows "classified from commentary" plus a coverage % per filter. Our **contract must explicitly allow** storing the text and building derived data from it. Many feed contracts restrict caching and derivative works.
- **Pro coded data (C, enterprise):** high quality and available, but expensive and partner-gated.
- **CV (D):** research-grade only; see §14.

**Recommendation:** a **Phase-2 "commentary NLP spike"**: license one commentary tier for 1–2 months (≈$250–500/mo), hand-label ~2,000 balls, measure per-field precision and recall, and ship the Shot Lab only where precision is ≥90% (shot family) with coverage disclosed.

## 12. Are line/length data realistically obtainable?

- **Exact coordinates:** only via tracking (Hawk-Eye-class) → C, rights-locked. Unrealistic early on.
- **Coarse buckets:** via commentary NLP → C (cheap tier). Expect usable *length* buckets on a decent fraction of balls and weaker *line* coverage. Coverage will be biased toward eventful balls, which we must disclose, because it biases rates.
- **Implied constraints from Laws:** partial and free (bowled / LBW / stumped). Not a substitute for a pitch map.
- **Verdict:** No pitch maps in MVP. Design the Line × Length engine and the PitchMap component now, against a schema that accepts both continuous coordinates (from tracking) and categorical buckets (from NLP), each with provenance.

## 13. Is exact bat-contact information obtainable?

**No, not realistically.** Exact contact location on the bat (toe, splice, upper/lower middle) is not a standard field even in professional tracking feeds. Ultra-edge / Snicko-type data indicates *whether* there was contact, not *where on the bat*. Bat sensors (e.g., StanceBeam-type) exist for academies, not elite matches. CV from broadcast can't resolve bat-face location reliably at broadcast frame rates and angles.

- **Coarse "edge happened"** (from commentary, C) is the most we can plausibly get. It would power a reduced "Edge Events" view (outside edge / inside edge / top edge as described by commentary, DERIVED-from-text).
- **Edge Map on a bat graphic** stays **D**. If it's ever shown, it's ILLUSTRATIVE with an explicit "no measured contact data" label.

## 14. Computer-vision feasibility

| Capability | Technically possible? | Legally / data-access possible for us? |
|---|---|---|
| Delivery segmentation (detect each ball in broadcast) | **Yes**: published work (YOLO/MobileNet ball-delivery segmentation, front-pitch-view detection) | Needs footage rights. Broadcast footage is copyrighted; commercial processing without a licence is high-risk |
| Shot classification from video | **Yes, in research**: CricShot10 (10 shots), CBSId (7 classes), 2025 baselines; accuracy drops on unconstrained broadcast | Same rights issue |
| Ball tracking from single broadcast camera | **Partially**: 2D tracking possible; reliable 3D trajectory needs calibrated multi-camera | Same |
| Batter/bowler pose (stance, foot movement) | **Yes for 2D pose** (off-the-shelf pose models); 3D needs multi-view | Same; also player likeness considerations |
| Bat position / contact location | **Very hard** at broadcast fps/resolution | Same |
| Field placement | **Partially** from wide shots (intermittent) | Same |

**Separation of possible vs permitted:**
- *Technically possible today:* delivery segmentation, coarse shot class, 2D pose, 2D ball path in favourable shots.
- *Legally possible for us today:* **none at scale on elite broadcast footage** without a licence.
- *Legitimate paths:* (1) **partnerships with leagues or boards that lack data budgets** (associates, domestic, women's leagues, academies), who grant footage rights in exchange for analytics; (2) **own-capture** at grassroots fixtures with consent; (3) user-uploaded *own* footage (net sessions) for a separate coaching product. All are **D** and post-MVP.

## 15. Legal / licensing constraints

> Not legal advice. Engage counsel (India + UK/EU + US) before launch and before any vendor contract.

1. **Facts vs databases.** Individual match facts (scores, who got out) are generally not copyrightable (US: *Feist*; live-facts reporting: *NBA v. Motorola*). **EU/UK** recognise a **sui generis database right** (cf. *Football DataCo v Sportradar*, 2012–13), and **contracts/ToS** bind regardless. → Use Cricsheet (open licence) plus licensed vendors. **No scraping** of Cricinfo, Cricbuzz, broadcaster sites or apps.
2. **Cricsheet licence.** Open, with attribution required (*verify current terms and version*). We must show attribution on data pages and in our open-data notices, and preserve source IDs.
3. **Vendor contracts.** Check rights to: store; build historical DB; create derivative data; display to unlimited users; use in AI features; retain after termination. Many cheap live feeds forbid retention after termination. Our canonical store must tag every record with source + licence, so we can purge or segregate per licence.
4. **Video/footage.** No commercial processing of broadcast footage without rights. No embedding of unlicensed clips.
5. **Player names & likeness.** Names in factual statistics are fine. **Photos require licensing.** Avoid implied endorsement. Use stylised, non-identifying avatars (no real faces), and never claim player-specific biomechanics.
6. **Trademarks.** Don't use IPL/ICC/team logos or "official". Team colours are fine as generic palettes; avoid trade-dress imitation.
7. **Gaming law.** India's Promotion and Regulation of Online Gaming Act, 2025 bans real-money online games and permits/promotes free social and e-sports games. Our game must have **no entry fees, no cash or cash-equivalent prizes, no purchasable advantage**. Before introducing *any* prizes, get a legal review per market. Also avoid sportsbook UI patterns and "odds" language.
8. **Privacy.** User predictions, leagues and Cricket IQ are personal data: DPDP Act (India), GDPR/UK GDPR. Minimal collection, export/delete support, age gating (13+/16+).
9. **AI outputs.** Ask Cricket must not make claims about real people beyond the data. No speculation on injuries, personal life or biomechanics.

---

## 16. Proposed canonical cricket data model

**Principle:** the **Delivery** is the atomic fact. Everything else either describes a delivery, groups deliveries, or is derived from them. Core observed facts live in wide, typed tables optimised for analytics. Derived, reconstructed and modelled facts live as **assertions** carrying provenance, and are materialised into wide views for speed.

### 16.1 Reference entities

```
Person(person_id, canonical_name, full_name, dob, country, gender,
       external_ids{cricsheet, cricinfo, cricbuzz, ...})
PlayerAttribute(person_id, attribute, value, valid_from, valid_to,
                provenance, source, confidence, note)
   -- batting_hand, bowling_arm, bowling_style (RF/RFM/RM/LF/LFM/LM/OB/LB/SLA/LWS…),
   -- bowling_family (pace/spin), primary_role, keeper (bool)
Team(team_id, name, type[international|franchise|domestic], gender, country)
Venue(venue_id, canonical_name, aliases[], city, country, lat, lon, timezone)
Competition(competition_id, name, type, gender, format)
Season / Series(series_id, competition_id, season_label, start, end)
```

### 16.2 Match structure

```
Match(match_id, source_ids, format[Test|ODI|T20I|T20|List A|FC|100-ball],
      balls_per_over, scheduled_overs, gender, series_id, venue_id, dates[],
      toss_winner, toss_decision, outcome{winner, by_runs, by_wickets, method[DLS..], result[tie|draw|NR]},
      stage[group|knockout|final], neutral_venue, officials, player_of_match,
      coverage_flags{ball_by_ball_complete, missing_sections[]})
PlayingXI(match_id, team_id, person_id, is_captain*, is_keeper*, batting_order*, replacement_info)
   -- * = derived/curated with provenance
Innings(innings_id, match_id, number, batting_team, bowling_team, target_runs, target_overs,
        declared, forfeited, super_over, penalty_runs, powerplays[])
```

### 16.3 Delivery and its satellites

```
Delivery(delivery_id, innings_id, over_number, ball_in_over, legal_ball_index, seq_in_innings,
         batter_id, bowler_id, non_striker_id,
         runs_batter, runs_extras, runs_total, non_boundary_flag,
         extras{wides, noballs, byes, legbyes, penalty},
         is_legal, is_boundary4, is_boundary6, is_dot,
         source, source_ref, ingested_at)              -- all OBSERVED

DeliveryContext(delivery_id, -- DERIVED, deterministic from event history
         score_before, wickets_before, balls_remaining, target_remaining, crr, rrr,
         partnership_runs, partnership_balls, batter_balls_before, batter_runs_before,
         bowler_balls_in_spell, phase[pp|middle|death | test_session_est], innings_lead,
         overs_since_new_ball, is_new_batter(<10 balls), chasing(bool), match_stage)

Dismissal(delivery_id, player_out_id, kind, bowler_credited(bool),
          fielders[{person_id, is_substitute, role*}],   -- role: keeper/bowler/fielder (DERIVED)
          route*,                                         -- canonical route enum (DERIVED)
          striker_or_non_striker)
Review(delivery_id, by_team, umpire, batter, decision, umpires_call, type)
Replacement(delivery_id|innings_id, in, out, reason, team)

-- Future-ready (empty in MVP, schema exists):
DeliveryTracking(delivery_id, release_xyz, speed_release, speed_bounce, pitch_xy,
                 bounce_height, swing_deg, seam_deg, spin_rpm, arrival_xyz, trajectory_ref, source, ...)
ShotEvent(delivery_id, shot_type, shot_family, direction_deg, distance_m, control, edge_type, ...)
FieldingEvent(delivery_id, fielder_id, position_label, xy, action[catch|drop|misfield|throw], ...)
ContactEvent(delivery_id, contact_zone, ...)       -- D
PlayerPosition(delivery_id, person_id, t, xyz/pose_ref, ...)  -- D
```

### 16.4 Assertions (derived / reconstructed / modelled facts)

```
Assertion(assertion_id, subject_type[delivery|player|match|innings], subject_id,
          attribute, value_json, provenance_class[OBSERVED|DERIVED|RECONSTRUCTED|MODELLED|ILLUSTRATIVE],
          source_id, method, method_version, confidence, evidence_refs[], created_at, superseded_by)
```

Examples:
- `delivery 123 · line_bucket = "outside_off" · DERIVED · source=entitysport_commentary · method=commentary_nlp v0.3 · conf 0.82 · evidence="…full outside off, drives…"`
- `dismissal 456 · route = "caught_keeper" · DERIVED · method=keeper_inference v1.0 · conf 0.97 · evidence=[stumpings_in_match, keeper_roster]`

### 16.5 Users & game

```
User, UserPrediction(user_id, moment_id, question_type, answer, model_probs_snapshot, model_version,
                     points, created_at), Moment(moment_id, delivery_id, state_snapshot, difficulty, leverage),
League, LeagueMember, Badge, UserSkillProfile(dimension, rating, uncertainty, updated_at),
ModelVersion(model_id, version, trained_on_through_date, features_hash, metrics, card_url)
```

### 16.6 Keeper identification (an important derivation)

Cricsheet names fielders but doesn't mark the wicketkeeper. Inference order:
1. Curated per-match keeper (if present) → DERIVED-H.
2. Player recorded with a **stumping** in that innings → keeper (H).
3. Player who is a known specialist keeper in the playing XI (curated keeper attribute) and the only one → H.
4. Ambiguous (two keepers in XI, mid-match swap) → leave `role = unknown` (never guess). Caught-behind stays "caught (fielder)".

Reported as: "Caught behind (keeper identified by inference; 97% of cases high-confidence)".

---

## 17. Data provenance architecture

1. **Source registry:** `Source(source_id, name, licence, licence_url, terms_version, retention_rules, attribution_text)`. Every row references a source.
2. **Immutable raw zone:** original files (Cricsheet JSON zips, vendor payloads) stored byte-for-byte with checksum and fetch timestamp. Re-ingestion is deterministic.
3. **Lineage:** each canonical row stores `source_id`, `source_ref` (e.g., Cricsheet match file + innings/over/ball index) and `ingest_run_id`.
4. **Assertions** as in §16.4 for everything non-OBSERVED. **Classifier/model versions** are immutable and registered. Re-running creates new assertions; old ones are superseded, not overwritten.
5. **Field-level provenance in APIs:** every API value that isn't plainly OBSERVED is returned as `{value, prov, conf, method_version}`. The frontend refuses to render a scene element without a `prov` tag (enforced by type system and lint rule).
6. **Data quality gates (CI):** per match, assert innings totals = Σ delivery runs; wickets ≤ 10 (allowing retired-not-out rules); legal balls per over consistent with `balls_per_over`; batter/bowler in XI; no orphan dismissals. Failing matches are quarantined and flagged in the UI.
7. **Coverage metadata:** for any query the engine returns `coverage = {matches_included, matches_known_missing, pct_balls_with_field_X}`, so the UI can say "Shot type known for 63% of these balls".
8. **Licence segregation:** licensed data lives in separate partitions keyed by licence, so a contract end means a clean purge of raw data and of derivatives where the contract requires it.

---

## 18. Graphics / visualization architecture

### 18.1 Layers

```
Geometry model (real-world metres; pitch 20.12m, crease lines, stumps 71.1cm, return creases, 30-yd circle,
                 field-position catalogue as angular/radial zones relative to batter hand)
        ↓
SceneSpec (renderer-agnostic JSON): entities + timeline + provenance per element
        ↓
Renderers:  SVG/2D (MVP) · Canvas2D (dense clouds, >2k marks) · WebGL/Three.js via react-three-fiber (later 3D replays)
        ↓
Components: PitchMap · ShotMap · DismissalMap · EdgeMap · BowlingMap · FieldMap · DeliveryScene/Replay ·
            MatchupVisualizer · WeaknessVisualizer · SituationMap · InningsStrip
```

### 18.2 Primitives

`Pitch, Crease, Stumps, Ball, Bat, Batter, Bowler, Keeper, Fielder, Trajectory, Bounce, Contact, ShotPath, CatchPath, HeatMap, FieldZone, UncertaintyEnvelope, UnknownToken, ProvenanceBadge`.

Players are **stylised silhouettes** (no likeness), mirrored by batting hand. In the MVP, poses are drawn only from a small library of *generic* poses, explicitly ILLUSTRATIVE.

### 18.3 The honest visual grammar (core IP)

| Provenance | Rendering rule |
|---|---|
| OBSERVED | Solid stroke/fill, full opacity, no badge needed (default) |
| DERIVED | Solid with small "D" badge; tooltip shows method and confidence |
| RECONSTRUCTED | Dashed stroke, reduced opacity, mandatory banner "RECONSTRUCTED FROM EVENT DATA" |
| MODELLED | Gradient/probability styling, banner "MODEL ESTIMATE · vX.Y" |
| ILLUSTRATIVE | Desaturated + "ILLUSTRATION" watermark; never mixed into a real-delivery scene without separation |
| UNKNOWN | Visible: hatched zone/envelope or "?" token. **Unknowns are never silently filled with a plausible value.** |

**Rule:** a `SceneSpec` element with missing `prov` fails validation. The scene's overall label is the *weakest* provenance among its non-decorative elements.

### 18.4 Delivery timeline phases

`run_up → release → flight → pitch → post_bounce → arrival → contact → post_contact → outcome`. Each phase renders only if it has data or a law-derived constraint. Example for a **bowled** dismissal with no tracking:
- release: generic bowler (ILLUSTRATIVE, bowling arm from curated attribute = DERIVED)
- flight/pitch: **UncertaintyEnvelope** spanning plausible line/length (RECONSTRUCTED, labelled "pitch point unknown")
- arrival: ball meets stumps (OBSERVED via dismissal kind)
- outcome: bails off, "BOWLED" (OBSERVED)

### 18.5 Performance & platform

- Mobile-first: SVG for <1k marks; Canvas for clouds; Three.js lazy-loaded only on 3D views (post-MVP).
- 60fps animations with Web Animations / requestAnimationFrame; scene specs are small JSON (<10KB).
- One `useScene()` hook drives the same scene in a player page, an AI answer, a game reveal, or a share card (server-rendered PNG via resvg/satori for social sharing).

---

## 19. Analytics architecture

**Data size reality check:** roughly 20k matches → about 8–15 million deliveries (*estimate*). Columnar Parquet: ~0.3–1 GB. **This is small data.** It fits comfortably in **DuckDB** on one machine. ClickHouse/Spark aren't justified at this stage.

```
Raw (Cricsheet JSON, vendor payloads)  →  Python ingest (pydantic validation)
   → Canonical Parquet (partitioned by format/gender/year)
   → dbt-duckdb transforms: DeliveryContext, Dismissal routes, PlayerAttribute joins
   → Feature marts: player×format×{season, opposition, venue, phase, bowler_type, ...}
   → Semantic layer: metric definitions (runs, balls, SR, avg, dot%, boundary%, dismissals/ball, …)
       defined ONCE, compiled to SQL; every metric has formula, numerator, denominator, min-sample
   → Query service (FastAPI + DuckDB, read-only) + precomputed JSON for hot pages
```

**Key components**
- **Metric registry:** YAML definitions (e.g., `batting_average = runs / dismissals`, `null if dismissals=0`; `strike_rate = 100*runs/balls_faced` where balls_faced excludes wides). This single source of truth is shared by UI, records, Ask Cricket and tests.
- **Filter grammar:** a typed filter AST (`format ∈ {T20I}`, `bowler.style_family = pace`, `phase = death`, `date ≥ 2022-01-01`, …) compiled to SQL. It's the same grammar the UI chips, records engine and LLM emit.
- **Statistical layer:** empirical-Bayes / beta-binomial shrinkage for rates (dismissals per ball, boundary %, dot %). Wilson / posterior intervals. Benjamini–Hochberg FDR control when scanning many splits for strengths/weaknesses. Minimum-sample thresholds per metric.
- **Strength & Weakness engine:** for each player, scan pre-defined dimensions (bowler type, phase, ball-of-innings, match situation, venue country, opposition, ground type) → compute shrunk rate vs player baseline → keep only splits with n ≥ threshold, FDR-adjusted significance and meaningful effect size → emit **Evidence Cards** `{claim_template, metric, sample, baseline, diff, ratio, ci, confidence_label, filters, delivery_query}`. Text is *templated*, never free-generated.
- **Point-in-time correctness:** all "as of" features (career-to-date, form) are computed with strict date cutoffs. This is essential for models and the game.

---

## 20. Prediction / model architecture

| Model | Target | Class | Approach | Notes |
|---|---|---|---|---|
| Win probability (T20/ODI) | P(batting side wins) per ball | B | Gradient-boosted trees (LightGBM) or logistic GAM on state (runs needed, balls left, wickets, format, venue scoring level, team strength Elo) | Calibrated (isotonic); DLS matches flagged; time-split validation |
| Win probability (Tests) | P(win/draw/loss) | B (harder) | Multinomial; overs remaining in match is a proxy (no clock data) | Lower confidence; ship later |
| Next-ball outcome | {dot, 1, 2, 3, 4, 6, wicket, extra} | B | Multinomial GBM: state + batter/bowler shrunk rates as-of-date + matchup type + phase + venue | Primary engine for the game and leverage metrics |
| Projected total / partnership | Distribution | B | Monte-Carlo simulation using next-ball model | Show interval |
| Batter milestone (50/100) | P(reach) | B | Simulation from current state | |
| Dismissal-type next match | P(caught behind next innings) etc. | B | **Competing-risks per-ball hazard** by dismissal route (shrunk, by bowler-type exposure) × **expected balls faced distribution** (batting position, format, form) → P(dismissed via route in innings) = Σ_b P(survive to b)·h_route(b). Opposition attack composition (curated bowling types) shifts exposure | Never a naive count/matches; show interval and drivers |
| Line/length/shot predictions | | C | Only after data exists | |
| Player Elo / ratings | Team/player strength | B | For features + a "form" product | |

**Model governance:** `ModelVersion` registry with model cards (training window, features, calibration curve, Brier/log-loss, known failure modes). Every prediction displayed shows **MODEL ESTIMATE · model vX.Y · drivers (SHAP top 3) · sample context**. HISTORICAL STATISTIC and MODEL ESTIMATE are always visually separated (different container styles, never in the same number style).

---

## 21. Historical "What Happens Next?" architecture

**Pipeline**
1. **Moment mining:** scan deliveries for high-leverage states: win-probability swing potential, close chases, milestone moments, famous-match flags, and balance across formats, eras and genders.
2. **Freeze state:** snapshot of `DeliveryContext` before the ball (score, target, batter/bowler with as-of-date stats, recent balls strip, matchup history *up to that date*).
3. **Pre-compute model probabilities** with a model **trained only on data before the match date**. That gives honest priors with no leakage.
4. **Questions:** MVP has outcome (0/1/2/3/4/6/W/extra) and "how will the wicket fall" (route). Later, visual questions (where will it pitch, what shot, where will it go) once C data exists.
5. **Reveal:** actual outcome (OBSERVED), model distribution (MODELLED), user pick, points, "what happened next" strip of the following 6 balls, link to match Innings Lab.
6. **Mystery mode:** hide team/player names and date for the first reveal stage to reduce lookup-cheating. Show them after the answer.

**Scoring (fair, non-gambling)**
- Single-pick mode: **points = round(10 / p_model(picked outcome))**, capped (e.g., 10–200) and floored. If the model is calibrated, every pick has the same expected value (10 × p_true / p_model ≈ 10), so there's no exploit in always picking rare events. Users only gain by **beating the model's knowledge**. Language is "rarity points", never odds.
- Confidence mode (Cricket IQ): user allocates a probability distribution and is scored with a **logarithmic or Brier proper scoring rule**. That measures calibration directly.
- Streaks, daily puzzle (Wordle-style "5 moments a day", shareable result grid), leaderboards (daily/series/global/friends leagues), badges.

**Cricket IQ:** per-dimension Bayesian skill ratings (e.g., Glicko-like on scoring-rule residuals) for outcome prediction, wicket-route prediction, T20/ODI/Test, death overs, chasing. Insight cards are generated from systematic bias, e.g. "You pick sixes 2.3× more often than they occur in these situations."

## 22. Ask Cricket architecture

```
User question
  → (1) Entity resolution: players/teams/venues via fuzzy index over Person/Team/Venue (+ aliases, nicknames)
  → (2) LLM parser → Query IR (JSON, strict schema: metric[], filters AST, group_by, order, limit, min_sample, viz_hint)
       • small fast model, constrained JSON output, few-shot from a curated question bank
  → (3) Validator: schema check; metric/filter existence; data-capability check
       (asks for line/length/shot? → reply "we don't hold that data yet" + closest supported alternative)
  → (4) Compiler → SQL (DuckDB) via the same semantic layer as the UI
  → (5) Execute → result table + coverage + sample sizes + delivery query handle
  → (6) Visual planner: maps IR + result shape → component (Matchup grid, DismissalMap, SituationMap, table…)
  → (7) Narrator LLM writes ≤3 sentences using ONLY the result payload
  → (8) Number guard: every numeral in the narration must match a value (or allowed rounding) in the payload;
        otherwise regenerate or fall back to a templated sentence
  → Answer = explanation + visual + "Show the deliveries" + "How this was computed" (IR + filters shown as chips)
```

- **"Why" questions** ("why does he struggle outside off?") → the system answers with *evidence* (what the data shows) and explicitly declines causal or biomechanical claims: "The data shows X; it can't tell us why." Line-based questions are flagged as needing data we don't have.
- **Caching:** normalised-IR cache; popular questions pre-answered.
- **Cost control:** the parser runs on a small model, and the narrator is optional (templated narration for simple answers). Free-tier rate limits apply.
- **Evaluation:** a golden set of 500+ question→IR pairs, with CI regression tests on parse accuracy and zero tolerance for unsupported numbers.

## 23. UX / information architecture

**Primary navigation (mobile bottom bar, 5 items):** `EXPLORE · PLAYERS · MATCHUPS · PREDICT · ASK`.
RECORDS sits inside EXPLORE. LIVE appears as a contextual top banner when we have a live feed (post-MVP).

**Player page (progressive disclosure)**
```
Hero: name, role chips, coverage note ("ball-by-ball coverage: 2008–2026, 94% of T20 career")
Layer 1  (casual):  3 headline insights (Evidence Cards, templated plain language)
Layer 2  (curious): Stats table with format tabs + filter chips
Layer 3  (geek):    Visual tabs → FORM · DISMISSALS · HOW HE GETS OUT · MATCHUPS · SITUATIONS · VENUES · RECORDS · PREDICTIONS
Layer 4  (obsessive): any element → "17 deliveries" → Delivery Explorer → Delivery Card (scene + context + model prob before ball)
```

**Interaction patterns**
- **Filter chips** persisted in the URL (shareable deep links); every visual reacts.
- **Breadcrumb drill path**: `Kohli › Dismissals › Caught › Keeper › Pace › Death overs › 9 deliveries`.
- **Always-visible sample size** on every number (`n=412 balls`), with greyed state below min-sample.
- **Provenance badges** with a one-tap explainer.
- **Share cards**: auto-generated images for any insight, matchup or game result (a growth loop).
- **Design language:** dark-first "night match under lights" palette with a light theme. Typography-led, generous motion, no grid-of-KPI-tiles dashboards and no sportsbook greens and reds.

## 24. Cost-conscious technical architecture

| Concern | Choice | Why |
|---|---|---|
| Ingest & transforms | **Python** (pydantic, polars) + **dbt-duckdb** | Free, fast, reproducible; small data |
| Analytical store | **Parquet + DuckDB** | 1 GB-scale data; zero ops; embeddable in the API and even the browser |
| Serving analytics | **FastAPI + DuckDB (read-only)** on one small container | Sub-100ms queries at this scale |
| Client-side analytics | **DuckDB-WASM** for per-player Parquet slices (optional, Phase 2) | Instant filter interactions; offloads server |
| Hot pages | Precomputed JSON on CDN | Near-zero cost at scale |
| App DB (users, predictions, leagues) | **PostgreSQL** (managed free tier, e.g., Supabase/Neon) | Transactional; auth included |
| Cache | None initially (CDN + in-process LRU); Redis only when live arrives | Avoid ops cost |
| Frontend | **Next.js (React, TypeScript)** as a **PWA**; static export where possible | SEO for player and record pages (an organic growth channel); one codebase for mobile web |
| Graphics | **SVG + D3 (scales/shapes only)**, Canvas2D for dense layers, **react-three-fiber** lazily for 3D (post-MVP) | PixiJS/WebGPU unjustified now |
| Mobile native | **Defer**; PWA first. React Native/Expo later if retention justifies it | Saves months |
| ML | scikit-learn / LightGBM, trained locally; models exported to ONNX or served in FastAPI | Free |
| LLM | Claude API: Haiku-class for parsing, Sonnet-class for complex narration; aggressive caching | Spend scales with usage; capped by rate limits |
| Object storage | Cloudflare R2 (free egress) or similar | Raw zone + Parquet + share images |
| CI/CD | GitHub Actions (free tier) | Nightly Cricsheet sync + data-quality gates |

Explicitly **not** chosen now: ClickHouse (unneeded at <100M rows), Kafka (no live), Kubernetes, WebGPU, microservices.

## 25. Near-zero-cost infrastructure plan

| Item | Provider (example) | Est. monthly cost (beta, ≤10k MAU) |
|---|---|---|
| Static frontend + CDN | Cloudflare Pages / Vercel hobby | $0 |
| API container (FastAPI + DuckDB, 1 vCPU/1–2 GB) | Fly.io / Render / Cloud Run | $0–10 |
| Postgres + auth | Supabase / Neon free tier | $0 (→ $25 when outgrown) |
| Object storage | Cloudflare R2 (10 GB free) | $0 |
| Nightly ingest + model training | GitHub Actions / local laptop | $0 |
| LLM (Ask Cricket) | Claude API with caching + rate limits | $10–40 (usage-dependent) |
| Domain | — | ~$1 |
| **Total** | | **≈ $10–50 / month** |

Live data (post-MVP) adds about €29–$500/month depending on vendor and coverage.

---

## 26. MVP recommendation

**Scope:** limited-overs (T20 and ODI; internationals + major leagues), **men's and women's**. Tests are ingested and available in stats tables, but the Test-specific context engine and visuals come later.

| # | MVP feature | Class | Why it earns its place |
|---|---|---|---|
| 1 | **Player Intelligence**: batting/bowling/fielding with full filter set (incl. bowler type, batter hand, phase, position, situation) | A/B | Core destination; SEO; foundation for everything |
| 2 | **Dismissal DNA**: kinds × bowler type × phase × situation × fielder role, drill to deliveries | A/B | Novel depth; honest |
| 3 | **"How He Gets Out" graphic**: batter at crease with routes (Bowled, LBW, Caught-keeper, C&B, Caught-in-field ring, Stumped, Run out, Hit wicket), clickable | B | Signature visual, factual without tracking |
| 4 | **Matchup Lab**: batter × bowler, batter × bowler type, bowler × batter hand, timeline + ball strip + dismissals | A/B | Top fan question |
| 5 | **Situation Maps**: heatmaps over over × wickets, required-rate × balls-left, ball-of-innings | B | Our honest pitch-map substitute; genuinely new |
| 6 | **Strength & Weakness Evidence Cards** (shrinkage + FDR + min samples) | B | Credibility differentiator |
| 7 | **Records Explorer**: metric × filters × group × min-sample builder; curated record pages | A | SEO + virality ("highest SR vs left-arm pace at the death since 2022, min 100 balls") |
| 8 | **Delivery Explorer + Delivery Card** with law-constrained scene, pre-ball model probability, context, source link | B | Makes the drill-down spine real |
| 9 | **Innings Lab** (historical): worm, Manhattan, WP curve, ball strip, partnerships, key moments | A/B | "Make history explorable" |
| 10 | **What Happens Next? (historical, daily)**: outcome + wicket-route questions, rarity points, streaks, share grid, global + friends leaderboards | B | Retention loop |
| 11 | **Ask Cricket (constrained)**: IR → query → visual answer, number guard, "show deliveries" | B | Wow factor; controller for visual engine |
| 12 | **Model estimates**: win probability, next-ball distribution (inside Innings Lab, Delivery Card, Game) | B | Powers game and context |
| 13 | **Provenance system & coverage notices** everywhere | A | Non-negotiable trust layer |

**The "I've never seen this" moment we're targeting:** a fan types "how does Bumrah get left-handers out at the death?" and gets three evidence-backed sentences, a dismissal-route graphic, a situation heatmap, and "23 deliveries", each of which opens to its match moment with the pre-ball win probability.

## 27. Deliberately NOT in MVP

- Pitch maps, line × length engine, bowler map from batter's view (C)
- Shot Lab, Graphical Shot Explorer, wagon wheel / field map (C)
- Bat contact / Edge Map, stance & movement (D)
- 3D delivery replays (no data to justify them; avoid "fake tracking" optics)
- Live second-screen (C; licence cost + ops)
- Test-specific context engine (sessions/days need data we lack; model complexity)
- Native iOS/Android apps (PWA first)
- Pro tier / paywall (validate engagement first; design for it)
- Computer vision anything (research track only)
- Free-form LLM chat that isn't backed by queries
- Prizes of any kind in the game
- Player photos, team logos

## 28. Roadmap: MVP → advanced product

| Phase | Duration (indicative, small team) | Outcome | Gate to next phase |
|---|---|---|---|
| **0. Feasibility** (this doc) | done | Decisions | Your approval |
| **1. Data foundation (M1)** | ~3 wks | Canonical store, provenance, QA gates, curated attributes, metric registry, one vertical slice | Reconciliation tests pass; slice demo |
| **2. MVP build** | ~8–10 wks | Features 1–13 above, PWA, SEO pages | Internal + 50-fan alpha |
| **3. Public beta** | ~4–6 wks | Daily WHN, share cards, friends leagues, Ask Cricket golden-set ≥90% | D7 retention, shares/user, WHN DAU |
| **4. Commentary-NLP spike** | ~4–6 wks, ~$500–1,000 licence | Measured shot/line/length/catch-position extraction; go/no-go per field | Precision ≥90% on shipped fields + licence permits derived storage |
| **5. Shot Lab v1 / Catch-position "How He Gets Out" v2 / coarse pitch-bucket maps** | ~6–8 wks | First C-class graphics, provenance "classified from commentary" | Usage + accuracy audits |
| **6. Live second screen** | ~6–8 wks + feed licence | Live scores, live WP, live matchups, live WHN | Revenue path (Pro tier / sponsorship) |
| **7. Pro tier** | ongoing | Advanced filters, exports, custom research, creator tools | Conversion |
| **8. Tracking partnership** | opportunistic | Real pitch maps, trajectories, 3D replays (OBSERVED) | Partner deal (e.g., B2B vendor, associate board) |
| **9. CV research track** | parallel, small | Footage-rights partnerships with associates/domestic/women's leagues; delivery segmentation, shot classification | Legal clearance + accuracy |
| **10. Test cricket depth** | after 5 | Test WP, ball-age context, session estimates | |

## 29. Key risks

| Risk | Type | Severity | Mitigation |
|---|---|---|---|
| **Fans expect pitch maps/wagon wheels**; MVP visuals feel "less" than broadcasters | Product | High | Lead with what's new (matchups, dismissal DNA, situations, game); make honesty a brand value; fast-follow commentary spike |
| **Incomplete careers** (Cricsheet coverage starts mid-2000s; some matches missing) → numbers differ from "official" totals | Data | High | Coverage badge on every player; "career (ball-by-ball era)" label; consider licensed scorecard-level totals later |
| Player attributes (bowling style, hand, keeper) are curated → errors | Data | Medium | Multi-source verification, provenance + confidence, user error reporting, unknown ≠ guessed |
| Keeper inference errors → wrong "caught behind" | Data | Medium | Conservative inference; unknown when ambiguous; audits |
| Cricsheet licence/terms change or project stops | Data/Legal | Medium | Mirror raw zone; attribution compliance; budget for a licensed fallback |
| Vendor contracts forbid retention/derivation | Legal | High (for C features) | Negotiate explicitly; licence-segregated storage |
| LLM hallucination in Ask Cricket | Trust | High | IR-only path, number guard, golden-set CI, templated fallback |
| Over-interpreting noise as "weakness" | Trust | High | Shrinkage, FDR, min-sample, effect-size floors, confidence labels |
| Game perceived as gambling / regulatory exposure | Legal/Brand | Medium | No money/prizes; non-odds language; legal review per market |
| Model leakage in WHN (future info) | ML | Medium | Point-in-time features, date-split training, audits |
| Scope creep from a 50-point vision | Execution | High | Gate by data capability matrix; vertical slices |
| Mobile performance of rich visuals | Tech | Medium | SVG/Canvas, lazy 3D, performance budgets |
| Cold-start growth | Business | High | SEO record/player pages, shareable cards, creator partnerships, daily puzzle |
| Moat erosion (others use same open data) | Business | Medium | Moat = provenance store + derived features + visual grammar + models + user prediction graph + Cricket IQ |

## 30. Proposed first implementation milestone (M1): "Truthful Foundation + One Vertical Slice"

**Goal:** prove that the data, the provenance and the drill-down spine work end-to-end for one player experience.

**Deliverables**
1. **Ingest:** Cricsheet full archive → raw zone (checksummed) → canonical Parquet (`Match, Innings, Delivery, Dismissal, Review, Replacement, PlayingXI, Person`), with source lineage on every row. Nightly incremental sync.
2. **QA gates:** reconciliation tests (innings totals, wickets, legal-ball counts, XI membership); quarantine report.
3. **Reference curation v0:** batting hand, bowling arm/style family, keeper flag for top ~1,000 limited-overs players (Wikidata seed + manual verification), each with provenance.
4. **Derived:** `DeliveryContext` (score/wickets/target/RRR/phase/partnership/ball-of-innings), keeper inference, dismissal `route`.
5. **Metric registry v0** (≈25 metrics) + filter AST + SQL compiler + tests.
6. **API:** `/players/{id}/summary`, `/players/{id}/dismissals?filters`, `/matchups?batter&bowler|bowler_type`, `/deliveries?query` (all values carry provenance).
7. **Frontend slice (PWA):** one batter page with stats + filter chips, Dismissal DNA, **How He Gets Out** (SVG, provenance grammar), Matchup view, Delivery Explorer list → Delivery Card (law-constrained scene).
8. **Docs:** data dictionary, provenance policy, attribution page.

**Acceptance criteria**
- 100% of ingested matches pass QA or are quarantined with a reason.
- Every number on screen shows its sample size, and every visual element carries a provenance tag (enforced in tests).
- Spot-check of 20 players' T20I/IPL aggregates against Cricsheet-derived independent recomputation: exact match.
- Drill-down from any dismissal aggregate to the underlying deliveries in ≤3 taps.
- p95 API latency <150 ms on a 1 vCPU container.

**Decisions needed from you before M1**
1. Approve the MVP scope (limited-overs first, men's + women's).
2. Approve the stack (Python/DuckDB/Parquet + FastAPI + Next.js PWA + Postgres free tier).
3. Approve the provenance visual grammar as a product-wide rule.
4. Budget appetite for the Phase-4 commentary-NLP spike (≈$500–1,000).
5. Repository layout: this repo currently holds an unrelated README ("Goa Travel Price Intelligence Engine"). Should the cricket platform live here, or in a new repository?

---

## Appendix A — Full feature classification (A/B/C/D)

| Feature (brief §) | Class | Notes |
|---|---|---|
| 1 Drill-down NUMBER→PATTERN→VISUAL→DELIVERY | A/B | Core architecture |
| 2 Graphics engine: 2D | A/B | SVG scenes with provenance |
| 2 Graphics engine: 2.5D/3D | B (illustrative/reconstructed) / C (observed) | Defer 3D until tracking data |
| 3 Provenance classes | A | Architecture |
| 4 Player intelligence: core stats & filters | A | |
| 4 Filters: bowler type / batter hand / captaincy / keeper | B | Curated attributes |
| 4 Fielding: catches, stumpings, run-outs | A | |
| 4 Fielding involvement (drops, misfields) | C | Not in Cricsheet |
| 5 Batter Shot Lab | C (commentary NLP) / C (pro data) | |
| 6 Graphical Shot Explorer | C | |
| 7 Bat contact / edge map | D (coarse edge events: C) | |
| 8 Stance & movement | D | |
| 9 Line × Length engine | C | Schema ready in MVP |
| 10 Pitch heatmap | C | Situation maps substitute (B) |
| 11 Dismissal DNA (kind, bowler, type, phase, venue, year, format) | A/B | |
| 11 Dismissal DNA (line, length, speed, shot) | C | |
| 12 How He Gets Out: route-level | B | |
| 12 How He Gets Out: slip/gully/point/deep positions | C | |
| 13 Dismissal reconstruction (law-constrained) | B | RECONSTRUCTED label |
| 13 Dismissal reconstruction (trajectory-accurate) | C | |
| 14 Bowler Lab: phase, spell, batter hand, situation | A/B | |
| 14 Bowler Lab: delivery types (yorker, slower, googly…) | C (NLP coarse) / C (pro) | |
| 15 Graphical bowler map (pitch) | C | |
| 16 Matchup Lab (stats, timeline, dismissals) | A | |
| 16 Matchup Lab (pitch map, shot distribution) | C | |
| 16 Matchups vs bowler types / inverse | B | |
| 17 Wagon wheel 2.0 | C | |
| 18 Strength & Weakness engine (available dimensions) | B | |
| 19 Visual Weakness Explorer (pitch/trajectory/contact) | C/D | MVP version uses situation & dismissal visuals (B) |
| 20 Context engine: limited overs | A/B | |
| 20 Context engine: Tests (innings, lead, target, overs since new ball) | B | |
| 20 Context engine: Tests day/session/exact ball age | C/D | No timestamps |
| 21 Records engine (flexible queries) | A | |
| 22 Player comparison (stats, situations, dismissals) | A/B | |
| 22 Comparison by line/length/shot | C | |
| 23 Prediction: next ball outcome, WP, totals, milestones | B | |
| 23 Prediction: dismissal-type next match | B | Competing-risks model |
| 23 Prediction: line/length/shot | C | |
| 24 What Happens Next? (historical) | B | |
| 25 Visual predictions (where pitch / what shot / where ball goes) | C | Needs ground truth |
| 25 Visual prediction: how wicket falls (route) | B | |
| 26 Probability-weighted scoring, leaderboards, leagues, badges | A/B | |
| 27 Cricket IQ | B | |
| 28 Live second screen | C | Live feed licence |
| 29 Ask Cricket (on supported data) | B | |
| 30 Visual AI answers | B | |
| 31 Delivery Explorer | A/B | |
| 32 Historical Cricket Lab (innings/match/spell) | A/B | |
| 33–35 Data investigation, matrix, provenance | A | This document + M1 |
| 36 Computer vision | D | Rights-gated |
| 37 Reconstruction without tracking | B | Law-constrained + uncertainty rendering |
| 49 Tap-any-delivery mini scene | B (reconstructed) / C (observed) | |

## Appendix B — Law-constrained reconstruction rules (MVP set)

| Dismissal / event | What we may draw (and label) | What stays UNKNOWN |
|---|---|---|
| Bowled | Ball arrives at stumps; stumps broken (OBSERVED-implied) | Line, length, speed, movement, whether inside edge |
| LBW | Pitched **not outside leg**; impact with batter; ball projected to hit stumps (OBSERVED-implied by the Law); if a DRS review shows umpire's call, mark it | Exact pitch point, impact height, shot |
| Caught – fielder is the keeper | Ball travels behind the stumps to the keeper (DERIVED) | Edge type, line, length, shot |
| Caught & bowled | Ball returns to the bowler (OBSERVED) | Shot, trajectory |
| Caught – other fielder | "Caught in the field by X" ring zone (OBSERVED fielder, position UNKNOWN) | Fielding position, direction, distance |
| Stumped | Batter out of crease; keeper breaks wicket (OBSERVED-implied) | Line, length, shot |
| Run out | Which batter, which end if derivable from striker/non-striker (DERIVED), fielders involved (OBSERVED) | Throw path, positions |
| Hit wicket | Batter's body or bat breaks own wicket (OBSERVED-implied) | Mechanism |
| Six / four | Ball reaches/clears boundary (OBSERVED) | Direction (C) |
| Wide | Ball judged out of the batter's reach for a wide (OBSERVED) | Which side, how wide |

## Sources consulted in this sprint

- [Best Cricket APIs in 2026 — Highlightly](https://highlightly.net/blogs/best-cricket-apis-in-2026)
- [7 Best Cricket APIs in 2026 — api.market](https://api.market/blog/veer-hanuman-1/sports/best-cricket-api-2026)
- [EntitySport pricing plans — apis.io](https://apis.io/plans/entitysport/entitysport-plans-pricing/)
- [Sportmonks Cricket API](https://www.sportmonks.com/cricket-api) and [Sportmonks cricket docs](https://docs.sportmonks.com/cricket/getting-started/getting-started)
- [Goalserve cricket API prices](https://www.goalserve.com/fr/sport-data-feeds/cricket-api/prices)
- [CricShotClassify (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8072636/)
- [Front Pitch View shot extraction & ball tracking — IEEE DataPort](https://ieee-dataport.org/documents/front-pitch-view-shot-extraction-and-ball-tracking-cricket-using-deep-learning)
- [Cricket shot classification baselines (arXiv 2510.09187)](https://arxiv.org/abs/2510.09187v1); [arXiv 2211.12009](https://arxiv.org/abs/2211.12009v1)
- [CricViz app listing](https://apps.apple.com/app/id1044644979); [Cricket Australia partners with CricViz — SportCal](https://www.sportcal.com/newsletters/cricket-australia-partners-with-cricviz-ecb-lands-cawston-press-as-sponsor); [CricViz licensed data contract notice](https://www.stotles.com/explore/notices/d1dd676c-4338-4e17-8f63-71d32b447083/cricviz-licensed-data)
- Cricsheet (cricsheet.org): blocked from this sandbox; details from prior knowledge, **to be verified in M1 step 1**
