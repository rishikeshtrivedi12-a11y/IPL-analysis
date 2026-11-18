"""Test the locked rankings against published / standard definitions of pressure.

Same value metric everywhere (runs vs par per 100 balls, player + (match,innings,phase)
fixed effects, 0.65 season decay, shrinkage balls/(balls+150), downside-sd penalty).
Only the rule that decides WHICH balls count as pressure changes.

Pre-registered before looking at results:
  - every definition keeps the live-ball gate (win prob 0.05-0.95), as in the model
  - a player needs >= THIN tagged balls under a definition to be ranked under it
  - flat weights (K=0) for every alternative definition
Run from the project root:  python3 -I pipeline/published.py
"""
import sys, numpy as np, pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
THIN = 100; DECAY = 0.65; MINSEAS = 40
KEYS = ['match_id', 'innings', 'ph']

d = pd.read_parquet('work/fixed_pi.parquet')
Eg = np.load('work/Eg.npy'); e, b, k = d.era.values, d.b.values, d.k.values
M = 100.0
LW = {1:1.30,2:1.35,3:1.40,4:1.45,5:1.38,6:1.18,7:0.98,8:0.79,9:0.59,10:0.39,11:0.19}
MEANW = np.mean([LW[i] for i in range(1, 12)])
NOTB = ['Retire Out', 'Obstracting the field', 'Obstructing the field']
d['pos'] = d.batting_order.fillna(11).clip(1, 11).astype(int)
raw = np.where(d.dismissal_type.isin(NOTB), 0.0, np.where(d.dismissal_type == 'RunOut', 0.25, d.is_wicket.astype(float)))
d['bw_big'] = raw * (d.pos.map(LW) / MEANW)
d['rq2'] = np.where(d.innings == 2, d.rq, 0); d['wv'] = Eg[e, b, k] - Eg[e, b, np.maximum(k - 1, 0)]
d['faced'] = d.groupby(['match_id', 'innings', 'striker_id']).cumcount()
d['sbucket'] = np.select([d.faced <= 5, d.faced <= 15], [0, 1], 2)
C = ['era', 'innings', 'ph', 'wq', 'rq2']; F = C + ['dbucket', 'sbucket']
def par(col, pid):
    f = d.groupby(F)[col]; c = d.groupby(C)[col]; fp = d.groupby(F + [pid])[col]; cp = d.groupby(C + [pid])[col]
    pa = (c.transform('sum') - cp.transform('sum')) / np.maximum(c.transform('size') - cp.transform('size'), 1)
    return (f.transform('sum') - fp.transform('sum') + M * pa) / (np.maximum(f.transform('size') - fp.transform('size'), 0) + M)
d['xw_big'] = par('bw_big', 'bowler_id')
d['rv_big'] = (d.x_conc - d.conceded) + d.wv * (d.bw_big - d.xw_big)

# extra quantities for the published definitions
pt = Eg[e, 120, 10]
d['ru'] = 100 * (1 - Eg[e, b, k] / pt)                                   # % resources used
d['rrr'] = np.where(d.innings == 2, d.runs_req / np.maximum(d.b, 1) * 6, np.nan)
d['yr'] = d.season.str[:4].astype(int)
live = d.live.values

SIDE = {'bowl': dict(rvc='rv_big', pid='bowler_id', nm='bowler_name', bl='bl_bowl_FIX', dot='dot_bowl', wpa='wpa_bowl'),
        'bat':  dict(rvc='rv_bat', pid='striker_id', nm='striker_name', bl='bl_bat_FIX',  dot='dot_bat',  wpa='wpa_bat')}

def cell_top(vals, idx, pct=0.70):
    """within (match,innings,phase) percentile rank of vals over rows idx; return rows with pct>=cut and their pct"""
    s = pd.Series(vals, index=idx)
    r = s.groupby([d.loc[idx, c].values for c in KEYS]).rank(pct=True)
    keep = r >= pct
    return r.index[keep.values].values, r[keep].values

