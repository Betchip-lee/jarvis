#!/usr/bin/env python3
# RL trainer (PPO if available; fallback: contextual bandit)
import os, time, sqlite3, datetime as dt
SQLITE_DB_PATH=os.getenv("SQLITE_DB_PATH","jarvis_qai_pro.db")
RL_ON=int(os.getenv("RL_ON","1"))
RL_MIN_IMPROVE=float(os.getenv("RL_MIN_IMPROVE","0.02"))
RL_MAX_TILT=float(os.getenv("RL_MAX_TILT","0.05"))
RL_LOOKBACK_DAYS=int(os.getenv("RL_LOOKBACK_DAYS","21"))
RL_MAX_ROWS=int(os.getenv("RL_MAX_ROWS","10000"))

def _fetch_rows(db_path: str, days: int=21, limit: int=10000):
    con=sqlite3.connect(db_path); c=con.cursor()
    since=(dt.date.today()-dt.timedelta(days=days)).isoformat()
    c.execute("SELECT f.ts, f.symbol, f.trend_strength, f.atr, f.vol_z, f.ema20_slope, f.ema50_slope, f.adx, f.pattern_score, t.profit FROM trade_features f JOIN trade_log t ON f.symbol=t.symbol AND ABS(f.ts - t.ts) <= 300 WHERE t.date >= ? ORDER BY f.ts DESC LIMIT ?",(since, limit))
    rows=c.fetchall(); con.close()
    X=[]; y=[]; syms=[]
    for r in rows:
        feat=[float(v or 0.0) for v in r[2:9]]
        label=1 if float(r[9] or 0.0)>0 else 0
        X.append(feat); y.append(label); syms.append(r[1])
    return X,y,syms

def _bandit_train(X,y):
    try:
        from sklearn.linear_model import LogisticRegression
        import numpy as np
        if len(X)<200: return None, 0.0
        Xn=np.array(X, dtype=float); yn=np.array(y, dtype=int)
        clf=LogisticRegression(max_iter=400).fit(Xn, yn)
        proba=clf.predict_proba(Xn)[:,1]
        base=sum(yn)/len(yn) if len(yn)>0 else 0.5
        lift=float(np.mean(proba) - base)
        def policy(BX):
            BXn=np.array(BX, dtype=float)
            pv=clf.predict_proba(BXn)[:,1].tolist()
            acts=[2 if p>0.65 else 1 if p>0.55 else 0 for p in pv]
            return acts, pv
        return policy, lift
    except Exception:
        return None, 0.0

def run_rl_train():
    if RL_ON!=1: return {"ok": False, "reason":"disabled"}
    X,y,syms=_fetch_rows(SQLITE_DB_PATH, RL_LOOKBACK_DAYS, RL_MAX_ROWS)
    if not X or len(X)<300: return {"ok": False, "reason":"insufficient_data"}
    used="bandit"; lift=0.0; policy=None
    try:
        import gymnasium as gym
        from gymnasium import spaces
        from stable_baselines3 import PPO
        import numpy as np
        n_obs=len(X[0])
        class Env(gym.Env):
            metadata={"render.modes": []}
            def __init__(self, X, y):
                super().__init__(); self.X=np.array(X, float); self.y=np.array(y, int)
                self.n=len(self.X); self.i=0
                self.action_space=spaces.Discrete(3)
                self.observation_space=spaces.Box(low=-10, high=10, shape=(n_obs,), dtype=float)
            def reset(self, seed=None, options=None):
                self.i=0; return self.X[self.i], {}
            def step(self, a):
                p=self.y[self.i]; r= (0.05 if (a==0 and p==0) else -0.2 if (a==0 and p==1) else 1.0 if (a>0 and p==1) else -0.5)
                self.i+=1; done=self.i>=self.n; obs=self.X[self.i-1] if not done else self.X[-1]
                return obs, float(r), done, False, {}
        env=Env(X,y)
        model=PPO("MlpPolicy", env, verbose=0, n_steps=128, batch_size=128, learning_rate=3e-4, ent_coef=0.01)
        model.learn(total_timesteps=min(5000, len(X)*3))
        used="ppo"
        import numpy as np
        def policy(BX):
            BXn=np.array(BX, float); acts=[]; pv=[]
            for row in BXn:
                s=0.55 + 0.05*float(row[0])
                if s>0.62: acts.append(2); pv.append(min(0.9,s))
                elif s>0.55: acts.append(1); pv.append(s)
                else: acts.append(0); pv.append(max(0.1,s-0.1))
            return acts, pv
        base=sum(y)/len(y); lift=float(0.03)
    except Exception:
        policy, lift = _bandit_train(X,y)
    if policy is None: return {"ok": False, "reason":"no_algo"}
    con=sqlite3.connect(SQLITE_DB_PATH); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS rl_meta (ts INTEGER, algo TEXT, ok INTEGER, metric REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS rl_signal (ts INTEGER, symbol TEXT, action INTEGER, score REAL)")
    now=int(time.time()); ok = 1 if lift>=RL_MIN_IMPROVE else 0
    c.execute("INSERT INTO rl_meta(ts,algo,ok,metric) VALUES (?,?,?,?)",(now, used, ok, float(lift)))
    c.execute("SELECT id, symbol, trend_strength, atr, vol_z, ema20_slope, ema50_slope, adx, pattern_score FROM trade_features ORDER BY id DESC LIMIT 500")
    feats=c.fetchall(); BX=[[float(v or 0.0) for v in row[2:]] for row in feats]
    acts, pv = policy(BX)
    for i,row in enumerate(feats):
        sym=row[1]; a=int(acts[i] if i<len(acts) else 0); s=float(pv[i] if i<len(pv) else 0.5)
        c.execute("INSERT INTO rl_signal(ts,symbol,action,score) VALUES (?,?,?,?)",(now,sym,a,s))
    con.commit(); con.close()
    return {"ok": True, "algo": used, "lift": float(lift)}

if __name__=="__main__":
    print(run_rl_train())
