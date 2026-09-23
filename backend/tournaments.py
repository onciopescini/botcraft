"""Tornei Botcraft — bracket 8 a eliminazione singola + report shareabile."""
from __future__ import annotations
import json
import sys
import time
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bots"))

from backend.store import get_agent, leaderboard
from backend.worker import load_decide
from runner.run import run_match

LEAGUE_OF = lambda preset: "open" if preset in ("llm-greedy", "custom") else "code-only"


def _seed_pool(n: int) -> list[int]:
    try:
        pool = json.loads((ROOT / "maps" / "pool.json").read_text())
        pub = pool.get("public_seeds", [1, 7, 11, 21, 42])
    except Exception:
        pub = [1, 7, 11, 21, 42]
    rnd = random.Random(20260921)
    return [rnd.choice(pub) + i * 1000 for i in range(n)]


def play_pair(a: str, b: str, seed: int, tag: str, best_of: int = 3, mutator: str = ""):
    """Best-of-N anti-fortuna (Halite/CodeClash style): vince chi prende più mappe."""
    ag_a, ag_b = get_agent(a), get_agent(b)
    if not ag_a or not ag_b:
        raise ValueError(f"agente mancante: {a} vs {b}")
    wa = wb = 0
    last = None
    for k in range(best_of):
        if wa * 2 >= best_of or wb * 2 >= best_of:
            break  # già deciso
        res, _ = run_match(load_decide(ag_a["preset"]), load_decide(ag_b["preset"]), seed + k * 7919,
                           out_path=str(ROOT / "matches" / f"{tag}-g{k}" / "replay.jsonl"),
                           name_a=a, name_b=b, mutator=mutator)
        last = res
        if res["winner"] == 0:
            wa += 1
        elif res["winner"] == 1:
            wb += 1
    winner = 0 if wa > wb else (1 if wb > wa else -1)
    from backend.store import connect, award_pair
    con = connect()
    award_pair(con, a, b, "tourney", winner, 2.0)  # tornei pagano doppio XP
    con.commit()
    con.close()
    return {"a": a, "b": b, "seed": seed, "winner": winner, "maps": f"{wa}-{wb}",
            "s0": last["s0"], "s1": last["s1"], "hash": last["hash"],
            "replay": f"{tag}-g0/replay.jsonl",
            "share": f"/viewer/?match={tag}-g0",
            "league_a": LEAGUE_OF(ag_a["preset"]), "league_b": LEAGUE_OF(ag_b["preset"])}


def run_bracket(names: list[str], seeds: list[int] | None = None, title: str = "weekly",
                mutator: str = ""):
    if len(names) != 8:
        raise ValueError("servono 8 nomi (anche con ripetizioni di preset diversi, ma nomi distinti)")
    seeds = seeds or _seed_pool(7)
    ts = int(time.time())
    base = f"tourney-{ts}"
    # quarti
    qf, winners_qf = [], []
    for i in range(0, 8, 2):
        m = play_pair(names[i], names[i + 1], seeds[len(qf)], f"{base}-qf{i//2}", mutator=mutator)
        qf.append(m)
        winners_qf.append(m["a"] if m["winner"] == 0 else m["b"])
    # semifinali
    sf, winners_sf = [], []
    for i in range(0, 4, 2):
        m = play_pair(winners_qf[i], winners_qf[i + 1], seeds[4 + len(sf)], f"{base}-sf{i//2}", mutator=mutator)
        sf.append(m)
        winners_sf.append(m["a"] if m["winner"] == 0 else m["b"])
    # finale + 3 posto
    losers_sf = [m["b"] if m["winner"] == 0 else m["a"] for m in sf]
    bronze = play_pair(losers_sf[0], losers_sf[1], seeds[6], f"{base}-bronze", mutator=mutator)
    final = play_pair(winners_sf[0], winners_sf[1], seeds[5], f"{base}-final", mutator=mutator)
    champion = final["a"] if final["winner"] == 0 else final["b"]
    report = {"v": 1, "title": title, "ts": ts, "mutator": mutator, "champion": champion,
              "qf": qf, "sf": sf, "bronze": bronze, "final": final}
    out = ROOT / "matches" / base / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    # default: top per Elo, fallback ai bot noti
    lb = [r["name"] for r in leaderboard()]
    names = (lb + ["bot-greedy", "bot-greedy2", "bot-random", "bot-llm1"])[:8]
    while len(names) < 8:  # nomi distinti obbligatori per Elo pulito
        names.append(f"{names[0]}-bis{len(names)}")
    import backend.store as S
    for n in names:
        if not S.get_agent(n):
            S.register_agent(n, "greedy")
    rep = run_bracket(names)
    print(f"campione: {rep['champion']}")
    print(f"finale: {rep['final']['a']} vs {rep['final']['b']} -> {rep['final']['s0']}-{rep['final']['s1']}")
    print(f"report: matches/tourney-{rep['ts']}/report.json")