# ---------------- definitions: each returns the tagged ball index (and optional pct) ----------------
def tag_model(side):
    s = SIDE[side]; idx = d.index[live].values
    pb = pd.Series(d.loc[idx, s['bl']].values, index=idx).groupby([d.loc[idx, c].values for c in KEYS]).rank(pct=True)
    pdo = pd.Series(d.loc[idx, s['dot']].values, index=idx).groupby([d.loc[idx, c].values for c in KEYS]).rank(pct=True)
    return cell_top((0.5 * pb + 0.5 * pdo).values, idx)
def tag_bl(side):   idx = d.index[live].values; return cell_top(d.loc[idx, SIDE[side]['bl']].values, idx)
def tag_blch(side): idx = d.index[live & (d.innings == 2).values].values; return cell_top(d.loc[idx, SIDE[side]['bl']].values, idx)
def tag_dot(side):  idx = d.index[live].values; return cell_top(d.loc[idx, SIDE[side]['dot']].values, idx)
def tag_lem(side):
    if side == 'bowl': return None
    idx = d.index[live & (d.innings == 2).values].values
    return cell_top((d.loc[idx, 'rrr'] * d.loc[idx, 'ru']).values, idx)
def tag_lev(side):
    thr = np.quantile(d.li.values[live], 0.70); return d.index[live & (d.li.values >= thr)].values, None
def tag_rrr(side):
    if side == 'bowl': return None
    return d.index[live & (d.innings == 2).values & (d.rrr.values >= 10)].values, None
def tag_close(side): return d.index[live & d.wp.between(0.25, 0.75).values].values, None
def tag_death(side): return d.index[live & (d.ph.values >= 4)].values, None

DEFS = {   # name: (function, group)
    'LEV30':  (tag_lev,   'indep'),   # leverage top 30%  (WPA tradition)
    'RRR10':  (tag_rrr,   'indep'),   # chases, required rate >= 10 (batters only)
    'CLOSE':  (tag_close, 'indep'),   # win prob 0.25-0.75
    'DEATH':  (tag_death, 'indep'),   # overs 16-20
    'BL':     (tag_bl,    'blfam'),   # BL index only
    'BLCH':   (tag_blch,  'blfam'),   # BL index, chases only
    'DOT':    (tag_dot,   'blfam'),   # dot squeeze only
    'LEMPR':  (tag_lem,   'blfam'),   # Lemmer product RRR x resources used, chases (adaptation; batters only)
}

# ---------------- the value metric, identical to pweight.py / bigwkt.py ----------------
def score(idx, pct, side, K=0.0, mid=None):
    s = SIDE[side]; pid = s['pid']
    h = d.loc[idx].copy()
    if mid is not None: h['match_id'] = mid          # bootstrap copies get their own innings cells
    h['w'] = 1.0 if (pct is None or K == 0) else 1.0 + K * (pct - 0.70) / 0.30
    h['iid'] = h.groupby(KEYS).ngroup()
    w = h.w.values; y = h[s['rvc']].values - np.average(h[s['rvc']].values, weights=w)
    ic, ii = np.unique(h.iid.values, return_inverse=True); pc, pi = np.unique(h[pid].values, return_inverse=True)
    sw_p = np.bincount(pi, weights=w); sw_i = np.bincount(ii, weights=w)
    g = np.zeros(len(ic))
    for _ in range(80):
        a = np.bincount(pi, weights=w * (y - g[ii])) / (sw_p + 150.0)
        g = np.bincount(ii, weights=w * (y - a[pi])) / (sw_i + 20.0)
    h['adj'] = y - g[ii]; h['aw'] = h.adj * h.w
    gg = h.groupby([pid, 'yr'])
    sp = pd.DataFrame({'rate': 100 * gg.aw.sum() / gg.w.sum(), 'balls': gg.size()})
    sp['wt'] = (DECAY ** (2026 - sp.index.get_level_values('yr'))) * sp.balls
    G = sp.groupby(level=0)
    o = pd.DataFrame({'wmean': G.apply(lambda s_: (s_.rate * s_.wt).sum() / s_.wt.sum(), include_groups=False)})
    def dsd(s_):
        s_ = s_[s_.balls >= MINSEAS]
        if len(s_) < 3: return np.nan
        m = (s_.rate * s_.wt).sum() / s_.wt.sum(); er = (s_.rate - m).clip(upper=0)
        return np.sqrt((s_.wt * er ** 2).sum() / s_.wt.sum())
    o['dsd'] = G.apply(dsd, include_groups=False)
    base = h.groupby(pid).agg(name=(s['nm'], 'first'), balls=('adj', 'size'))
    base['inns'] = h.groupby([pid, 'match_id']).size().groupby(level=0).size()
    t = base.join(o); t['dsd'] = t.dsd.fillna(t.dsd.median())
    t['SCORE'] = (t.wmean - 0.50 * t.dsd) * (t.balls / (t.balls + 150.0))
    return t

