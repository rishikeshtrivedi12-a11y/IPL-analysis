# SupeRR Selector S2 — pipeline (rebuilt 15 Nov 2026, final 16 Nov)

## FINAL METHOD — read this first

Run order:

```
mkdir -p work
python3 -I build_state.py "<data pack folder>" work   # 1. state table
python3 -I tiers.py       "<data pack folder>" work   # 2. team tier map
python3 -I model3.py      work                        # 3. outcome model + win probability
python3 -I fixpi.py                                   # 4. CORRECTED Bhattacharjee-Lemmer index
python3 -I bigwkt.py                                  # 5a. FINAL BOWLERS
python3 -I pweight.py                                 # 5b. FINAL BATTERS (use the K=2 block)
```

`fixpi.py` writes `work/fixed_pi.parquet`, which both ranking scripts read. They load
`_base.py` (first 52 lines of `final2.py`) for the par model and ball valuation.

**Final outputs:** `results/BIGWKT_bowlers.csv`, `results/PWEIGHT_batters.csv`.

Then, to test the locked lists against published definitions (section below; run from the
project root, in this order, about 8 minutes in total):

```
python3 -I pipeline/published.py             # tag + score every definition -> work/PUB_bat.csv, PUB_bowl.csv
python3 -I pipeline/analyze_published.py     # spearman, overlap, consensus, exposure, ball-set overlap
python3 -I pipeline/robust_published.py 60   # split-half reliability + 60-rep match-clustered bootstrap
python3 -I pipeline/crosshalf_published.py   # model on half A vs definition on half B
```

`published.py` needs only `work/fixed_pi.parquet`, `work/Eg.npy`, `work/PW_bat.csv` (from
`pweight.py`) and `work/BIGWKT_bowl.csv` (from `bigwkt.py`). It re-scores the locked model
first and asserts it reproduces the locked SCOREs (max abs diff 1e-14 on 16 Nov).

**Missing file:** `pipeline/allround.py` is not in the project. `knockout.py`, `reliability.py`
and `verify_items.py` all open with `exec(open('pipeline/allround.py')...)` and cannot run
without it. The whole final chain above, and everything in the published-definitions
section, does not depend on it. On 16 Nov `work/` was rebuilt from the data pack alone and
reproduced both locked lists exactly (Shami 52.3, Abhishek Sharma 44.5, same order).

### The five parts of the final method

**1. Pressure definition.** Bhattacharjee-Lemmer (2016) index in its published form:

```
PI = (CRRR/IRRR) x 0.5 * [ exp(RU/100) + exp(sum_w_i / 11) ]
```

with two deliberate departures:

- **Demand term `D` replaces CRRR/IRRR.** `D = runs still needed / expected runs from
  this state`. Works identically in both innings (CRRR/IRRR is undefined in the first)
  AND fixes the main published criticism of the index — see "Literature".
- **Bowling side is the sign-reversed mirror**: `1/D`, and `exp((Wmax - sum_w_i)/11)`
  for the wicket term, resources term unchanged. Follows Thomson & Swartz's symmetry
  argument, not our invention.

`sum_w_i` uses Lemmer (2015) wicket weights by batting position
(1.30, 1.35, 1.40, 1.45, 1.38, 1.18, 0.98, 0.79, 0.59, 0.39, 0.19).

Blended 50/50 on within-cell percentiles with a dot-ball squeeze term. Tagging is the
hardest **30%** of live balls (win probability 0.05–0.95) **within each
(match, innings, phase) cell**, so every innings contributes its own hardest balls.

**2. Ball valuation.** Each ball scored against a shrunk par (M=100, Dirichlet toward
coarser parents) conditioned on era, innings, phase, wickets, required-rate bucket,
recent dots, and — for bowlers — batter set-ness. Leave-one-player-out, so no ball is in
its own par. Batters: runs vs par, minus wicket value × (out vs par). Bowlers: runs saved
vs par, plus wicket value × (wickets vs par).

**3. Big-wicket weighting (bowlers).** Wicket credit is multiplied by the dismissed
batter's Lemmer position weight / mean weight, so a top-order dismissal is worth ~1.5×
a number-eleven's ~0.2×. Dismissing Suryakumar no longer counts the same as dismissing
a number nine.

**4. Player effect.** Two-way fixed effects by alternating projection (80 iters, KP=150
players, KI=20 innings), after removing the global weighted mean. The innings term
absorbs conditions and selection; the player term is his own skill.

**5. Recency, downside variance, pressure weighting.** Season rates weighted by
`0.65^(2026-season)` × balls (half-life ~1.6 seasons). Score
`= (weighted mean − 0.50 × downside sd) × balls/(balls+150)`, where downside sd counts
only seasons *below* the player's mean — so being sometimes brilliant is not punished,
only collapsing is. Seasons need 40+ balls to enter the sd.

