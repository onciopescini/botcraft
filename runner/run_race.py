"""Runner corse — replay v1-compatibile (p1/p2 + gas/coach) per il viewer 3D."""
from __future__ import annotations
import json
import sys
import pathlib
import concurrent.futures as cf

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim.race import new_race, step_race, to_obs_race, result_race, state_hash_race
from runner.run import safe_decide, load_memory, save_memory

TIMEOUT_S = 0.6


def run_race(decide_a, decide_b, seed: int, out_path: str | None = None,
             name_a: str = "r1", name_b: str = "r2"):
    st = new_race(seed)
    mem_a, mem_b = load_memory(name_a), load_memory(name_b)
    new_a, new_b = mem_a, mem_b
    replay = []
    for _ in range(160):
        if st["over"]:
            break
        obs_a, obs_b = to_obs_race(st, 0), to_obs_race(st, 1)
        obs_a["memory"], obs_b["memory"] = mem_a, mem_b
        a1, s1 = safe_decide(decide_a, obs_a)
        a2, s2 = safe_decide(decide_b, obs_b)
        if isinstance(a1.get("memory"), dict):
            new_a = a1["memory"]
        if isinstance(a2.get("memory"), dict):
            new_b = a2["memory"]
        if s1 == "timeout":
            st["agents"][0]["timeouts"] += 1
        if s2 == "timeout":
            st["agents"][1]["timeouts"] += 1
        step_race(st, a1, a2)
        g = st["agents"]
        replay.append({
            "v": 1, "tick": st["tick"], "mode": "race", "gas": 99.0,
            "p1": {"x": g[0]["x"], "y": g[0]["y"], "hp": g[0]["hp"], "wood": g[0]["wood"],
                   "stone": g[0]["stone"], "gold": g[0]["gold"], "sword": g[0]["has_sword"]},
            "p2": {"x": g[1]["x"], "y": g[1]["y"], "hp": g[1]["hp"], "wood": g[1]["wood"],
                   "stone": g[1]["stone"], "gold": g[1]["gold"], "sword": g[1]["has_sword"]},
            "a1": a1["action"], "a2": a2["action"], "m1": "", "m2": "",
            "c1": None, "c2": None, "s1": s1, "s2": s2,
            "trees": [list(p) for p in st["trees"]],
            "rocks": [list(p) for p in st["rocks"]],
            "golds": [list(p) for p in st["golds"]],
            "walls": sorted(st["walls"].keys()),
        })
        if st["over"]:
            break
    res = result_race(st)
    res.update({"v": 1, "hash": state_hash_race(st), "seed": seed, "mode": "race"})
    save_memory(name_a, new_a)
    save_memory(name_b, new_b)
    if out_path:
        p = pathlib.Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            for row in replay:
                f.write(json.dumps(row) + "\n")
        with open(str(p) + ".result.json", "w") as f:
            json.dump(res, f, indent=2)
    return res, replay


if __name__ == "__main__":
    import time
    sys.path.insert(0, str(ROOT / "bots"))
    import racer_bot
    t0 = time.time()
    res, _ = run_race(racer_bot.decide, racer_bot.decide, 5, out_path="matches/race-5/replay.jsonl")
    print(f"race: winner={res['winner']} tick={res['tick']} time={time.time()-t0:.1f}s")
