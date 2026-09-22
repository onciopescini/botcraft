"""Store SQLite Botcraft — agenti, coda match, Elo."""
from __future__ import annotations
import sqlite3
import pathlib
import time
import random

DB = pathlib.Path(__file__).resolve().parents[1] / "backend" / "botcraft.db"


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
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
    """)
    con.commit()
    for ddl in ("ALTER TABLE agents ADD COLUMN elo_squad REAL NOT NULL DEFAULT 1200",
                "ALTER TABLE agents ADD COLUMN games_squad INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE agents ADD COLUMN rd REAL NOT NULL DEFAULT 350",
                "ALTER TABLE agents ADD COLUMN rd_squad REAL NOT NULL DEFAULT 350",
                "ALTER TABLE agents ADD COLUMN last_game REAL NOT NULL DEFAULT 0",
                "ALTER TABLE matches ADD COLUMN mode TEXT NOT NULL DEFAULT '1v1'"):
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
    else:
        rows = con.execute("SELECT name,preset,elo,games,rd FROM agents ORDER BY elo DESC").fetchall()
    con.close()
    return [dict(r) for r in rows]


def enqueue(a: str, b: str, seed: int | None = None, mode: str = "1v1"):
    if a == b:
        raise ValueError("usa due nomi diversi (es. bot-greedy e bot-greedy2) anche se stesso preset")
    # 20% seed nascosti: seed alto random non comunicato prima (qui solo flag concettuale)
    if seed is None:
        seed = random.randrange(1_000_000)
    con = connect()
    cur = con.execute(
        "INSERT INTO matches(a,b,seed,status,mode,created) VALUES(?,?,?,?,?,?)",
        (a, b, seed, "pending", mode, time.time()))
    mid = cur.lastrowid
    con.commit()
    con.close()
    return mid


def next_pending():
    con = connect()
    row = con.execute("SELECT * FROM matches WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
    con.close()
    return dict(row) if row else None


def finish_match(mid: int, winner: int, s0: int, s1: int, h: str):
    con = connect()
    con.execute("UPDATE matches SET status='done',winner=?,s0=?,s1=?,hash=? WHERE id=?",
                (winner, s0, s1, h, mid))
    m = con.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
    squad = (m["mode"] == "squad")
    ecol, gcol = ("elo_squad", "games_squad") if squad else ("elo", "games")
    rdcol = "rd_squad" if squad else "rd"
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


def pending_count() -> int:
    con = connect()
    row = con.execute("SELECT COUNT(*) c FROM matches WHERE status='pending'").fetchone()
    con.close()
    return row["c"]


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
