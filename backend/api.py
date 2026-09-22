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
    preset: str  # random|greedy|llm-greedy|jev-greedy|squad|bt in S2


class MatchIn(BaseModel):
    a: str
    b: str
    seed: int | None = None
    mode: str = "1v1"  # 1v1|squad


@app.post("/agents")
def post_agent(inp: AgentIn, req: Request):
    tok = require_token(req)
    if inp.preset not in ("random", "greedy", "llm-greedy", "jev-greedy", "squad", "bt", "squad"):
        return {"error": "preset deve essere random|greedy|llm-greedy|jev-greedy|squad|bt"}
    ag = register_agent(inp.name.strip(), inp.preset)
    ag = register_agent(inp.name.strip(), inp.preset)
    record_use(tok)
    return ag


@app.get("/leaderboard")
def get_lb(league: str | None = None, mode: str = "1v1"):
    lb = leaderboard(mode if mode in ("1v1", "squad") else "1v1")
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
    mode = inp.mode if inp.mode in ("1v1", "squad") else "1v1"
    mid = enqueue(inp.a, inp.b, inp.seed, mode)
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
        errs = scan(pathlib.Path(tf.name))
    h = hashlib.sha256(raw).hexdigest()[:16]
    if errs:
        return {"status": "rejected", "hash": h, "errors": errs}
    updir = ROOT / "backend" / "uploads"
    updir.mkdir(parents=True, exist_ok=True)
    (updir / f"{h}.zip").write_bytes(raw)
    return {"status": "quarantined", "hash": h,
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
    from backend.store import get_agent, recent_matches
    ag = get_agent(name)
    if not ag:
        raise HTTPException(404, "agente inesistente")
    recent = recent_matches(name)
    elo = ag.get("elo", 1200)
    games = ag.get("games", 0)
    badges = []
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
    me = exchange(code)
    tok = token_for_discord(me["discord_id"], me["username"])
    return {"token": tok, "username": me["username"],
            "hint": "usalo come Authorization: Bearer nei POST"}
