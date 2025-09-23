from flask import Flask, jsonify
import os, sqlite3, datetime as dt
app=Flask(__name__)
@app.get("/")
def home(): return "Jarvis Dashboard OK"
@app.get("/metrics")
def metrics():
    DB=os.getenv("SQLITE_DB_PATH","jarvis_qai_pro.db")
    con=sqlite3.connect(DB); c=con.cursor()
    today=dt.date.today().isoformat()
    c.execute("SELECT COALESCE(SUM(profit),0), COUNT(*) FROM trade_log WHERE date=?", (today,))
    s=c.fetchone() or (0.0,0); tr=float(s[0] or 0.0); n=int(s[1] or 0)
    c.execute("SELECT COUNT(*) FROM trade_log WHERE date=? AND profit>0", (today,)); wins=int((c.fetchone() or (0,))[0])
    wr=wins/max(1,n); con.close()
    out=[f"jarvis_today_realized {tr}", f"jarvis_today_trades {n}", f"jarvis_today_winrate {wr}"]
    return app.response_class("\n".join(out)+"\n", mimetype="text/plain; version=0.0.4")
@app.get("/ab")
def ab():
    DB=os.getenv("SQLITE_DB_PATH","jarvis_qai_pro.db")
    con=sqlite3.connect(DB); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS policy_experiments (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INT, symbol TEXT, policy TEXT, realized REAL)")
    c.execute("SELECT policy, COUNT(*), SUM(CASE WHEN realized>0 THEN 1 ELSE 0 END)*1.0/COUNT(*), AVG(realized), SUM(realized) FROM policy_experiments GROUP BY policy ORDER BY SUM(realized) DESC")
    rows=c.fetchall(); con.close()
    data=[{"policy":r[0], "n":r[1], "winrate":r[2], "avg£":r[3], "pnl£":r[4]} for r in rows]
    return jsonify(data)
if __name__=="__main__":
    app.run(host=os.getenv("DASHBOARD_HOST","0.0.0.0"), port=int(os.getenv("DASHBOARD_PORT","5000")))
