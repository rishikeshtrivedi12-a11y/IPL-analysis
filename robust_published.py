"""Split-half reliability, disattenuated agreement, and match-clustered bootstrap of the consensus."""
import sys, numpy as np, pandas as pd, time
sys.path.insert(0,'pipeline')
import published as P
from published import d, DEFS, THIN, score
B=int(sys.argv[1]) if len(sys.argv)>1 else 60; NSPLIT=10
rng=np.random.default_rng(2026)
INDEP={'bat':['LEV30','RRR10','CLOSE','DEATH'],'bowl':['LEV30','CLOSE','DEATH']}
out=pd.read_pickle('work/pub_out.pkl')
tags={}   # fixed tagged sets (full sample); resampling happens over matches
for side in ['bat','bowl']:
    tags[side]={'M':P.tag_model(side)}
    for n in INDEP[side]: tags[side][n]=DEFS[n][0](side)
mids=np.sort(d.match_id.unique()); mpos={m:i for i,m in enumerate(mids)}
def sub(idx,pct,counts):
    m=d.match_id.loc[idx].values; inv=np.array([mpos[x] for x in m]) if False else np.searchsorted(mids,m)
    rep=counts[inv]; keep=rep>0
    idx2=np.repeat(idx,rep); st=np.cumsum(rep)-rep
    cp=np.arange(rep.sum())-np.repeat(st,rep)
    mid=np.repeat(m,rep)*100+cp
    p2=None if pct is None else np.repeat(pct,rep)
    return idx2,p2,mid
def run(side,counts,ids,thin):
    res={}
    for nm,(idx,pct) in tags[side].items():
        K=(2.0 if side=='bat' else 0.0) if nm=='M' else 0.0
        i2,p2,mid=sub(idx,pct,counts)
        t=score(i2,p2,side,K=K,mid=mid).reindex(ids)
        sc=t.SCORE.where(t.balls.fillna(0)>=thin)
        res[nm]=sc
    return pd.DataFrame(res)
def cons(R,side):
    pr=pd.DataFrame({n:(R[n].rank(ascending=False,method='min')-1)/(R[n].notna().sum()-1) for n in INDEP[side]})
    return pr.mean(axis=1).where(pr.notna().sum(axis=1)>=2)
rows=[]
for side in ['bat','bowl']:
    ids=out[side].index; ones=np.ones(len(mids),dtype=int)
    # ---------- split-half reliability ----------
    rels={n:[] for n in tags[side]}; relc=[]
    for r in range(NSPLIT):
        half=rng.random(len(mids))<0.5
        A=run(side,half.astype(int),ids,THIN//2); Bh=run(side,(~half).astype(int),ids,THIN//2)
        for n in tags[side]:
            ok=A[n].notna()&Bh[n].notna()
            if ok.sum()>8: rels[n].append(A[n][ok].corr(Bh[n][ok]))
        ca,cb=cons(A,side),cons(Bh,side); ok=ca.notna()&cb.notna(); relc.append(ca[ok].corr(cb[ok]))
    for n in tags[side]:
        r=np.mean(rels[n]); rows.append(dict(side=side,defn=n,split_half_r=r,spearman_brown=2*r/(1+r)))
    r=np.mean(relc); rows.append(dict(side=side,defn='CONSENSUS',split_half_r=r,spearman_brown=2*r/(1+r)))
    print(f'[{side}] split-half done',flush=True)
rel=pd.DataFrame(rows); print(rel.round(3).to_string(index=False)); rel.to_csv('work/PUB_reliability.csv',index=False)
# ---------- bootstrap ----------
boot={}
for side in ['bat','bowl']:
    ids=out[side].index; t0=time.time(); topM=np.zeros(len(ids)); topC=np.zeros(len(ids)); rkC=[]; rkM=[]
    for bi in range(B):
        counts=np.bincount(rng.integers(0,len(mids),len(mids)),minlength=len(mids))
        R=run(side,counts,ids,THIN)
        m=R['M'].rank(ascending=False,method='min'); c=cons(R,side).rank(method='min')
        topM+=(m<=10).values; topC+=(c<=10).values; rkM.append(m.values); rkC.append(c.values)
        if bi%10==0: print(f'[{side}] boot {bi}/{B} {time.time()-t0:.0f}s',flush=True)
    rkM=np.array(rkM); rkC=np.array(rkC)
    D=pd.DataFrame({'name':out[side].name,'locked_rk':out[side].locked_rk,'P_top10_model':topM/B,'P_top10_consensus':topC/B,
                    'model_rk_p05':np.nanpercentile(rkM,5,axis=0),'model_rk_p95':np.nanpercentile(rkM,95,axis=0),
                    'cons_rk_p05':np.nanpercentile(rkC,5,axis=0),'cons_rk_p95':np.nanpercentile(rkC,95,axis=0)},index=ids)
    boot[side]=D; D.to_csv(f'work/PUB_boot_{side}.csv')
pd.to_pickle(boot,'work/pub_boot.pkl'); print('DONE')
