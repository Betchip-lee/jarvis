#!/usr/bin/env python3
import os, duckdb, pandas as pd
SQLITE_DB_PATH=os.getenv("SQLITE_DB_PATH","jarvis_qai_pro.db"); OUT="analytics_out"
def run():
    import pathlib; pathlib.Path(OUT).mkdir(exist_ok=True)
    con=duckdb.connect()
    con.execute(f"ATTACH DATABASE '{SQLITE_DB_PATH}' AS jarvis (TYPE SQLITE)")
    df=con.execute("SELECT date, SUM(profit) pnl, COUNT(*) n FROM jarvis.trade_log GROUP BY date ORDER BY date DESC LIMIT 60").fetchdf()
    df.to_csv(f"{OUT}/pnl_by_day.csv", index=False)
    df2=con.execute("SELECT symbol, COUNT(*) n, AVG(profit) avgp, SUM(profit) pnl FROM jarvis.trade_log GROUP BY symbol ORDER BY pnl DESC LIMIT 50").fetchdf()
    df2.to_csv(f"{OUT}/pnl_by_symbol.csv", index=False)
    print("Analytics written to", OUT)
if __name__=="__main__": run()
