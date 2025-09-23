#!/usr/bin/env python3
import os, time, sqlite3, random, datetime as dt, traceback, re, math, statistics
from collections import deque, defaultdict

# ============== ENV ==============
SQLITE_DB_PATH=os.getenv("SQLITE_DB_PATH","jarvis_qai_pro.db")
LOG_LEVEL=os.getenv("LOG_LEVEL","INFO")
AUTO_TRADING=os.getenv("AUTO_TRADING","true").lower()=="true"
AUTO_DISCOVER=1 if os.getenv("AUTO_DISCOVER","1")=="1" else 0
DISCOVERY_REFRESH_MIN=int(os.getenv("DISCOVERY_REFRESH_MIN","120"))
MT5_LOGIN=os.getenv("MT5_LOGIN","")
MT5_PASSWORD=os.getenv("MT5_PASSWORD","")
MT5_SERVER=os.getenv("MT5_SERVER","PepperstoneUK-Live")
WEEKEND_PROFILE_ON=int(os.getenv("WEEKEND_PROFILE_ON","1"))
WEEKEND_MAX_ENTRIES=int(os.getenv("WEEKEND_MAX_ENTRIES","30"))
MAX_ENTRIES_PER_HOUR=int(os.getenv("MAX_ENTRIES_PER_HOUR","60"))
DAILY_LOSS_STOP=float(os.getenv("DAILY_LOSS_STOP","0"))
WEEKEND_DAILY_LOSS=float(os.getenv("WEEKEND_DAILY_LOSS","50"))
ENABLE_GHOST=1 if os.getenv("ENABLE_GHOST","1")=="1" else 0
GHOST_RATIO=float(os.getenv("GHOST_RATIO","3.0"))  # ghost scans per 1 live attempt
CONSOLE_WIDTH=int(os.getenv("CONSOLE_WIDTH","94"))
STRICT_CRYPTO=1

# ============== Colors (terminal) ==============
try:
    from colorama import init as colorama_init, Fore, Back, Style
    colorama_init()
except Exception:
    class _D: RESET_ALL=""; BRIGHT=""; DIM=""; NORMAL=""
    class _F: YELLOW=""; GREEN=""; RED=""; CYAN=""; BLUE=""; MAGENTA=""; WHITE=""
    class _B: RED=""; GREEN=""; BLUE=""; YELLOW=""; BLACK=""; MAGENTA=""; CYAN=""
    Style=_D(); Fore=_F(); Back=_B()

def log(level, msg):
    if level=="DEBUG" and LOG_LEVEL!="DEBUG": return
    print(f"[{dt.datetime.utcnow().strftime('%H:%M:%S')}] {level} | {msg}", flush=True)

