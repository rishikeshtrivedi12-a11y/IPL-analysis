"""Out-of-sample agreement between the locked model and each independent definition.

Score the locked model on one random half of the matches and a definition on the other half
(both directions, NSPLIT random splits), so the two lists share no noise. Compare with the
ceiling set by each list's own split-half reliability (work/PUB_reliability.csv, run
robust_published.py first). disattenuated = cross-half r / sqrt(rel_model * rel_definition).
Unstable (> 1 or wildly negative) wherever a definition's own reliability is near zero,
e.g. bowler leverage (0.06); read those rows as 'cannot tell'.

Run from the project root:  python3 -I pipeline/crosshalf_published.py
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, 'pipeline')
import published as P
from published import d, DEFS, THIN, score

rng = np.random.default_rng(77); NS = 12
INDEP = {'bat': ['LEV30', 'RRR10', 'CLOSE', 'DEATH'], 'bowl': ['LEV30', 'CLOSE', 'DEATH']}
out = pd.read_pickle('work/pub_out.pkl'); rel = pd.read_csv('work/PUB_reliability.csv')
mids = np.sort(d.match_id.unique())

def sub(idx, pct, counts):
    m = d.match_id.loc[idx].values; inv = np.searchsorted(mids, m); rep = counts[inv]
    i2 = np.repeat(idx, rep); st = np.cumsum(rep) - rep; cp = np.arange(rep.sum()) - np.repeat(st, rep)
    return i2, (None if pct is None else np.repeat(pct, rep)), np.repeat(m, rep) * 100 + cp

rows = []
for side in ['bat', 'bowl']:
    ids = out[side].index
    tg = {'M': P.tag_model(side)}
    for n in INDEP[side]: tg[n] = DEFS[n][0](side)
    def run(counts):
        r = {}
        for nm, (idx, pct) in tg.items():
            K = (2.0 if side == 'bat' else 0.0) if nm == 'M' else 0.0
            i2, p2, mid = sub(idx, pct, counts); t = score(i2, p2, side, K=K, mid=mid).reindex(ids)
            r[nm] = t.SCORE.where(t.balls.fillna(0) >= THIN // 2)
        return pd.DataFrame(r)
    acc = {n: [] for n in INDEP[side]}
    for _ in range(NS):
        half = (rng.random(len(mids)) < 0.5).astype(int); A = run(half); Bh = run(1 - half)
        for n in INDEP[side]:
            for X, Y in [(A, Bh), (Bh, A)]:
                ok = X['M'].notna() & Y[n].notna()
                if ok.sum() > 8: acc[n].append(X['M'][ok].corr(Y[n][ok]))
    rr = rel[rel.side == side].set_index('defn').split_half_r
    for n in INDEP[side]:
        c = np.mean(acc[n]); ceil = np.sqrt(rr['M'] * rr[n])
        rows.append(dict(side=side, defn=n, cross_half_r=c, ceiling=ceil, disattenuated=c / ceil))
R = pd.DataFrame(rows); print(R.round(3).to_string(index=False)); R.to_csv('work/PUB_crosshalf.csv', index=False)