def wpa100(idx, side):
    h = d.loc[idx]; s = SIDE[side]
    g = h.groupby(s['pid'])[s['wpa']]
    return pd.DataFrame({'wpa100': 100 * g.mean(), 'wpa_n': g.size()})

if __name__ == '__main__':
    pool = {'bat': pd.read_csv('work/PW_bat.csv'), 'bowl': pd.read_csv('work/BIGWKT_bowl.csv')}
    pidcol = {'bat': 'striker_id', 'bowl': 'bowler_id'}
    out = {}
    for side in ['bat', 'bowl']:
        P = pool[side].set_index(pidcol[side]); ids = P.index
        res = pd.DataFrame(index=ids); res['name'] = P.name; res['locked_rk'] = P.rk
        # ---- fidelity check: reproduce the locked scores exactly
        idx, pct = tag_model(side); K = 2.0 if side == 'bat' else 0.0
        t = score(idx, pct, side, K=K)
        chk = (t.reindex(ids).SCORE - P.SCORE).abs().max()
        print(f'[{side}] reproduces locked SCORE: max abs diff {chk:.2e} over {len(ids)} players')
        assert chk < 1e-6, 'scoring function does not reproduce the locked list'
        # model at K=0 for like-for-like with the flat-weight alternatives
        t0 = score(idx, pct, side, K=0.0); res['M0_score'] = t0.reindex(ids).SCORE; res['M0_balls'] = t0.reindex(ids).balls
        res['M0_rk'] = res.M0_score.rank(ascending=False, method='min')
        for nm, (fn, grp) in DEFS.items():
            r = fn(side)
            if r is None: continue
            idx, pct = r
            t = score(idx, None, side)
            res[f'{nm}_score'] = t.reindex(ids).SCORE; res[f'{nm}_balls'] = t.reindex(ids).balls.fillna(0).astype(int)
            ok = res[f'{nm}_balls'] >= THIN
            res[f'{nm}_rk'] = res[f'{nm}_score'].where(ok).rank(ascending=False, method='min')
            print(f'  [{side}] {nm:6s} tagged balls {len(idx):>7,} | players ranked {int(ok.sum())}/{len(ids)}')
        # model-free-ish checks (value metric swapped for de-drifted WPA per 100 balls)
        w_all = wpa100(d.index[live].values, side).reindex(ids)
        res['WPA_live'] = w_all.wpa100; res['WPA_live_n'] = w_all.wpa_n
        thr = np.quantile(d.li.values[live], 0.70)
        w_lev = wpa100(d.index[live & (d.li.values >= thr)].values, side).reindex(ids)
        res['WPA_lev'] = w_lev.wpa100; res['WPA_lev_n'] = w_lev.wpa_n
        res['WPA_live_rk'] = res.WPA_live.rank(ascending=False, method='min')
        res['WPA_lev_rk'] = res.WPA_lev.where(res.WPA_lev_n >= THIN).rank(ascending=False, method='min')
        out[side] = res
        res.to_csv(f'work/PUB_{side}.csv')
    pd.to_pickle(out, 'work/pub_out.pkl')
    print('\nwritten work/PUB_bat.csv, work/PUB_bowl.csv, work/pub_out.pkl')