Within the tagged set, each ball is weighted `1 + K(pct − 0.70)/0.30`, so the very
hardest balls count (1+K)× the threshold balls. **K=2 for batters, K=0 for bowlers** —
a role-specific choice justified by concentration, see "Findings".

**Ranking metric: rate only.** Volume does not enter the score, only the shrinkage.
Eligibility: 300+ pressure balls and 20+ innings (bowlers), 350+ and 25+ (batters).

### FINAL LISTS

**Bowlers** (`BIGWKT_bowlers.csv`): Shami 52.3, Hazlewood 34.8, Boult 34.7,
Hasaranga 30.8, Archer 23.3, Bhuvneshwar 22.1, Harshit Rana 16.7, Chakravarthy 16.1,
Arshdeep 15.1, Siraj 14.1. (Axar #11, Hosein #14, Bumrah #20, Narine #37 of 48.)

**Batters** (`PWEIGHT_batters.csv`, K=2): Abhishek Sharma 44.5, Jaiswal 31.1,
Nissanka 30.3, Marsh 25.6, Samson 23.1, Salt 22.5, Suryakumar 21.6, Rohit Sharma 14.5,
Gill 12.6, Kohli 10.3.

**Present these as tiers, not a strict 1-to-10.** Batting: Sharma alone (44.5 vs 31.1),
then a tier of five, then the rest. Bowling: Shami alone (52.3 vs 34.8), then Hazlewood
through Bhuvneshwar, then a cluster. The bootstrap gives P(rank 1 > rank 2) ≈ 52% for
adjacent names inside a tier — a coin flip. **Read the next section before presenting any
single name as robustly best: several of these only lead under this pressure definition.**

### Validation

| Check | Result |
|---|---|
| Suppression bias on tagged balls | 0.000 (algebraic) |
| corr(value, total defended) | −0.012 |
| corr(value, team-mate quality) | +0.773 (real talent clustering, not a penalty) |
| spearman(shrunk rate, unshrunk rate) | 0.997 bowlers / 0.999 batters |
| D on ball 1 of a chase | 0.34 to 1.79, corr +0.969 with target |
| P(Sharma > Jaiswal), match-clustered bootstrap | 51.9% — a tie |
| Big-wicket vs flat wicket credit | spearman 0.990, 9/10 top-10 overlap |
| Batters, K=0 vs K=4 pressure weighting | spearman 0.969, 9/10 overlap |
| Bowlers, K=0 vs K=4 pressure weighting | spearman 0.953, **6/10 overlap** |

The 0.997/0.999 rank correlation is the proof that volume has no effect on the ordering.

---

## Tested against published definitions (added 16 Nov, after the model was locked)

**Question.** Does the locked ranking survive when "pressure" is defined the way other
people define it? Same value metric throughout (runs vs par per 100 balls, player and
(match, innings, phase) fixed effects, 0.65 decay, balls/(balls+150) shrinkage, downside
sd); only the rule that selects the balls changes. Pools are the locked eligible sets: 34
batters, 48 bowlers.

**Choices fixed before looking at results.** (1) Every definition keeps the live-ball gate
(win prob 0.05 to 0.95). (2) A player needs 100 or more tagged balls to be ranked under a
definition. (3) Flat weights (K=0) for every alternative. The locked model is also re-run at
K=0 (`M0`) so differences are not a K effect.

**Definitions.**

| Code | Rule | Group |
|---|---|---|
| LEV30 | top 30% of live balls by leverage index (global threshold, WPA tradition) | independent |
| RRR10 | second innings, required rate >= 10 (batters only; a common threshold, **not** a Thomson-Swartz rule) | independent |
| CLOSE | win prob 0.25 to 0.75 (tags **70% of live balls**, so a weak filter) | independent |
| DEATH | overs 16 to 20 | independent |
| BL | BL index only, hardest 30% per (match, innings, phase) | same lineage as locked model |
| BLCH | BL index, second innings only | same lineage |
| DOT | dot squeeze only | same lineage |
| LEMPR | required rate x resources used, second innings (batters only), see Lemmer note | same lineage |
| WPA | de-drifted WPA per 100 balls, all live balls and leverage top 30% | value-metric check |

"Independent" means no term in common with the locked blend. They are only partly distinct from
each other too: tagged-ball overlap (Jaccard) runs 0.09 to 0.33 between them. DEATH is purely
late-innings; LEV30 puts 35% of its tags in overs 3 to 6; CLOSE follows the all-live phase mix.

**Lemmer's choking measure cannot be used as a player definition.** Lemmer (2015a) is a
team-level, match-level curve: required run rate times DLS resources used at the end of each
over, plotted against overs, with choking measured by the ratio of the slopes either side of
the point where it bends upward. It has no per-player attribution and is not a ball-tagging
rule. (2015b, strangling, is the same idea for a team that needs a few runs with many balls
left.) What is implemented as `LEMPR` is only its pressure quantity, required rate x resources
used (resources from our fitted expected-runs table, not DLS), used as a chase-only ball tag. It
is an adaptation, not Lemmer's measure. Earlier notes saying it could serve as a player-level
external benchmark were wrong. Combined Bowling Rate is still not implemented.

### Results (spearman vs locked list · names shared with locked top 10)

| Definition | Batters | Bowlers |
|---|---|---|
| M0 (locked model at K=0) | 0.98 · 9 | 1.00 · 10 |
| LEV30 | 0.40 · 6 | 0.67 · 4 |
| RRR10 | -0.10 · 3 | n/a |
| CLOSE | 0.26 · 3 | 0.63 · 5 |
| DEATH (25/34 batters, 43/48 bowlers rankable) | 0.08 · 1 | 0.27 · 3 |
| BL | 0.88 · 8 | 0.87 · 7 |
| BLCH | 0.73 · 7 | 0.78 · 7 |
| DOT | 0.64 · 7 | 0.81 · 6 |
| LEMPR | 0.26 · 5 | n/a |
| WPA per 100, all live balls | 0.30 · 3 | 0.56 · 3 |
| WPA per 100, leverage top 30% | 0.25 · 3 | 0.54 · 1 |

The same-lineage rows agree largely because they tag the same balls (Jaccard with the locked
tag set: BL 0.58, DOT 0.52). The independent rows agree weakly.

### Why they disagree, and how much is noise

- **Mostly structural, not skill.** The locked tagging reproduces the phase mix of all live balls by
  construction (that is what makes openers rankable). DEATH is 100% overs 16 to 20. On average
  58% of the locked top-10 batters' pressure balls fall in overs 1 to 6, against 30% for the
  other 24. How much worse a batter does on the independent definitions than on ours correlates
  +0.62 with his early-innings share (-0.64 with late share); bowlers +0.28 / -0.22. Openers have
  28 to 51 death-over balls, so DEATH cannot rank them at all (9 of 34 batters unranked).
- **Reliability is moderate to poor.** Split-half r, Spearman-Brown to full length: batters locked
  model 0.64, LEV30 0.42, RRR10 0.29, CLOSE 0.54, DEATH 0.50, independent consensus 0.55.
  Bowlers locked model 0.48, **LEV30 0.11**, CLOSE 0.32, DEATH 0.40, consensus 0.36. Bowler
  leverage rankings are close to noise. (Deck page 33 reports 0.69 / 0.47 for the locked lists
  from a different random-split draw; consistent.)
- **Out-of-sample agreement is poor.** Locked model scored on one random half of matches vs a
  definition on the other half (12 splits, both directions; ceiling = sqrt of the two split-half
  reliabilities): batters LEV30 +0.14 (ceiling 0.35), RRR10 -0.16 (0.28), CLOSE +0.10 (0.42),
  DEATH +0.01 (0.39); bowlers LEV30 +0.20 (0.13), CLOSE +0.17 (0.24), DEATH -0.01 (0.28).
  Ceiling-corrected values are unstable where a definition's own reliability is near zero
  (bowler LEV30 comes out at 1.5, which means only "cannot tell"). The in-sample correlations in
  the table above overstate agreement, because the lists share the same matches and so the same noise.
- **Exposure is not the explanation.** Spearman of consensus rank vs tagged-ball count is -0.13
  (batters) and -0.14 (bowlers); weak.

### Who holds up and who does not

Match-clustered bootstrap, 60 resamples of whole matches, tag sets held fixed (so intervals are a
little too narrow, especially for LEV30's global threshold). P(top 10) is within the pool
(29% of batters, 21% of bowlers are top 10), on the locked model and on the independent consensus.

**Batters.**
- **Holds up:** Suryakumar Yadav (top 10 under all 8 definitions, worst rank 10th; P 0.85 locked,
  0.90 consensus). Phil Salt (locked 6th, consensus 6th; P 0.85 / 0.75; top 10 under 5 of 7).
  Abhishek Sharma is 1st on leverage, 2nd on close games, 1st on BL, but 30th of 33 in chases
  needing 10 or more and has only 51 death-over balls (P 1.00 / 0.52).
- **Only under ours:** Rohit Sharma (locked 8th; 29th leverage, 33rd close games; top 10 under 0 of
  7; P 0.55 / 0.00). Samson (33rd leverage; P 0.88 / 0.02). Gill (P 0.45 / 0.03). Nissanka
  (3rd; 27th on close games; P 0.98 / 0.25). Kohli's own locked top-10 place is P 0.28.
- **Missing from our list:** Tim David (locked 11th; top 10 under 7 of 8; P 0.25 / 0.92), Tilak
  Varma (20th; 1st on death overs; P 0.12 / 0.88), Klaasen (26th; 4th on leverage; P 0.02 / 0.82),
  Shreyas Iyer (12th; P 0.32 / 0.73).

**Bowlers.**
- **Holds up:** Hasaranga (P 0.85 / 0.65), Bhuvneshwar (0.60 / 0.48), Hazlewood (0.78 / 0.57),
  Archer (0.62 / 0.35), Chakravarthy (0.47 / 0.77). Each is top 10 under at least half of 6
  definitions.
- **Only under ours:** Shami (locked 1st; 1st on BL and DOT, 42nd of 43 on death overs; P 0.97 /
  **0.02**). Siraj (3rd on BL, 32nd on leverage; P 0.55 / 0.07). Harshit Rana (37th on death
  overs; P 0.38 / 0.02). Boult (P 0.85 / 0.23) and Arshdeep (0.55 / 0.22) are in between.
- **Missing from our list:** Bumrah (locked 20th; 2nd on death overs, 5th on close games; P 0.07 /
  0.75), Narine (37th; **1st on death overs**, 16th close, 19th leverage, 33rd BL; P 0.00 / 0.57),
  Pathirana (22nd; P 0.10 / 0.68), Krunal Pandya (13th; P 0.38 / 0.68).

**What to say.** Our lists are the best at the hardest balls of each phase, not the best at the end
of an innings. Suryakumar is the only name that is top 10 on everything. Shami's lead is real under
our tagging and does not travel; claiming him as robustly the best bowler under pressure is not
supported. Bowler rankings overall are about half signal.

### Limitations specific to this test

- **Not read directly:** Thomson & Swartz (README summary only), Bhattacharjee & Lemmer's bowling
  form, Lemmer 2015a/b beyond the abstracts. `RRR10` is a common threshold, not their rule; their
  clutch window (win prob 0.25 to 0.50, excluding balls under 10% resources) was not run.
- The 100-ball threshold and the live-ball gate are choices; DEATH and RRR10 are the definitions
  most affected by the threshold (fewest openers and top-order batters clear it).
- RRR10 and LEMPR are one-sided (batting side under pressure in a chase) and are not defined for
  bowlers; the bowler consensus rests on only 3 independent definitions (LEV30, CLOSE, DEATH), so
  one definition's quirks move it. CLOSE tags 70% of live balls, so it barely filters.
- The WPA checks use our win-probability model; they are free of the par model and the pressure
  tag, not of the win-probability model.
- A top 10 out of 34 or 48 is a loose bar; 10 of 34 would be 29% by chance.

---

## Widened pool, lower tier and final combined list (added 16 to 17 Nov)

The locked lists above are unchanged. This section is the selection view built on top of them. Everything here is
produced by one script, `pipeline/final_list.py`; the earlier scripts (`published150.py`, `bowl_rrr.py`) and
their `results/PUB150_*` files are kept for provenance and are superseded by it.

**Rules.**
- **Eligibility** is the original bars: 350 tagged balls and 25 innings (batters), 300 and 20 (bowlers). A wider
  pool (150 balls, 10 innings, 113 batters and 115 bowlers) is produced as a watch list; its extra players are
  marked `provisional`. Scores do not depend on the bar, so every player keeps his score in both.
- **Lower tier.** Anyone who appears for Pakistan or Pakistan A in the data pack (matched on player id, not
  name) is ranked in a separate lower tier, because the BCCI has not allowed Pakistani players in the IPL since
  2009 (news reports; a Pakistan-born player with another nationality, such as Azhar Mahmood, was the exception).
  This is a selection rule, not a model finding. It removes only Rizwan from the locked batting pool (33 batters
  and 48 bowlers remain). **Afghanistan is not in the lower tier**: Afghan players are in the IPL (Rashid Khan,
  Noor Ahmad, Omarzai, Farooqi), so there is no eligibility reason. An earlier version of this section put them
  there at Rishi's request; that was removed because it had no reasoning behind it, and it changes the order of
  the final ten but not its membership. Two same-name players on other sides (Rashid Khan of Nepal, Haider Ali of
  the UAE) have different ids and are not an issue.
- **Definitions.** The eight of the previous section, plus `RRRB`, a bowling mirror of RRR10 so that bowlers are
  ranked on 7 definitions and batters on 8 (LEMPR remains batter-only; no bowling counterpart of Lemmer's choking
  measure was found). RRRB tags live second-innings balls with required rate <= 9.00, the quantile that gives the
  same share of live chase balls as RRR10 (27,436 against 27,307 balls). The cut-off was fixed before any bowler
  was scored and no other value was tried. It is a weak filter: 9.00 is below the typical chase required rate
  (median 9.48), so "the batting side is cruising" overstates it.
- **Combined score** = 0.5 x percentile of the model score within role + 0.5 x mean percentile over the
  definitions the player can be ranked on (at least 4; a definition ranks a player only with 100 or more tagged
  balls). Lower is better. Percentiles are recomputed inside each pool. The 0.5 weight is a judgement call.

**Final top 10 (locked eligibility, Pakistan tier excluded).** Model rank is the rank on the model score within the pool.

| # | Player | Role | Model rank | Top 10 on N of definitions | Worst rank |
|---|---|---|---|---|---|
| 1 | Wanindu Hasaranga | bowler | 4 | 5 of 7 | 22 |
| 2 | Abhishek Sharma | batter | 1 | 5 of 7 | 29 |
| 3 | Bhuvneshwar Kumar | bowler | 6 | 6 of 7 | 12 |
| 4 | Jofra Archer | bowler | 5 | 5 of 7 | 25 |
| 5 | Josh Hazlewood | bowler | 2 | 4 of 7 | 22 |
| 6 | Yashasvi Jaiswal | batter | 2 | 4 of 7 | 20 |
| 7 | Trent Boult | bowler | 3 | 3 of 7 | 29 |
| 8 | Varun Chakravarthy | bowler | 8 | 4 of 7 | 18 |
| 9 | Suryakumar Yadav | batter | 7 | 8 of 8 | 10 |
| 10 | Mohammed Shami | bowler | 1 | 3 of 7 | 42 |

Next: Marsh 11, Nissanka 12, Salt 13, Axar Patel 14. Seven bowlers and three batters; no hand edits.

**Read this before presenting it.**
- Scores 0.108 to 0.165 across the ten. Gaps inside it are small and not separable; present a tier.
- Suryakumar is the only name top 10 on every definition. Shami leads the model but is 42nd of 43 on death overs.
- The list leans to bowlers (7 of 10). Cause not tested; one candidate is that batters are unrankable on several
  definitions (DEATH ranks 24 of 33 batters) and lose consensus breadth.
- Reliability caveats of the previous section apply, worst for bowlers.
- **Watch list** (wide pool, `work/FL_wide_comb.csv`): Sooryavanshi (+51.3 on 194 balls, India T20I debut July
  2026, so capped, not uncapped), Chahar (+31.5, 75% of his tagged balls in overs 1 to 6 and top-order wickets
  are weighted up, so part role), Finn Allen, Naman Dhir. Priyansh Arya (+28.0) has 117 tagged balls, below even
  the 150 bar. Cap status came from web searches and may be out of date; the data pack has no age or cap field.
  Sooryavanshi's score bootstrap (5th, 50th, 95th percentile) is 25, 49, 64 (seed 1) and 30, 51, 69 (seed 7).
- An earlier version of this list filtered the 150-ball pool's percentiles instead of re-ranking inside the true
  pools. That put Marsh 10th and Shami 12th; the correct re-ranking above has Shami 10th and Marsh 11th. Lists
  shown in chat before that fix, or with Afghanistan in the lower tier, are superseded.

**Published bowling form of the index.** Lemmer and Bhattacharjee (2018) quote the bowling form as
BI = (1/CI) x [(11 - sum w)/11 + exp(RU/100)] / 2. Ours differs only in the wicket term
(exp((Wmax - sum w)/11) instead of the linear term). `bowl_pubform.py`: within-cell rank correlation 0.948,
tag-set Jaccard 0.83, bowler list with the published form spearman 0.963 and 9 of 10 top-10 names shared. The
locked lists were not changed.

**Tests.** `final_list.py` first re-ranks the original 34 and 48 pools and asserts that the model rank and every
definition rank equal `published.py`'s output. `final_checks.py` (all pass) then checks: no-bar scores reproduce
the locked lists to 1e-14; eligibility bars, tier membership, contiguous ranks and sort order of the saved
lists; ball counts against the raw file; SCORE by hand; the combined-score arithmetic; the RRRB share; this
README's top 10 against `work/FL_locked_comb.csv`; a second bootstrap seed.

Run order: `uncapped.py`, `final_list.py`, `final_checks.py` (plus `bowl_pubform.py` for the index comparison).

---

## Literature — what we follow, diverge from, and could cite

**Bhattacharjee, D. & Lemmer, H.H. (2016)**, *Quantifying the pressure on the teams
batting or bowling in the second innings of limited overs cricket matches*, Int. J.
Sports Science & Coaching 11(5), 683-692. The index we use. PI = (CRRR/IRRR) ×
½[e^(RU/100) + e^(Σwᵢ/11)].

**Lemmer, H.H. (2015)** — wicket weights by batting position, used both in Σwᵢ and in the
big-wicket credit. Also *A Method to Measure Choking in Cricket*, Int. J. Sports Science &
Coaching 10(2+3), 461-477: a **team-level** choking measure built from required run rate times
resources used at the end of each over (see the section above); it cannot rank players, and only
its pressure quantity is adapted (`LEMPR`). *A Method to Measure Strangling* (2015b, 10(4),
715-726) is the same idea for a team that needs a few runs with many balls left. The Combined
Bowling Rate CBR = 3R/(B/6 + R/W + W) is not implemented.

**Thomson, J. & Swartz, T.B.**, *Contextual Batting and Bowling in Limited Overs
Cricket* (SFU). Two things matter:
- They criticise BL and Shah-Shah because **the second innings always commences with
  PI = 1 (or 100), so the index cannot distinguish a large target from a small one.**
  Their fix is `r = runs required / resources available`. Our `D` is structurally the
  same object with a fitted expected-runs table in place of DLS percentages.
  **Verified: our D on ball 1 of a chase runs 0.34 to 1.79 and correlates +0.969 with the
  target, where BL returns exactly 1.00 for every chase.** The change made for
  first-innings reasons is also the published remedy for the index's best-known flaw.
  Cite this.
- Their bowling treatment is **the same ratio with the sign reversed**, no separate
  bowling formula. Validates our mirror.
- Not adopted: they standardise each ball by the sd of the ratio change across the seven
  possible outcomes, and define clutch only over win probability 0.25–0.50, excluding
  balls under 10% resources remaining. Both are reasonable sensitivity checks not run.

**Mallawa Arachchi, D.K., Manage, A.B. & Scariano, S.M. (2024)**, *A pressure index for
the team batting second in T20I cricket*, J. Sports Analytics. Derives a PI from a
differential equation, scaled 0–10, reports better prediction accuracy than BL's PI₃.
Not used — we rank within cells, which normalises adaptively. Cite to show the choice of
BL was deliberate.

**Bandyopadhyay, R. & Bhattacharjee, D. (2025)**, arXiv:2505.01849 — higher-order Markov
models on the PI; a controlled chase keeps PI inside [0.5, 3.5].

**Shah, P. & Shah, M. (2014)**, *Pressure Index in Cricket* — the original. Rejected by
later authors and by us.

Unread: Bhattacharjee et al. (2019) solve the first-innings problem by setting an initial
target T₀ = μ + σ. Our state-based D avoids that arbitrary choice.

---

## Defects found and fixed

1. **`comp_name` was never merged** into the ball table by `build_state.py`, but
   `model2.py` and `stage4.py` both used it. The pipeline could not run end to end as
   delivered. Fixed in `build_state.py`.
2. **`first_inn_revised_overs` / `second_inn_revised_overs` are in BALLS, not overs.**
   Every value is a multiple of 6, the maximum is 114 (19 overs), and of 23 DLS chases 13
   ended at exactly that figure with none exceeding it. The old build multiplied by 6.
   Now applied per innings, not per match.
3. **Innings 2 was never recalibrated.** Model said 2.5% where reality was 5.9%.
   `model3.py` fits logistic (Platt) recalibration per innings. Innings 2 lowest bin now
   0.027 predicted against 0.030 actual; Brier 0.1258 → 0.1249.
4. **A hidden leverage filter.** `stage4.py` opened with `bb = bb[bb.li >= 0.1]`,
   silently dropping 18,970 balls (9.8%). Gone.
5. **The pressure index tagged decided matches.** 42% of batting and 41% of bowling
   pressure balls had the pressured side below 5% win probability. Fixed by the liveness
   gate.
6. **`.rpow(1)` typo** collapsed the venue factor to exactly 1.000 at all 97 grounds.
7. **The phase-equalisation multiplier was the worst bug in the project.** Equalising
   tagged balls across phases produced weights of 4.27× on over 20 and 3.71× on over 19.
   Jofra Archer's **6 balls in over 20 became 52.8% of his entire rating**. This is what
   made the top 10 unstable to every change in the tagging. Removed entirely.
8. **Bowler par had a −0.086 runs/ball circular bias.** Concentrated in innings 1
   (−0.0913 vs −0.0281 in innings 2). Cause: with no real target, bowler "pressure" was
   defined off the pseudo-target as *the batting side is ahead of par*, which is literally
   *runs have been conceded above par*. Selection on the outcome variable's own running
   total. 61% of tagged bowler balls were in innings 1. Batter set-ness explained almost
   none of it (−0.0726 → −0.0665).
9. **Innings demeaning charged bowlers for their team-mates' quality.** The first fix for
   (8) subtracted the innings mean, driving corr(value, team-mate quality) to −0.069 when
   the true value is strongly positive — good bowlers cluster in good attacks. Replaced
   with two-way fixed effects, which separate innings from player effects.
10. **Global centering was missing** from the first two-way fit, so the +0.157 tagging
    bias leaked into every player's effect and inflated all rates (Arshdeep showed 67.7
    runs/100 balls).
11. **Ranking on total value weighted volume.** Arshdeep ranked 1st on 956 balls despite
    a per-ball rate below Shami's, Chakravarthy's and Archer's. Now rate only.
12. **The resources term was sign-inverted.** Published form is `e^(RU/100)` with RU the
    percentage of resources USED, so pressure rises as the innings is consumed. Ours was
    `exp((100-ru)/100)` — resources REMAINING — so pressure *fell* as the innings
    progressed. Within a phase RU is nearly constant, so the term's value barely varies,
    but its magnitude relative to the wicket term flips by phase: ~2.7 early and ~1.04
    late under the bug, ~1.05 early and ~2.6 late corrected. That reweighting of demand
    against wickets changed **4 of the top 10 bowlers and 2 of the top 10 batters**
    (spearman 0.92 bowlers, 0.77 batters). Boult 12→3, Hasaranga 11→4, Siraj 17→9,
    Arshdeep 6→12, Shaheen out of the qualifying pool entirely; Buttler 9→22,
    Pooran 8→27, Rohit 13→7.
13. **Equal wicket weights instead of Lemmer's.** Used `exp((11-k)/11)`, weighting every
    wicket identically. **Immaterial**: corr(equal-weight proxy, Lemmer Σwᵢ) = 0.9956,
    because wickets mostly fall in batting order. Fixed anyway.
14. **Wicket credit ignored who got out.** Any wicket counted 1.0, so dismissing a top
    batter paid the same as dismissing a tailender. Now weighted by Lemmer position
    weight. Also near-immaterial (spearman 0.990) for the reason in "Findings", but it is
    the more correct construction and it is citable.

## Findings

- **Top-order batters are now rankable.** Overs 1-2 carry 3,012 pressure balls where the
  entire old powerplay had 215. Top-order share of tagged balls went 1.3% → 6.2%.
  Openers were also penalised twice: overs 1-2 score 7.12 rpo against 8.89 for overs 3-6,
  a 27% par handicap the old single powerplay phase averaged away.
- **Dot pressure suppresses runs but reduces wicket rate.** Preceding dots cut scoring by
  0.57–1.43 rpo (surviving bowler, batter and match controls) but wicket rate falls
  5.91% → 4.62%. Contradicts the coaching orthodoxy that dots build towards a wicket.
- **Pressure transfers between bowling partners at ~40% strength.** Own dots −0.76 rpo,
  partner's dots −0.31 rpo.
- **On pressure balls, "wickets" and "big wickets" are nearly the same thing.** Of 4,947
  wickets on tagged balls, positions 1-5 account for ~4,000 and positions 9-11 for 139.
  Pressure concentrates where the top order bats, which is why position weighting cannot
  differentiate bowlers much.
- **Bumrah's pressure value is 97% economy.** Wicket component +11.1 of 373.7, i.e.
  league-average striking, against roughly 50/50 splits for everyone else. He contains
  without striking.
- **Bumrah's decline is two seasons, not one.** 2022 +19.4, 2024 +36.7, then 2025 +9.6 and
  2026 +9.3 — his two largest samples. Economy holds (65.8, 68.3) while the wicket
  component goes negative (−4.4, −2.4). No recency weighting rescues him; he is worse
  than baseline under every recency setting tested. **That holds only for this pressure
  definition: on death overs he is 2nd of 43 and on close games 5th (16 Nov test).**
- **Archer was genuinely underrated by career pooling.** 2023 −44.8 on 45 balls (injury
  return), then +24.7, +12.1, and **2026 +45.5 on 165 balls** — his best season is his
  most recent and his largest sample.
- **Chakravarthy is the most volatile bowler near the top** (−20.3, +14.0, +60.7, +69.3,
  −6.5). His rank rests on 2024-25 alone.
- **Jaiswal and Suryakumar rise when the hardest balls count more**, which means they
  perform at the sharpest end rather than on the easier tagged balls. A better argument
  for them than any tie-break.
- **Pressure weighting helps batters and wrecks bowlers.** At K=2 the batting list holds
  (9/10, spearman 0.969, concentration 16-31%) but the bowling list admits Krunal Pandya
  at 7th with 89.3% of his value from three innings — the phase-multiplier failure in a
  new guise. Median top-3-innings share is already **74% for bowlers against 60% for
  batters** at K=0.
- **The four-over cap is the root of several asymmetries.** A batter can face 40 balls in
  an innings; a bowler is capped at 24 and weak bowlers must bowl anyway. This explains
  (a) why top batters out-rate top bowlers by 2.8 runs/100 and equalising the eligibility
  *fraction* barely closes it (+2.74 vs +2.81), (b) why volume filters batting quality
  more sharply, and (c) why pressure weighting concentrates bowling value but not batting.
- **Clutch does not persist**: batters −0.12 to −0.14, bowlers +0.10 to +0.14.
- **Narine ranks near the bottom** of the qualifying pool: 9 dismissals in 47 pressure
  balls against 2.3 expected. Five model structures agree, **but all five share the same
  pressure tagging, so that is agreement on valuation, not on the definition.** Under the
  independent definitions he is 1st on death overs (181 balls), 16th on close games and 19th
  on leverage (16 Nov test); only the BL-family tags (BL 33rd, DOT 33rd) put him near the bottom.
- **Batters and bowlers are already on a common scale.** Both are runs vs par; spread
  ratio 1.04, and both roles get exactly 7.0 pressure balls per innings by construction,
  since every tagged ball has one batter and one bowler. Z-scoring within role and
  per-innings impact both reproduce the same top 10 and 6-4 role split. Role-centring
  removes the 2.8-run gap by construction if a role-neutral combined list is wanted.
- **Two-way tier effects are nearly flat** (0.91–1.09) against the hand-set 0.45–1.00.

## Remaining limitations — state these, don't bury them

- **Two-way fixed effects are weakly identified** with only 5–7 bowlers per innings. The
  innings and player terms are partly collinear, so some innings quality leaks into
  player effects.
- **KP=150, DECAY=0.65, LAM=0.50 and K are judgement calls**, not fitted values.
- **K differs by role (2 for batters, 0 for bowlers).** Justified by the concentration
  figures above, but it is a role-specific choice and must be declared.
- **The bowling list below the top four rests on few innings per player.** Top-3-innings
  share: Shami 36.5%, Hazlewood 34.0%, Boult 38.9%, Hasaranga 28.0% are spread; Siraj
  ~97%, Krunal ~89%, Archer ~73% are not. The ratio is unstable where net value is near
  zero, so treat the exact figures as indicative.
- **The 30% cutoff cannot be derived.** Scoring and wicket rates move smoothly across
  pressure percentiles with no kink.
- **The 50/50 blend** of Bhattacharjee-Lemmer and the dot term is a judgement.
- **The pressure definition itself drives the lists** (see "Tested against published
  definitions"): the locked lists agree only weakly with leverage, close-game, death-over and
  required-rate definitions, mainly because ours tags the hardest balls within each phase.
- **Quality bands are circular** — derived from run values produced by the same model,
  one pass, no iteration.
- **The eligibility bar drives who is rankable**, and the corrected index moved Shaheen
  Afridi out of the pool entirely by changing which balls are tagged.
- A pure rate metric measures quality while under pressure, not how often a player is
  trusted with it.
- **Ranks inside a tier are not separable.** P(Sharma > Jaiswal) = 51.9% on a
  match-clustered bootstrap; the point gap was 0.7 runs/100 against a CI width of 38.
- Bhattacharjee & Lemmer's own 2016 paper has not been read directly (ResearchGate blocked). The bowling
  formula was checked against how Lemmer & Bhattacharjee (2018) quote it: BI = (1/CI) x [(11 - sum w)/11 +
  exp(RU/100)] / 2. Our mirror differs only in the wicket term (exp((Wmax - sum w)/11) instead of the linear
  term). `pipeline/bowl_pubform.py` shows it barely matters: within-cell rank correlation 0.948, tag-set Jaccard
  0.83, bowler list with the published form spearman 0.963 and 9 of 10 top-10 names shared (Shami still 1st).
  Locked lists were not changed. No player-level or ball-level bowling counterpart of Lemmer's choking measure
  was found (Lemmer 2015b, strangling, is cited with it but its definition was not read), so LEMPR stays
  batter-only.
