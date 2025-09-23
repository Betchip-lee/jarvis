#!/usr/bin/env python3
import os, time, sqlite3, shutil, datetime as dt
from pathlib import Path
try:
    from prefect import flow, task
    HAS_PREFECT=True
except Exception:
    HAS_PREFECT=False
SQLITE_DB_PATH=os.getenv("SQLITE_DB_PATH","jarvis_qai_pro.db")
@task
def quantum_task():
    try:
        import quantum_expts as qx; return qx.run_quantum_expts()
    except Exception as e:
        return {"ok": False, "err": str(e)}
@task
def sqlite_backup():
    Path("backups").mkdir(exist_ok=True)
    tag=dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S"); dst=f"backups/jarvis_{tag}.db"
    shutil.copy2(SQLITE_DB_PATH, dst) if Path(SQLITE_DB_PATH).exists() else open(dst,"wb").close()
    return {"ok": True, "dst": dst}
@flow(name="Jarvis Nightly")
def nightly():
    r1=quantum_task.submit(); r2=sqlite_backup.submit()
    return {"quantum": r1.result(), "backup": r2.result()}
@flow(name="Jarvis Hourly")
def hourly(): return {"ts": int(time.time()), "ok": True}
if __name__=="__main__":
    print("Prefect installed?", HAS_PREFECT)
    if HAS_PREFECT: print(nightly())
