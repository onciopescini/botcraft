"""API Botcraft S1 — submit agenti, upload zip, enqueue match, leaderboard, replay statici."""
from __future__ import annotations
import hashlib
import io
import os
import sys
import pathlib
import zipfile
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.store import init, register_agent, leaderboard, enqueue, get_match, check_quota, record_use, pending_count
from sdk.check import scan

TOKENS = {t.strip() for t in os.environ.get("API_TOKENS", "").split(",") if t.strip()}


def require_token(req: Request) -> str:
    from backend.store import token_owner
    if not TOKENS:  # dev locale: aperto
        return "local"
    auth = req.headers.get("authorization", "")
    tok = auth.removeprefix("Bearer ").strip()
    if tok in TOKENS or token_owner(tok):
        return tok
    raise HTTPException(401, "serve Bearer token (API_TOKENS o login Discord)")

app = FastAPI(title="Botcraft S1")
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def _json_500(req: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return JSONResponse({"detail": "errore interno, riprova"}, status_code=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8000").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
init()
# replay statici: /replays/ladder-4/replay.jsonl e /replays/1/replay.jsonl
(ROOT / "matches").mkdir(parents=True, exist_ok=True)
app.mount("/replays", StaticFiles(directory=str(ROOT / "matches")), name="replays")


@app.get("/health")
def health():
    return {"ok": True, "game": "botcraft"}


@app.get("/")
def root():
    return {"game": "botcraft", "health": "/health", "docs": "/docs",
            "leaderboard": "/leaderboard", "viewer": "vedi repo /viewer e /site"}


class AgentIn(BaseModel):
    name: str
    preset: str  # random|greedy|llm-greedy|jev-greedy|squad|bt|racer in S2


class MatchIn(BaseModel):
    a: str
    b: str
    seed: int | None = None
    mode: str = "1v1"  # 1v1|blitz|squad
    coach_a: dict | None = None  # {"tick":t,"x":x,"y":y} 1 ping coach
    coach_b: dict | None = None
    draft_a: dict | None = None  # {"hp10":n,"sword":bool,"walls2":n,"wood2":n,"stone2":n,"gold1":n} max 10pt
    draft_b: dict | None = None
    mutator: str = ""  # gold_rush|no_swords|fast_gas (rotazione settimanale)


@app.post("/agents")
def post_agent(inp: AgentIn, req: Request):
    tok = require_token(req)
    if inp.preset not in ("random", "greedy", "llm-greedy", "jev-greedy", "squad", "bt", "racer", "squad"):
        return {"error": "preset deve essere random|greedy|llm-greedy|jev-greedy|squad|bt|racer"}
    ag = register_agent(inp.name.strip(), inp.preset)
    ag = register_agent(inp.name.strip(), inp.preset)
    record_use(tok)
    return ag


@app.get("/leaderboard")
def get_lb(league: str | None = None, mode: str = "1v1"):
    lb = leaderboard(mode if mode in ("1v1", "blitz", "squad", "race") else "1v1")
    if league in ("code-only", "open"):
        want = "code-only" if league == "code-only" else "open"
        lb = [r for r in lb if ("open" if r["preset"] in ("llm-greedy", "jev-greedy", "custom") else "code-only") == want]
    return lb


@app.post("/matches")
def post_match(inp: MatchIn, req: Request):
    tok = require_token(req)
    if pending_count() > 200:
        raise HTTPException(429, "coda piena, riprova tra poco")
    from backend.store import get_agent
    pa = (get_agent(inp.a) or {}).get("preset", "")
    pb = (get_agent(inp.b) or {}).get("preset", "")
    league = "open" if pa in ("llm-greedy", "jev-greedy", "custom") or pb in ("llm-greedy", "jev-greedy", "custom") else "code-only"
    ok, left = check_quota(tok, league)
    if not ok:
        raise HTTPException(429, f"quota giornaliera {league} esaurita (monetizzabile: alza il piano)")
    mode = inp.mode if inp.mode in ("1v1", "blitz", "squad", "race") else "1v1"
    mid = enqueue(inp.a, inp.b, inp.seed, mode, inp.coach_a, inp.coach_b, inp.draft_a, inp.draft_b,
                  inp.mutator if inp.mutator in ("gold_rush", "no_swords", "fast_gas") else "")
    record_use(tok)
    return {"id": mid, "status": "pending", "league": league, "mode": mode, "quota_left": left - 1,
            "hint": "avvia backend/worker.py per giocarlo"}


class ForkIn(BaseModel):
    src: str
    new_name: str


@app.post("/agents/fork")
def post_fork(inp: ForkIn, req: Request):
    require_token(req)
    from backend.store import fork_agent
    try:
        ag = fork_agent(inp.src.strip(), inp.new_name.strip())
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {**ag, "forked_from": inp.src}


@app.get("/matches/{mid}")
def get_m(mid: int):
    m = get_match(mid)
    if not m:
        return {"error": "not found"}
    # share link pronto da copiare (funziona se viewer servito dalla stessa origine o con CORS)
    m["replay_url"] = f"/replays/ladder-{mid}/replay.jsonl"
    m["share"] = f"/viewer/?match=ladder-{mid}"
    return m


@app.post("/agents/upload")
async def upload_agent(file: UploadFile = File(...)):
    """Pre-approvazione: valida zip <2MB, <200 file, agent.py+capabilities.yaml, scan AST.
    Salva in backend/uploads/:hash.zip in quarantena. Esecuzione custom solo con worker Docker (S1)."""
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        return {"error": "zip >2MB rifiutato"}
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        names = z.namelist()
    except Exception:
        return {"error": "zip invalido"}
    if len(names) > 200:
        return {"error": "troppi file (>200)"}
    if "agent.py" not in names or "capabilities.yaml" not in names:
        return {"error": "servono agent.py + capabilities.yaml nella root dello zip"}
    if any(n.endswith((".exe", ".so", ".dll", ".sh")) for n in names):
        return {"error": "eseguibili non ammessi"}
    src = z.read("agent.py").decode(errors="strict")
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(src)
        tf.flush()
        errs, warns = scan(pathlib.Path(tf.name))
    h = hashlib.sha256(raw).hexdigest()[:16]
    if errs:
        return {"status": "rejected", "hash": h, "errors": errs}
    updir = ROOT / "backend" / "uploads"
    updir.mkdir(parents=True, exist_ok=True)
    (updir / f"{h}.zip").write_bytes(raw)
    return {"status": "quarantined", "hash": h, "warnings": warns,
            "hint": "validato e firmato. Esecuzione custom attiva solo con worker Docker; in locale usa preset random|greedy|llm-greedy"}


class TourneyIn(BaseModel):
    names: list[str]
    title: str = "weekly"


@app.post("/tournaments")
def post_tourney(inp: TourneyIn, req: Request):
    tok = require_token(req)
    if len(inp.names) != 8:
        raise HTTPException(400, "servono 8 nomi")
    ok, _ = check_quota(tok, "open", limit_free=5, limit_open=5)
    if not ok:
        raise HTTPException(429, "quota tornei giornaliera esaurita")
    from backend.tournaments import run_bracket
    from backend.caster import comment_tournament
    rep = run_bracket(inp.names, title=inp.title[:40])
    commentary = comment_tournament(rep)
    (ROOT / "matches" / f"tourney-{rep['ts']}" / "commentary.md").write_text(commentary)
    record_use(tok)
    return {"champion": rep["champion"], "ts": rep["ts"],
            "report": f"/replays/tourney-{rep['ts']}/report.json",
            "commentary": commentary[:2000]}


@app.get("/tournaments")
def list_tourneys():
    import json as _j
    out = []
    md = ROOT / "matches"
    if md.exists():
        for d in sorted(md.glob("tourney-*"), reverse=True):
            rp = d / "report.json"
            if rp.exists():
                try:
                    r = _j.loads(rp.read_text())
                    out.append({"ts": r["ts"], "title": r.get("title", ""),
                                "champion": r.get("champion", "")})
                except Exception:
                    pass
    return out[:20]


@app.get("/agents/{name}")
def agent_profile(name: str):
    from backend.store import get_agent, recent_matches, get_progress, owned_packs, prestige_of
    ag = get_agent(name)
    if not ag:
        raise HTTPException(404, "agente inesistente")
    recent = recent_matches(name)
    prest = prestige_of(name)
    elo = ag.get("elo", 1200)
    games = ag.get("games", 0)
    badges = []
    for p in prest:
        badges.append(f"prestige-{p['rank']}@{p['season']}")
    if games < 5:
        badges.append("rookie")
    if games >= 20:
        badges.append("veteran")
    if elo >= 1300:
        badges.append("gladiator")
    elif elo >= 1200:
        badges.append("contender")
    else:
        badges.append("underdog")
    if ag.get("preset") == "squad":
        badges.append("captain")
    if ag.get("preset") == "llm-greedy":
        badges.append("mind")
    if ag.get("preset") == "greedy":
        badges.append("farmer")
    if ag.get("preset") == "random":
        badges.append("wild")
    return {**{k: ag[k] for k in ("name", "preset", "elo", "games") if k in ag},
            "elo_squad": ag.get("elo_squad", 1200), "games_squad": ag.get("games_squad", 0),
            "elo_blitz": ag.get("elo_blitz", 1200), "games_blitz": ag.get("games_blitz", 0),
            "elo_race": ag.get("elo_race", 1200), "games_race": ag.get("games_race", 0),
            "coins": ag.get("coins", 100), "progress": get_progress(name),
            "packs": owned_packs(name),
            "badges": badges, "recent": recent,
            "share": f"/viewer/profile.html?name={name}"}


class SeasonIn(BaseModel):
    names: list[str]
    seed: int | None = None
    title: str = "season"
    ticks: int = 500

@app.post("/world/seasons")
def post_season(inp: SeasonIn, req: Request):
    tok = require_token(req)
    if not (2 <= len(inp.names) <= 50):
        raise HTTPException(400, "servono 2-50 nomi")
    ok, _ = check_quota(tok, "open", limit_free=3, limit_open=3)
    if not ok:
        raise HTTPException(429, "quota stagioni giornaliera esaurita")
    import time as _t
    from backend.store import get_agent as _ga
    from runner.run_world import run_season
    import sys as _s
    _s.path.insert(0, str(ROOT / "bots"))
    import importlib as _il
    decides = {}
    for n in inp.names:
        ag = _ga(n)
        if not ag:
            raise HTTPException(404, f"agente {n} inesistente")
        mod = _il.import_module(f"{ag['preset'].replace('-', '_')}_bot")
        decides[n] = mod.decide
    ts = int(_t.time())
    out = str(ROOT / "matches" / f"world-{ts}")
    rep, _ = run_season(decides, inp.seed or ts % 100000, title=inp.title[:40],
                        out_dir=out, max_ticks=max(50, min(500, inp.ticks)))
    record_use(tok)
    return {"dir": f"world-{ts}", "champion": rep["champion"],
            "standings": rep["standings"][:5], "share": f"/viewer/world.html"}


@app.get("/world/seasons")
def list_seasons():
    import json as _j
    out = []
    md = ROOT / "matches"
    if md.exists():
        for d in sorted(md.glob("world-*"), reverse=True):
            sj = d / "season.json"
            if sj.exists():
                try:
                    r = _j.loads(sj.read_text())
                    out.append({"dir": d.name, "title": r.get("title", ""),
                                "champion": r.get("champion", ""), "tick": r.get("tick", 0)})
                except Exception:
                    pass
    return out[:20]


@app.get("/auth/discord/login")
def discord_login():
    from backend.auth_discord import enabled, login_url
    if not enabled():
        raise HTTPException(501, "login Discord non configurato (DISCORD_* env)")
    from fastapi.responses import RedirectResponse
    return RedirectResponse(login_url())


@app.get("/auth/discord/callback")
def discord_callback(code: str = ""):
    from backend.auth_discord import enabled, exchange
    from backend.store import token_for_discord
    if not enabled():
        raise HTTPException(501, "login Discord non configurato (DISCORD_* env)")
    if not code:
        raise HTTPException(400, "code mancante")
    try:
        me = exchange(code)
    except Exception as e:
        raise HTTPException(502, f"Discord exchange fallito: {type(e).__name__} (controlla secret e redirect)")
    try:
        tok = token_for_discord(me["discord_id"], me["username"])
    except Exception as e:
        raise HTTPException(502, f"DB token fallito: {type(e).__name__}")
    return {"token": tok, "username": me["username"],
            "hint": "usalo come Authorization: Bearer nei POST"}


class DailyIn(BaseModel):
    name: str
    coach: dict | None = None  # 1 ping {"tick":t,"x":x,"y":y}


@app.get("/daily")
def get_daily():
    from backend.store import daily_board
    return daily_board()


@app.post("/daily")
def post_daily(inp: DailyIn, req: Request):
    from backend.store import daily_seed, get_agent, register_agent
    tok = require_token(req)
    ag = get_agent(inp.name)
    if not ag:
        raise HTTPException(404, "agente inesistente")
    day, seed = daily_seed()
    if not daily_submit_check(inp.name, day):
        raise HTTPException(429, "daily già giocato oggi: 1 submit/giorno")
    try:
        register_agent("daily-rival", "greedy")
    except Exception:
        pass
    mid = enqueue(inp.name, "daily-rival", seed, "daily", inp.coach, None)
    record_use(tok)
    return {"id": mid, "day": day, "seed": seed, "mode": "daily",
            "hint": "stesso seed per tutti oggi. Chi fa più punti vince il giorno"}


def daily_submit_check(name: str, day: str) -> bool:
    import sqlite3
    con = sqlite3.connect(str(ROOT / "backend" / "botcraft.db"))
    row = con.execute("SELECT 1 FROM daily WHERE day=? AND name=?", (day, name)).fetchone()
    con.close()
    return row is None


class BetIn(BaseModel):
    mid: int
    bettor: str
    pick: str  # a|b
    amount: int

@app.post("/bets")
def post_bet(inp: BetIn, req: Request):
    from backend.store import place_bet, get_agent
    require_token(req)
    if not get_agent(inp.bettor):
        raise HTTPException(404, "scommettitore inesistente")
    try:
        bid = place_bet(inp.mid, inp.bettor, inp.pick, inp.amount)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"bet": bid, "pot_hint": "i vincitori spartiscono il piatto in proporzione"}


@app.get("/coins/{name}")
def get_coins(name: str):
    from backend.store import coins_of, get_agent
    if not get_agent(name):
        raise HTTPException(404, "agente inesistente")
    return {"name": name, "coins": coins_of(name)}


@app.get("/prompts")
def list_prompts():
    from backend.store import PACKS
    out = []
    for pack, price in PACKS.items():
        p = ROOT / "prompts" / f"{pack}.md"
        out.append({"pack": pack, "price": price,
                    "preview": p.read_text()[:300] if p.exists() else ""})
    return out


class BuyIn(BaseModel):
    name: str
    pack: str


@app.post("/prompts/buy")
def buy_prompt(inp: BuyIn, req: Request):
    from backend.store import buy_pack
    require_token(req)
    try:
        st = buy_pack(inp.name, inp.pack)
    except ValueError as e:
        raise HTTPException(400, str(e))
    p = ROOT / "prompts" / f"{inp.pack}.md"
    return {"status": st, "pack": inp.pack,
            "content": p.read_text() if p.exists() else ""}


def _require_admin(req: Request):
    admin = os.environ.get("ADMIN_TOKEN", "").strip()
    if admin:
        tok = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if tok != admin:
            raise HTTPException(403, "serve token admin")
        return tok
    return require_token(req)


class RolloverIn(BaseModel):
    season: str


@app.post("/admin/rollover")
def post_rollover(inp: RolloverIn, req: Request):
    from backend.store import season_rollover
    _require_admin(req)
    champs = season_rollover(inp.season[:20])
    return {"season": inp.season[:20], "champions": champs,
            "note": "Elo/XP/boost resettati, prestige assegnati"}


@app.delete("/agents/{name}")
def delete_agent_ep(name: str, req: Request):
    from backend.store import delete_agent, get_agent
    require_token(req)
    if not get_agent(name):
        raise HTTPException(404, "agente inesistente")
    delete_agent(name)
    return {"deleted": name}
