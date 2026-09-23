"""Lega AlphaStar-style: main agents + exploiter che cacciano il leader (PFSP-lite).

Uso: python scripts/league.py [--title lega-1]
- main: top-4 Elo 1v1. exploiter: 2 pescati tra Elo medio-bassa + random.
- PFSP: ogni exploiter gioca 2 match contro il leader; i main giocano round-robin.
- Exploiter che batte il leader: bonus XP x3 (incentivo anti-meta).
- Report: matches/league-<ts>/report.json (ruoli, risultati, counter-scoperti).
"""
from __future__ import annotations
import json
import sys
import time
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.store import leaderboard, connect, XP_BASE
from backend.worker import load_decide
from runner.run import run_match


def pick_roster():
    from backend.store import get_agent
    lb = [r["name"] for r in leaderboard() if r["games"] >= 1]
    if not lb:
        lb = [r["name"] for r in leaderboard()]
    mains = lb[:4]
    pool = [n for n in lb[4:] if n not in mains]
    exploiters = (pool[:1] + pool[-1:] + ["bot-random", "bot-greedy"])[:2]
    seen, roster = set(), []
    for n in mains + exploiters:
        if n not in seen and get_agent(n):
            seen.add(n)
            roster.append(n)
    while len(roster) < 6 and lb:
        roster.append(lb[len(roster) % len(lb)])
    return roster[:4], roster[4:6]


def play(a, b, seed, tag, xp_mult=1.0):
    import backend.store as S
    ag_a, ag_b = S.get_agent(a), S.get_agent(b)
    res, _ = run_match(load_decide(ag_a["preset"]), load_decide(ag_b["preset"]), seed,
                       out_path=str(ROOT / "matches" / tag / "replay.jsonl"),
                       name_a=a, name_b=b)
    con = S.connect()
    S.award_pair(con, a, b, "tourney", res["winner"], xp_mult)
    con.commit()
    con.close()
    return {"a": a, "b": b, "seed": seed, "winner": res["winner"],
            "s0": res["s0"], "s1": res["s1"], "share": f"/viewer/?match={tag}"}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="lega")
    args = ap.parse_args()
    mains, exploiters = pick_roster()
    leader = mains[0]
    ts, i = int(time.time()), 0
    games = []
    # PFSP: exploiter vs leader (caccia al meta)
    for e in exploiters:
        for k in range(2):
            i += 1
            g = play(e, leader, 5000 + i, f"league-{ts}-x{i}", xp_mult=3.0)
            g["role"] = "exploit"
            games.append(g)
    # round-robin main
    for x in range(len(mains)):
        for y in range(x + 1, len(mains)):
            i += 1
            g = play(mains[x], mains[y], 5000 + i, f"league-{ts}-m{i}", xp_mult=1.0)
            g["role"] = "main"
            games.append(g)
    counters = [g for g in games if g["role"] == "exploit"
                and ((g["winner"] == 0 and g["a"] != leader) or (g["winner"] == 1 and g["b"] != leader))]
    rep = {"v": 1, "title": args.title, "ts": ts, "mains": mains,
           "exploiters": exploiters, "leader": leader,
           "counters_found": counters, "games": games}
    d = ROOT / "matches" / f"league-{ts}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.json").write_text(json.dumps(rep, indent=2))
    print(f"lega: leader={leader} mains={mains} exploiters={exploiters}")
    print(f"counter trovati: {len(counters)}")
    print(f"report: matches/league-{ts}/report.json")


if __name__ == "__main__":
    main()
