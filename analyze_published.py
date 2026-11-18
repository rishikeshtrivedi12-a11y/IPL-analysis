import sys, numpy as np, pandas as pd
sys.path.insert(0, 'pipeline')
import published as P
from published import DEFS, THIN, d, live, score, SIDE
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
out = pd.read_pickle('work/pub_out.pkl')
INDEP = ['LEV30', 'RRR10', 'CLOSE', 'DEATH']; BLFAM = ['BL', 'BLCH', 'DOT', 'LEMPR']

def avail(res, names): return [n for n in names if f'{n}_rk' in res.columns]
def pctrank(res, n):
    """percentile rank 0 (best) .. 1 (worst) among players ranked under definition n"""
    r = res[f'{n}_rk']; m = r.notna().sum()
    return (r - 1) / (m - 1)

summary = {}
for side, lbl in [('bat', 'BATTERS'), ('bowl', 'BOWLERS')]:
    res = out[side].copy(); top10 = set(res.index[res.locked_rk <= 10])
    print('\n' + '=' * 110); print(f'{lbl}  (pool {len(res)}, rank = within pool, thin < {THIN} tagged balls not ranked)'); print('=' * 110)
    rows = []
    for n in ['M0'] + avail(res, INDEP) + avail(res, BLFAM):
        r = res[f'{n}_rk']; ok = r.notna()
        sp = res.locked_rk[ok].corr(r[ok], method='spearman')
        t10 = set(r.index[(r <= 10) & ok]); ov = len(t10 & top10)
        grp = 'model(K=0)' if n == 'M0' else ('indep' if n in INDEP else 'BL-family')
        rows.append(dict(defn=n, group=grp, n_ranked=int(ok.sum()), spearman_vs_locked=sp, top10_overlap=ov,
                         tagged_balls_locked_top10_median=int(res.loc[list(top10), f'{n}_balls'].median()) if n != 'M0' else np.nan))
    for n, col in [('WPA_live', 'WPA_live_rk'), ('WPA_lev', 'WPA_lev_rk')]:
        r = res[col]; ok = r.notna(); t10 = set(r.index[(r <= 10) & ok])
        rows.append(dict(defn=n, group='WPA check', n_ranked=int(ok.sum()), spearman_vs_locked=res.locked_rk[ok].corr(r[ok], method='spearman'),
                         top10_overlap=len(t10 & top10), tagged_balls_locked_top10_median=np.nan))
    T = pd.DataFrame(rows); print(T.round(3).to_string(index=False)); summary[side + '_table'] = T

    # --- consensus
    def consensus(names, extra=()):
        cols = [pctrank(res, n) for n in names]
        raws = [res[f'{n}_rk'] for n in names]
        for col in extra:
            r = res[col]; m = r.notna().sum(); cols.append((r - 1) / (m - 1)); raws.append(r)
        A = pd.concat(cols, axis=1); R = pd.concat(raws, axis=1)
        return pd.DataFrame({'mean_pct': A.mean(axis=1), 'ndef': A.notna().sum(axis=1),
                             'top5': (R <= 5).sum(axis=1), 'top10': (R <= 10).sum(axis=1)})
    ind = avail(res, INDEP)
    C = consensus(ind); C.insert(0, 'name', res.name); C.insert(1, 'locked_rk', res.locked_rk)
    C2 = consensus(ind + avail(res, BLFAM)); C3 = consensus(ind, extra=['WPA_live_rk', 'WPA_lev_rk'])
    C['mean_pct_allBL'] = C2.mean_pct; C['top10_allBL'] = C2.top10; C['ndef_allBL'] = C2.ndef
    C['mean_pct_wpa'] = C3.mean_pct; C['top10_wpa'] = C3.top10
    C = C[C.ndef >= 2].sort_values('mean_pct')
    C['cons_rk'] = range(1, len(C) + 1)
    print(f'\nCONSENSUS over independent definitions {ind} (mean percentile, 0 = best)')
    print(C.head(15).round(3).to_string())
    print(f'\n  locked top 10 -> where the independent consensus puts them:')
    print(C[C.locked_rk <= 10][['name', 'locked_rk', 'cons_rk', 'mean_pct', 'top10', 'ndef']].sort_values('locked_rk').round(3).to_string(index=False))
    summary[side + '_cons'] = C
    # --- exposure: does consensus track how many pressure balls a player has?
    ex = pd.DataFrame({'cons': C.mean_pct}).join(res[[f'{n}_balls' for n in ind]].sum(axis=1).rename('indep_balls')).join(res.M0_balls.rename('model_balls'))
    print(f"\n  exposure check: spearman(consensus rank, tagged balls under independent defs) = {ex.cons.corr(ex.indep_balls, method='spearman'):+.3f}"
          f" | vs model tagged balls = {ex.cons.corr(ex.model_balls, method='spearman'):+.3f}   (negative = more balls, better rank)")
    print(f"  same for the locked rank: spearman(locked rank, model tagged balls) = {res.locked_rk.corr(res.M0_balls, method='spearman'):+.3f}")

# --- overlap of the ball sets themselves (are the 'independent' definitions actually independent?)
print('\n' + '=' * 110); print('JACCARD OVERLAP OF TAGGED BALL SETS (batter-side tags)'); print('=' * 110)
sets = {}
for n, (fn, g) in DEFS.items():
    r = fn('bat')
    if r is not None: sets[n] = set(r[0])
sets['MODEL'] = set(P.tag_model('bat')[0])
names = list(sets)
J = pd.DataFrame({a: {b_: len(sets[a] & sets[b_]) / len(sets[a] | sets[b_]) for b_ in names} for a in names})
print(J.round(2).to_string())
pd.to_pickle(summary, 'work/pub_summary.pkl')

# --- overall table: every definition (independent + BL family), role-percentile, plus bootstrap columns
# (needs work/pub_boot.pkl from robust_published.py)
import os
if os.path.exists('work/pub_boot.pkl'):
    boot = pd.read_pickle('work/pub_boot.pkl')
    IND = {'bat': ['LEV30', 'RRR10', 'CLOSE', 'DEATH'], 'bowl': ['LEV30', 'CLOSE', 'DEATH']}; FAM = ['BL', 'BLCH', 'DOT', 'LEMPR']
    rows = []
    for side in ['bat', 'bowl']:
        r = out[side]; cols = [c for c in IND[side] + FAM if f'{c}_rk' in r.columns]
        Pc = pd.DataFrame({c: (r[f'{c}_rk'] - 1) / (r[f'{c}_rk'].notna().sum() - 1) for c in cols})
        R = pd.DataFrame({c: r[f'{c}_rk'] for c in cols})
        df = pd.DataFrame({'name': r.name, 'side': side, 'locked_rk': r.locked_rk, 'n_defs': R.notna().sum(axis=1),
                           'top10_frac': (R <= 10).sum(axis=1) / R.notna().sum(axis=1), 'worst_rk': R.max(axis=1),
                           'pct_all': Pc.mean(axis=1), 'pct_indep': Pc[IND[side]].mean(axis=1)})
        df['P_top10_model'] = boot[side].P_top10_model; df['P_top10_cons'] = boot[side].P_top10_consensus; df['pool'] = len(r)
        rows.append(df)
    ALL = pd.concat(rows).sort_values('pct_all'); ALL.to_csv('work/PUB_overall.csv')
    print('\nwritten work/PUB_overall.csv')
