#!/usr/bin/env python3
import os, time, requests, sqlite3, datetime as dt
BOT=os.getenv("TELEGRAM_BOT_TOKEN",""); CHAT=os.getenv("TELEGRAM_CHAT_ID","")
def send(msg):
    if not BOT or not CHAT: return
    try: requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={'chat_id':CHAT,'text':msg}, timeout=5)
    except Exception: pass
def poll():
    if not BOT: return
    offset=None
    while True:
        try:
            r=requests.get(f"https://api.telegram.org/bot{BOT}/getUpdates", params={"timeout":30,"offset":offset}, timeout=35).json()
            for upd in r.get("result",[]):
                offset=upd["update_id"]+1
                txt=(upd.get("message",{}).get("text") or "").strip().lower()
                if txt.startswith("/status"):
                    DB=os.getenv("SQLITE_DB_PATH","jarvis_qai_pro.db"); con=sqlite3.connect(DB); c=con.cursor()
                    today=dt.date.today().isoformat()
                    c.execute("SELECT COALESCE(SUM(profit),0), COUNT(*) FROM trade_log WHERE date=?", (today,))
                    s=c.fetchone() or (0.0,0); tr=float(s[0] or 0.0); n=int(s[1] or 0)
                    c.execute("SELECT COUNT(*) FROM trade_log WHERE date=? AND profit>0", (today,)); wins=int((c.fetchone() or (0,))[0])
                    wr=wins/max(1,n); con.close(); send(f"Status: P/L £{tr:.2f} | trades {n} | wr {wr:.2%}")
                elif txt.startswith("/killswitch"):
                    os.environ["AUTO_TRADING"]="false"; send("Killswitch engaged")
                elif txt.startswith("/target"):
                    parts=txt.split(); 
                    if len(parts)>=2: os.environ["DAILY_TARGET_PROFIT"]=parts[1]; send(f"Target £{parts[1]} set")
                elif txt.startswith("/mode"):
                    parts=txt.split(); 
                    if len(parts)>=2: os.environ["MAX_ENTRIES_PER_HOUR"]="30" if parts[1]=="sniper" else "60"; send(f"Mode {parts[1]}")
                elif txt.startswith("/profile"):
                    parts=txt.split(); 
                    if len(parts)>=2: 
                        if parts[1]=="weekend": os.environ["WEEKEND_PROFILE_ON"]="1"; send("Profile: WEEKEND")
                        elif parts[1]=="weekday": os.environ["WEEKEND_PROFILE_ON"]="0"; send("Profile: WEEKDAY")
                else:
                    send("Commands: /status /killswitch /target <£> /mode sniper|normal /profile weekend|weekday")
        except Exception: time.sleep(2)
if __name__=="__main__": send("Telegram bot online."); poll()