# ============== DB ==============
class DB:
    def __init__(self, path=SQLITE_DB_PATH):
        self.path=path; self.ensure()
    def ensure(self):
        con=sqlite3.connect(self.path); c=con.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS trade_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INT, date TEXT, symbol TEXT, side TEXT, volume REAL,
            profit REAL, comm REAL, swap REAL, conf REAL, mode TEXT, reason TEXT, vol_bucket TEXT,
            balance_after REAL, potential_balance REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS decisions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INT, symbol TEXT, mode TEXT, take INT, conf REAL,
            q_tilt REAL, rl_tilt REAL, vol REAL, vol_bucket TEXT, reason TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS slippage_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INT, symbol TEXT, slip REAL)""")
        con.commit(); con.close()
    def log_trade(self, **kw):
        con=sqlite3.connect(self.path); c=con.cursor()
        now=int(time.time()); date=dt.date.today().isoformat()
        c.execute("""INSERT INTO trade_log(ts,date,symbol,side,volume,profit,comm,swap,conf,mode,reason,vol_bucket,balance_after,potential_balance)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",                  (now,date,kw.get('symbol'),kw.get('side'),kw.get('volume'),kw.get('profit'),kw.get('comm',0.0),kw.get('swap',0.0),                   kw.get('conf'),kw.get('mode',"LIVE"),kw.get('reason',''),kw.get('vol_bucket','NA'),                   kw.get('balance_after'),kw.get('potential_balance')))
        con.commit(); con.close()
    def log_decision(self, **kw):
        con=sqlite3.connect(self.path); c=con.cursor()
        now=int(time.time())
        c.execute("""INSERT INTO decisions(ts,symbol,mode,take,conf,q_tilt,rl_tilt,vol,vol_bucket,reason)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",                  (now,kw.get('symbol'),kw.get('mode'),int(kw.get('take',0)),kw.get('conf'),kw.get('q_tilt'),kw.get('rl_tilt'),                   kw.get('vol'),kw.get('vol_bucket'),kw.get('reason','')))
        con.commit(); con.close()

# ============== Helpers & State ==============
def is_weekend(): return dt.datetime.utcnow().weekday()>=5
def today_sum(db: DB, col="profit"):
    con=sqlite3.connect(db.path); c=con.cursor()
    c.execute(f"SELECT COALESCE(SUM({col}),0) FROM trade_log WHERE date=?", (dt.date.today().isoformat(),))
    v=c.fetchone()[0]; con.close(); return float(v or 0.0)

ENTRY_TIMES=deque()
def allow_entry_now():
    max_e=MAX_ENTRIES_PER_HOUR
    if WEEKEND_PROFILE_ON and is_weekend(): max_e=min(MAX_ENTRIES_PER_HOUR, WEEKEND_MAX_ENTRIES)
    cutoff=time.time()-3600
    while ENTRY_TIMES and ENTRY_TIMES[0] < cutoff: ENTRY_TIMES.popleft()
    return len(ENTRY_TIMES) < (max_e if max_e>0 else 10**9)
def mark_entry_time(): ENTRY_TIMES.append(time.time())

def session_name():
    h=dt.datetime.utcnow().hour
    if 22<=h or h<6: return "SYDNEY"
    if 0<=h<9: return "TOKYO"
    if 7<=h<16: return "LONDON"
    if 12<=h<21: return "NEW_YORK"
    return "MIXED"

# ============== Discovery (strict crypto) ==============
CRYPTO_BASES=(
    "BTC","ETH","LTC","XRP","ADA","BNB","DOGE","SOL","DOT","AVAX","TRX","NEAR","SHIB","LINK","MATIC","XLM","ETC","ATOM","APT","ARB","OP","SUI"
)
import re
CRYPT_RE = re.compile(r"^(" + "|".join(CRYPTO_BASES) + r")USD(_SB)?$", re.IGNORECASE)

def discover_crypto():
    if AUTO_DISCOVER!=1: return []
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        log("WARN", f"MetaTrader5 not available: {e}")
        return []
    names=set()
    try:
        ok = mt5.initialize(login=int(MT5_LOGIN or 0), password=MT5_PASSWORD, server=MT5_SERVER) or mt5.initialize()
        if not ok:
            log("WARN","MT5 initialize() returned False; falling back to defaults")
            return []
        for grp in ("*CRYPTO*", "*Crypto*", "*Cryptocurrencies*"):
            res = mt5.symbols_get(grp)
            if res:
                for s in res:
                    nm = s.name.upper()
                    if CRYPT_RE.match(nm): names.add(nm)
        if not names:
            syms = mt5.symbols_get()
            for s in syms or []:
                nm = s.name.upper()
                if CRYPT_RE.match(nm): names.add(nm)
        out = sorted(names)
        log("INFO", f"Discovered {len(out)} STRICT crypto SB symbols: {out[:10]}{'...' if len(out)>10 else ''}")
        return out
    except Exception as e:
        log("WARN", f"MT5 discovery failed: {e}\n{traceback.format_exc()}")
        return []

# ============== Volatility & Regime ==============
def volatility_meter(series):
    if len(series)<8: return 0.0, "NA"
    mu = statistics.mean(series[-8:])
    sd = statistics.pstdev(series[-8:]) or 1e-6
    vol = abs(sd/mu) if abs(mu)>1e-6 else sd
    if vol < 0.005: bucket="CALM"
    elif vol < 0.015: bucket="NORMAL"
    elif vol < 0.040: bucket="BRISK"
    else: bucket="WILD"
    return vol, bucket

def sentiment_from_conf(conf):
    if conf>=0.65: return "BULLISH"
    if conf<=0.45: return "BEARISH"
    return "NEUTRAL"

# ============== Console Rendering ==============
try:
    from colorama import Fore, Back, Style
except Exception:
    class _D: RESET_ALL=""; BRIGHT=""; DIM=""; NORMAL=""
    class _F: YELLOW=""; GREEN=""; RED=""; CYAN=""; BLUE=""; MAGENTA=""; WHITE=""
    class _B: RED=""; GREEN=""; BLUE=""; YELLOW=""; BLACK=""; MAGENTA=""; CYAN=""
    Style=_D(); Fore=_F(); Back=_B()

def ctag(tag):
    colors={"CALM":Back.BLUE+Style.BRIGHT,"NORMAL":Back.GREEN+Style.BRIGHT,"BRISK":Back.YELLOW+Style.BRIGHT,"WILD":Back.RED+Style.BRIGHT,
            "BULLISH":Fore.GREEN+Style.BRIGHT, "BEARISH":Fore.RED+Style.BRIGHT, "NEUTRAL":Fore.CYAN+Style.DIM}
    return colors.get(tag,"")

def sep(width):
    print("="*width)

def render_panel(db: DB, balance_est, symbols, last_decisions, last_trades, width=94):
    sep(width)
    sess=session_name()
    pnl=today_sum(db,"profit")
    ghost_n=sum(1 for d in last_decisions if d["mode"]=="GHOST")
    live_n=sum(1 for d in last_decisions if d["mode"]=="LIVE")
    header=f" Jarvis OVERLORD | Bal £{balance_est:.2f} | P/L Today £{pnl:.2f} | Ghost {ghost_n} | Live {live_n} | Sess {sess} "
    print(header[:width])
    print("-"*width)
    print(" Market scan / decisions (why traded or not):")
    for d in list(last_decisions)[-8:]:
        vt = f"{d['vol_bucket']}"
        sent = sentiment_from_conf(d["conf"])
        print(f"  {d['mode']:5} | {d['symbol']:12} | conf {d['conf']:.2f} | q {d['q_tilt']:+.2f} rl {d['rl_tilt']:+.2f} | vol {d['vol']:.3f} {ctag(vt)}{vt}{Style.RESET_ALL} | {ctag(sent)}{sent}{Style.RESET_ALL} | {d['reason']}")
    print("-"*width)
    print(" Last trades (PnL & balances):")
    if last_trades:
        for t in list(last_trades)[-6:]:
            col = Fore.GREEN if t['profit']>=0 else Fore.RED
            print(f"  {t['mode']:4} | {t['symbol']:12} | {col}{t['profit']:>+6.2f}{Style.RESET_ALL} | conf {t['conf']:.2f} | bal£ {t['balance_after']:.2f} | pot£ {t['potential_balance']:.2f} | {t['vol_bucket']} | {t['reason']}")
    else:
        print("  (no trades yet)")
    print("-"*width)
    con=sqlite3.connect(db.path); c=con.cursor()
    c.execute("""SELECT symbol,
                        AVG(profit) AS avgp,
                        SUM(CASE WHEN profit>0 THEN 1 ELSE 0 END)*1.0/COUNT(*) AS wr,
                        COUNT(*) n
                 FROM trade_log
                 GROUP BY symbol HAVING n>=5
                 ORDER BY (avgp*wr) DESC
                 LIMIT 8""")
    rows=c.fetchall(); con.close()
    if rows:
        line=" | ".join([f"{r[0]}:{(r[1]*r[2]):+.2f}" for r in rows])
        print(" Top symbols (efficiency score):")
        print("  ", line[:width-4])
    else:
        print(" Top symbols (efficiency score): need >=5 trades/symbol.")
    sep(width)

# ============== Jarvis Core ==============
class Jarvis:
    def __init__(self):
        self.db=DB()
        discovered=discover_crypto()
        if not discovered:
            discovered=["BTCUSD_SB","ETHUSD_SB","LTCUSD_SB","XRPUSD_SB"]
        self.symbols=discovered
        self.balance=230.00
        self.price_noise=defaultdict(lambda: deque(maxlen=64))
        self.last_panel=0; self.last_disc=0
        self.decisions=deque(maxlen=200)
        self.trades=deque(maxlen=200)
        self.width=CONSOLE_WIDTH

    def mk_features(self, sym):
        d = (random.random()-0.5)*0.004
        self.price_noise[sym].append(d if d!=0 else 1e-6)
        vol, bucket = volatility_meter(list(self.price_noise[sym]))
        q_tilt = random.uniform(-0.03,0.03)
        rl_tilt = random.uniform(-0.05,0.05)
        conf = 0.55 + q_tilt + (rl_tilt*0.5)
        conf = max(0.05, min(0.95, conf))
        return conf, q_tilt, rl_tilt, vol, bucket

    def decide(self, sym, mode="GHOST"):
        conf, q_tilt, rl_tilt, vol, bucket = self.mk_features(sym)
        reasons=[]
        if not allow_entry_now():
            reasons.append("rate-limit"); take=False
        else:
            if bucket=="WILD" and conf<0.60:
                take=False; reasons.append("wild+lowconf")
            else:
                take = conf>=0.54; reasons.append("conf>=0.54" if take else "conf<0.54")
        reason = ",".join(reasons)
        self.db.log_decision(symbol=sym, mode=mode, take=int(take), conf=conf, q_tilt=q_tilt, rl_tilt=rl_tilt, vol=vol, vol_bucket=bucket, reason=reason)
        self.decisions.append({"symbol":sym,"mode":mode,"take":take,"conf":conf,"q_tilt":q_tilt,"rl_tilt":rl_tilt,"vol":vol,"vol_bucket":bucket,"reason":reason})
        return take, conf, q_tilt, rl_tilt, vol, bucket, reason

    def execute(self, sym, conf, vol_bucket, reason, mode="LIVE"):
        mark_entry_time()
        pnl = (0.25 if random.random()<conf else -0.30) * (1.0 if vol_bucket in ("NORMAL","CALM") else 0.9)
        self.balance += pnl
        pot_balance = self.balance + max(0.0, pnl)*0.2
        self.db.log_trade(symbol=sym, side="BUY", volume=0.1, profit=pnl, conf=conf, mode=mode, reason=reason, vol_bucket=vol_bucket,
                          balance_after=self.balance, potential_balance=pot_balance)
        self.trades.append({"symbol":sym,"profit":pnl,"conf":conf,"mode":mode,"balance_after":self.balance,"potential_balance":pot_balance,"vol_bucket":vol_bucket,"reason":reason})

    def loop_symbol(self, sym):
        g_scans = int(GHOST_RATIO) if ENABLE_GHOST else 0
        for _ in range(g_scans):
            self.decide(sym, mode="GHOST")
        take, conf, q_tilt, rl_tilt, vol, bucket, reason = self.decide(sym, mode="LIVE")
        if take and AUTO_TRADING:
            self.execute(sym, conf, bucket, reason, mode="LIVE")

    def run(self):
        log("INFO","Jarvis CMD Ultra started.")
        while True:
            if AUTO_DISCOVER and (time.time()-self.last_disc)>DISCOVERY_REFRESH_MIN*60:
                try:
                    new=discover_crypto()
                    if new: self.symbols=new; log("INFO", f"Symbols refreshed: {len(new)} crypto SB")
                except Exception as e:
                    log("WARN", f"Discovery loop error: {e}")
                self.last_disc=time.time()
            for s in list(self.symbols):
                try: self.loop_symbol(s)
                except Exception as e: log("WARN", f"loop_symbol({s}) error: {e}")
            if time.time()-self.last_panel>5:
                render_panel(self.db, self.balance, self.symbols, self.decisions, self.trades, width=self.width)
                self.last_panel=time.time()
            time.sleep(0.5)

if __name__=="__main__":
    try:
        Jarvis().run()
    except KeyboardInterrupt:
        log("INFO","Stopped by user.")
    except Exception as e:
        log("ERROR", f"Fatal error: {e}\n{traceback.format_exc()}")
