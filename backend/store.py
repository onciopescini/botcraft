"""Store SQLite Botcraft — agenti, coda match, Elo+Glicko-RD, daily, coin."""
from __future__ import annotations
import json
import sqlite3
import pathlib
import time
import random

DB = pathlib.Path(__file__).resolve().parents[1] / "backend" / "botcraft.db"


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB), timeout=30.0)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    return con


def init():
    con = connect()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS agents(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE NOT NULL,
      preset TEXT NOT NULL,
      elo REAL NOT NULL DEFAULT 1200,
      games INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS matches(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      a TEXT NOT NULL, b TEXT NOT NULL,
      seed INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      winner INTEGER, s0 INTEGER, s1 INTEGER, hash TEXT,
      mode TEXT NOT NULL DEFAULT '1v1',
      created REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS api_usage(
      token TEXT NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (token, day)
    );
    CREATE TABLE IF NOT EXISTS tokens(
      token TEXT PRIMARY KEY, discord_id TEXT NOT NULL, username TEXT NOT NULL DEFAULT '',
      created REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS daily(
      day TEXT NOT NULL, name TEXT NOT NULL, score INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (day, name)
    );
    CREATE TABLE IF NOT EXISTS bets(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      mid INTEGER NOT NULL, bettor TEXT NOT NULL, pick TEXT NOT NULL,
      amount INTEGER NOT NULL, settled INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS xp(
      name TEXT PRIMARY KEY, xp INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS owned(
      name TEXT NOT NULL, pack TEXT NOT NULL,
      PRIMARY KEY (name, pack)
    );
    CREATE TABLE IF NOT EXISTS prestige(
      name TEXT NOT NULL, season TEXT NOT NULL, rank INTEGER NOT NULL,
      PRIMARY KEY (name, season)
    );
    """)
    con.commit()
    for ddl in ("ALTER TABLE agents ADD COLUMN elo_squad REAL NOT NULL DEFAULT 1200",
                "ALTER TABLE agents ADD COLUMN games_squad INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE agents ADD COLUMN elo_blitz REAL NOT NULL DEFAULT 1200",
                "ALTER TABLE agents ADD COLUMN games_blitz INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE agents ADD COLUMN rd REAL NOT NULL DEFAULT 350",
                "ALTER TABLE agents ADD COLUMN rd_squad REAL NOT NULL DEFAULT 350",
                "ALTER TABLE agents ADD COLUMN rd_blitz REAL NOT NULL DEFAULT 350",
                "ALTER TABLE agents ADD COLUMN last_game REAL NOT NULL DEFAULT 0",
                "ALTER TABLE agents ADD COLUMN coins INTEGER NOT NULL DEFAULT 100",
                "ALTER TABLE matches ADD COLUMN mode TEXT NOT NULL DEFAULT '1v1'",
                "ALTER TABLE matches ADD COLUMN coach_a TEXT NOT NULL DEFAULT ''",
                "ALTER TABLE matches ADD COLUMN coach_b TEXT NOT NULL DEFAULT ''"):
        try:
            con.execute(ddl)
        except Exception:
            pass
    con.commit()
    con.close()


def register_agent(name: str, preset: str):
    assert preset in ("random", "greedy", "llm-greedy", "squad", "jev-greedy", "bt"), "preset: random|greedy|llm-greedy|squad|jev-greedy|bt"
    con = connect()
    try:
        con.execute("INSERT INTO agents(name,preset) VALUES(?,?)", (name, preset))
        con.commit()
    except sqlite3.IntegrityError:
        pass
    row = con.execute("SELECT * FROM agents WHERE name=?", (name,)).fetchone()
    con.close()
    return dict(row)


def get_agent(name: str):
    con = connect()
    row = con.execute("SELECT * FROM agents WHERE name=?", (name,)).fetchone()
    con.close()
    return dict(row) if row else None


def leaderboard(mode: str = "1v1"):
    con = connect()
    if mode == "squad":
        rows = con.execute("SELECT name,preset,elo_squad AS elo,games_squad AS games,rd_squad AS rd FROM agents ORDER BY elo_squad DESC").fetchall()
    elif mode == "blitz":
        rows = con.execute("SELECT name,preset,elo_blitz AS elo,games_blitz AS games,rd_blitz AS rd FROM agents ORDER BY elo_blitz DESC").fetchall()
    else:
        rows = con.execute("SELECT name,preset,elo,games,rd FROM agents ORDER BY elo DESC").fetchall()
    con.close()
    return [dict(r) for r in rows]


def enqueue(a: str, b: str, seed: int | None = None, mode: str = "1v1",
            coach_a: dict | None = None, coach_b: dict | None = None):
    if a == b:
        raise ValueError("usa due nomi diversi (es. bot-greedy e bot-greedy2) anche se stesso preset")
    # 20% seed nascosti: seed alto random non comunicato prima (qui solo flag concettuale)
    if seed is None:
        seed = random.randrange(1_000_000)
    con = connect()
    cur = con.execute(
        "INSERT INTO matches(a,b,seed,status,mode,coach_a,coach_b,created) VALUES(?,?,?,?,?,?,?,?)",
        (a, b, seed, "pending", mode,
         json.dumps(coach_a) if coach_a else "", json.dumps(coach_b) if coach_b else "",
         time.time()))
    mid = cur.lastrowid
    con.commit()
    con.close()
    return mid


def next_pending():
    con = connect()
    row = con.execute("SELECT * FROM matches WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
    con.close()
    return dict(row) if row else None


def mark_failed(mid: int, reason: str):
    con = connect()
    con.execute("UPDATE matches SET status='failed',hash=? WHERE id=?", (reason[:64], mid))
    con.commit()
    con.close()


def finish_match(mid: int, winner: int, s0: int, s1: int, h: str):
    con = connect()
    con.execute("UPDATE matches SET status='done',winner=?,s0=?,s1=?,hash=? WHERE id=?",
                (winner, s0, s1, h, mid))
    m = con.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
    if m["mode"] == "daily":
        # puzzle giornaliero: niente Elo, solo classifica score (1 submit/giorno già garantito all'enqueue)
        con.commit()
        con.close()
        daily_submit(m["a"], s0)
        if m["b"] != "daily-rival":
            daily_submit(m["b"], s1)
        settle_bets(mid, winner)
        award_xp(mid, winner, s0, s1)
        return
    squad = (m["mode"] == "squad")
    blitz = (m["mode"] == "blitz")
    ecol, gcol = ("elo_squad", "games_squad") if squad else (("elo_blitz", "games_blitz") if blitz else ("elo", "games"))
    rdcol = "rd_squad" if squad else ("rd_blitz" if blitz else "rd")
    import time as _t
    now = _t.time()
    # Elo + Glicko-RD: RD cresce con l'inattività (max 350), cala giocando (min 30).
    # K scalato da RD: rientranti si muovono in fretta, grinder stabili.
    for name, score in ((m["a"], 1.0 if winner == 0 else 0.5 if winner == -1 else 0.0),
                        (m["b"], 1.0 if winner == 1 else 0.5 if winner == -1 else 0.0)):
        ag = con.execute("SELECT * FROM agents WHERE name=?", (name,)).fetchone()
        opp_name = m["b"] if name == m["a"] else m["a"]
        opp = con.execute("SELECT * FROM agents WHERE name=?", (opp_name,)).fetchone()
        idle_days = max(0.0, (now - (ag["last_game"] or now)) / 86400)
        rd = min(350.0, max(30.0, ag[rdcol] + idle_days * 12.0))
        base_k = 32 if ag[gcol] < 20 else 16
        k = base_k * (rd / 150.0)
        k = max(8.0, min(64.0, k))
        exp = 1.0 / (1.0 + 10 ** ((opp[ecol] - ag[ecol]) / 400))
        new_elo = ag[ecol] + k * (score - exp)
        new_rd = max(30.0, rd * 0.92)
        con.execute(f"UPDATE agents SET {ecol}=?,{gcol}={gcol}+1,{rdcol}=?,last_game=? WHERE name=?",
                    (new_elo, new_rd, now, name))
    con.commit()
    con.close()
    settle_bets(mid, winner)
    award_xp(mid, winner, s0, s1)


def fork_agent(src: str, new_name: str):
    """Marketplace fork 1-click: copia preset+memoria, Elo da 1200."""
    import shutil
    con = connect()
    row = con.execute("SELECT * FROM agents WHERE name=?", (src,)).fetchone()
    if not row:
        con.close()
        raise ValueError(f"sorgente {src} inesistente")
    try:
        con.execute("INSERT INTO agents(name,preset) VALUES(?,?)", (new_name, row["preset"]))
        con.commit()
    except Exception:
        pass
    con.close()
    memdir = pathlib.Path(__file__).resolve().parents[1] / "backend" / "memory"
    srcm, dstm = memdir / f"{src}.json", memdir / f"{new_name}.json"
    if srcm.exists() and not dstm.exists():
        shutil.copy(srcm, dstm)
    return get_agent(new_name)


def get_match(mid: int):
    con = connect()
    row = con.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
    con.close()
    return dict(row) if row else None


def recent_matches(name: str, limit: int = 10):
    con = connect()
    rows = con.execute(
        "SELECT * FROM matches WHERE (a=? OR b=?) AND status='done' ORDER BY id DESC LIMIT ?",
        (name, name, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def check_quota(token: str, league: str, limit_free: int = 60, limit_open: int = 20) -> tuple[bool, int]:
    """Quote giornaliere scalabili/monetizzabili: code-only larga, open stretta (BYOK)."""
    import datetime
    day = datetime.date.today().isoformat()
    con = connect()
    row = con.execute("SELECT count FROM api_usage WHERE token=? AND day=?", (token, day)).fetchone()
    used = row["count"] if row else 0
    limit = limit_open if league == "open" else limit_free
    con.close()
    return used < limit, limit - used


def record_use(token: str):
    import datetime
    day = datetime.date.today().isoformat()
    con = connect()
    con.execute("INSERT INTO api_usage(token,day,count) VALUES(?,?,1) "
                "ON CONFLICT(token,day) DO UPDATE SET count=count+1", (token, day))
    con.commit()
    con.close()


PACKS = {"greedy-opener": 50, "sword-rush": 100, "totem-close": 200}


def owned_packs(name: str) -> list[str]:
    con = connect()
    rows = con.execute("SELECT pack FROM owned WHERE name=?", (name,)).fetchall()
    con.close()
    return [r["pack"] for r in rows]


def buy_pack(name: str, pack: str) -> str:
    """Compra conoscenza con coin vinte. MAI effetti automatici nel sim."""
    if pack not in PACKS:
        raise ValueError("pack inesistente")
    con = connect()
    ag = con.execute("SELECT coins FROM agents WHERE name=?", (name,)).fetchone()
    if not ag:
        con.close()
        raise ValueError("agente inesistente")
    if con.execute("SELECT 1 FROM owned WHERE name=? AND pack=?", (name, pack)).fetchone():
        con.close()
        return "owned"
    if ag["coins"] < PACKS[pack]:
        con.close()
        raise ValueError(f"servono {PACKS[pack]} coin (ne hai {ag['coins']})")
    con.execute("UPDATE agents SET coins=coins-? WHERE name=?", (PACKS[pack], name))
    con.execute("INSERT INTO owned(name,pack) VALUES(?,?)", (name, pack))
    con.commit()
    con.close()
    return "ok"


def pending_count() -> int:
    con = connect()
    row = con.execute("SELECT COUNT(*) c FROM matches WHERE status='pending'").fetchone()
    con.close()
    return row["c"]


XP_BASE = {"blitz": 10, "1v1": 20, "squad": 30, "daily": 15, "world": 30, "tourney": 20}


def level_of(xp: int) -> int:
    return xp // 100


def bonus_of(level: int) -> tuple[int, int]:
    """(mem_kb_extra, ping_extra). Auto: pari +1KB (cap 20KB tot), dispari +1 ping (cap 3)."""
    mem = min(10, (level + 1) // 2)
    ping = min(2, level // 2)
    return mem, 1 + ping  # 1 ping base + bonus


def get_progress(name: str) -> dict:
    con = connect()
    row = con.execute("SELECT xp FROM xp WHERE name=?", (name,)).fetchone()
    con.close()
    xp = row["xp"] if row else 0
    lv = level_of(xp)
    mem, ping = bonus_of(lv)
    return {"xp": xp, "level": lv, "mem_kb": 10 + mem, "pings": ping}


def award_xp(mid: int, winner: int, s0: int, s1: int):
    con = connect()
    m = con.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
    if not m:
        con.close()
        return
    award_pair(con, m["a"], m["b"], m["mode"], winner, 1.0)
    con.commit()
    con.close()


def award_pair(con, a: str, b: str, mode: str, winner: int, mult: float):
    """XP diretta senza riga matches (tornei x2, mondo)."""
    base = XP_BASE.get(mode, 20)
    ecol = {"squad": "elo_squad", "blitz": "elo_blitz"}.get(mode, "elo")
    for name, won in ((a, winner == 0), (b, winner == 1)):
        ag = con.execute("SELECT * FROM agents WHERE name=?", (name,)).fetchone()
        opp = b if name == a else a
        op = con.execute("SELECT * FROM agents WHERE name=?", (opp,)).fetchone()
        gap = max(0.0, (op[ecol] if op else 1200) - (ag[ecol] if ag else 1200)) if ag else 0.0
        pts = round(base * mult * (1.0 + min(1.0, gap / 800.0))
                    * (1.0 if won else (0.5 if winner == -1 else 0.25)))
        con.execute("INSERT INTO xp(name,xp) VALUES(?,?) "
                    "ON CONFLICT(name) DO UPDATE SET xp=xp+?", (name, pts, pts))


def daily_seed() -> tuple[str, int]:
    """Seed unico del giorno per tutti: YYYYMMDD -> deterministico."""
    import datetime
    day = datetime.date.today().isoformat()
    seed = int(day.replace("-", "")) % 100000
    return day, seed


def daily_submit(name: str, score: int) -> bool:
    """1 submit/giorno per agente. Ritorna False se già presente."""
    day, _ = daily_seed()
    con = connect()
    try:
        con.execute("INSERT INTO daily(day,name,score) VALUES(?,?,?)", (day, name, score))
        con.commit()
        ok = True
    except Exception:
        ok = False
    con.close()
    return ok


def daily_board(limit: int = 20):
    day, seed = daily_seed()
    con = connect()
    rows = con.execute("SELECT name,score FROM daily WHERE day=? ORDER BY score DESC LIMIT ?",
                       (day, limit)).fetchall()
    con.close()
    return {"day": day, "seed": seed, "board": [dict(r) for r in rows]}


def coins_of(name: str) -> int:
    con = connect()
    row = con.execute("SELECT coins FROM agents WHERE name=?", (name,)).fetchone()
    con.close()
    return row["coins"] if row else 0


def place_bet(mid: int, bettor: str, pick: str, amount: int):
    """Scommessa coin finte sul vincitore ('a' o 'b'). Pari-mutuel al settle."""
    if pick not in ("a", "b") or amount <= 0:
        raise ValueError("pick a|b, amount > 0")
    con = connect()
    m = con.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
    if not m or m["status"] != "pending":
        raise ValueError("match inesistente o già giocato")
    if m["a"] != bettor and m["b"] != bettor:
        pass  # chiunque può puntare, anche non giocatori
    ag = con.execute("SELECT coins FROM agents WHERE name=?", (bettor,)).fetchone()
    if not ag or ag["coins"] < amount:
        con.close()
        raise ValueError("coin insufficienti (100 gratis a ogni agente)")
    con.execute("UPDATE agents SET coins=coins-? WHERE name=?", (amount, bettor))
    cur = con.execute("INSERT INTO bets(mid,bettor,pick,amount) VALUES(?,?,?,?)",
                      (mid, bettor, pick, amount))
    bid = cur.lastrowid
    con.commit()
    con.close()
    return bid


def settle_bets(mid: int, winner: int):
    """Pari-mutuel: i vincitori si spartiscono il piatto in proporzione."""
    if winner not in (0, 1):
        return
    win_pick = "a" if winner == 0 else "b"
    con = connect()
    bets = [dict(r) for r in con.execute("SELECT * FROM bets WHERE mid=? AND settled=0", (mid,))]
    if not bets:
        con.close()
        return
    pot = sum(b["amount"] for b in bets)
    win_tot = sum(b["amount"] for b in bets if b["pick"] == win_pick)
    for b in bets:
        if b["pick"] == win_pick and win_tot > 0:
            prize = round(pot * b["amount"] / win_tot)
            con.execute("UPDATE agents SET coins=coins+? WHERE name=?", (prize, b["bettor"]))
        con.execute("UPDATE bets SET settled=1 WHERE id=?", (b["id"],))
    con.commit()
    con.close()


def token_for_discord(discord_id: str, username: str) -> str:
    """Riuso: stesso discord = stesso token (stabile per spettatore)."""
    import time as _t
    from backend.auth_discord import mint_token
    con = connect()
    row = con.execute("SELECT token FROM tokens WHERE discord_id=?", (discord_id,)).fetchone()
    if row:
        con.execute("UPDATE tokens SET username=? WHERE discord_id=?", (username, discord_id))
        con.commit()
        con.close()
        return row["token"]
    tok = mint_token()
    con.execute("INSERT INTO tokens(token,discord_id,username,created) VALUES(?,?,?,?)",
                (tok, discord_id, username, _t.time()))
    con.commit()
    con.close()
    return tok


def token_owner(token: str):
    con = connect()
    row = con.execute("SELECT discord_id,username FROM tokens WHERE token=?", (token,)).fetchone()
    con.close()
    return dict(row) if row else None


def season_rollover(season: str):
    """Reset Elo/XP/boost, albo d'oro top-3, badge prestige permanenti."""
    con = connect()
    top = con.execute("SELECT name,elo FROM agents ORDER BY elo DESC LIMIT 3").fetchall()
    for rank, r in enumerate(top, 1):
        con.execute("INSERT OR IGNORE INTO prestige(name,season,rank) VALUES(?,?,?)",
                    (r["name"], season, rank))
    con.execute("UPDATE agents SET elo=1200,games=0,elo_squad=1200,games_squad=0,"
                "elo_blitz=1200,games_blitz=0,rd=350,rd_squad=350,rd_blitz=350,"
                "coins=100,last_game=0")
    con.execute("DELETE FROM xp")
    con.commit()
    champs = [dict(r) for r in top]
    con.close()
    return champs


def prestige_of(name: str):
    con = connect()
    rows = con.execute("SELECT season,rank FROM prestige WHERE name=? ORDER BY season", (name,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def delete_agent(name: str):
    """Cancellazione GDPR: nome, Elo, memoria file, zip. Replay restano anonimizzati."""
    import shutil
    con = connect()
    for t in ("agents", "xp", "owned", "prestige"):
        con.execute(f"DELETE FROM {t} WHERE name=?", (name,))
    con.execute("UPDATE matches SET a='[deleted]' WHERE a=?", (name,))
    con.execute("UPDATE matches SET b='[deleted]' WHERE b=?", (name,))
    con.commit()
    con.close()
    memdir = pathlib.Path(__file__).resolve().parents[1] / "backend" / "memory"
    try:
        (memdir / f"{name}.json").unlink(missing_ok=True)
    except Exception:
        pass
    return True
