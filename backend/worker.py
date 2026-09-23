"""Worker Botcraft — locale di default, Boxer/gVisor se BOXER_URL settato (hook prod)."""
from __future__ import annotations
import os
import sys
import pathlib
import importlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bots"))

from backend.store import init, next_pending, finish_match, get_agent
from runner.run import run_match

BOXER_URL = os.environ.get("BOXER_URL", "").strip()  # es. http://boxer:8080/run


def load_decide(preset: str):
    mod_name = f"{preset.replace('-', '_')}_bot"
    mod = importlib.import_module(mod_name)
    importlib.reload(mod)
    return mod.decide


def run_once() -> dict | None:
    init()
    m = next_pending()
    if not m:
        return None
    a = get_agent(m["a"])
    b = get_agent(m["b"])
    if not a or not b:
        raise ValueError(f"agente mancante per match {m['id']}: {m['a']} vs {m['b']}")
    decide_a = load_decide(a["preset"])
    decide_b = load_decide(b["preset"])
    if BOXER_URL:
        print(f"BOXER_URL settato ({BOXER_URL}): in prod qui si POSTa lo zip a Boxer invece di import locale. Fallback locale per S2.")
    import json as _j
    out = ROOT / "matches" / f"ladder-{m['id']}" / "replay.jsonl"
    if m.get("mode") == "race":
        from runner.run_race import run_race
        res, _ = run_race(decide_a, decide_b, m["seed"], out_path=str(out),
                          name_a=m["a"], name_b=m["b"])
    elif m.get("mode") == "squad":
        from runner.run_squad import run_squad_match
        res, _ = run_squad_match(decide_a, decide_b, m["seed"], out_path=str(out),
                                 name_a=m["a"], name_b=m["b"])
    else:
        mt = {"blitz": 60, "daily": 300}.get(m.get("mode"), 300)
        try:
            ca = _j.loads(m.get("coach_a") or "null")
        except Exception:
            ca = None
        try:
            cb = _j.loads(m.get("coach_b") or "null")
        except Exception:
            cb = None
        try:
            da = _j.loads(m.get("draft_a") or "null")
        except Exception:
            da = None
        try:
            db = _j.loads(m.get("draft_b") or "null")
        except Exception:
            db = None
        res, _ = run_match(decide_a, decide_b, m["seed"], out_path=str(out),
                           name_a=m["a"], name_b=m["b"], max_ticks=mt,
                           coach_a=ca, coach_b=cb, draft_a=da, draft_b=db,
                           mutator=m.get("mutator") or "")
    finish_match(m["id"], res["winner"], res["s0"], res["s1"], res["hash"])
    return {"id": m["id"], **res}


def run_once_safe():
    """Mai morire: match bacato -> failed, si passa oltre."""
    try:
        return run_once()
    except Exception as e:
        try:
            from backend.store import next_pending as _np, mark_failed
            m = _np()
            if m:
                mark_failed(m["id"], f"{type(e).__name__}")
                print(f"match {m['id']} fallito ({type(e).__name__}), continuo.")
        except Exception:
            pass
        return {"id": -1, "failed": True}


if __name__ == "__main__":
    import time
    n = 0
    while True:
        r = run_once_safe()
        if not r:
            print("coda vuota, stop.")
            break
        if r.get("failed"):
            continue
        n += 1
        print(f"match {r['id']}: winner={r['winner']} {r['s0']}-{r['s1']} hash={r['hash']}")
        if "--once" in sys.argv:
            break
        time.sleep(0.2)
