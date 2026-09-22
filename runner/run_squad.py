"""Runner squadre S2 — 6 decide parallele, memoria condivisa per team, replay v2."""
from __future__ import annotations
import json
import sys
import pathlib
import concurrent.futures as cf

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim.squad import new_match_squad, step_squad, to_obs_squad, result_squad, state_hash_squad
from sim.sim import VALID_ACTIONS, clean_message
from runner.run import safe_decide, load_memory, save_memory


def run_squad_match(decide_a, decide_b, seed: int, out_path: str | None = None,
                    name_a: str = "sq1", name_b: str = "sq2"):
    st = new_match_squad(seed)
    mem_a, mem_b = load_memory(name_a), load_memory(name_b)
    new_a, new_b = mem_a, mem_b
    replay = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for _ in range(300):
            if st["over"]:
                break
            obs = [to_obs_squad(st, i) for i in range(6)]
            for i in range(3):
                obs[i]["memory"] = mem_a
            for i in range(3, 6):
                obs[i]["memory"] = mem_b
            futs = [ex.submit(safe_decide, decide_a if i < 3 else decide_b, obs[i]) for i in range(6)]
            acts = []
            for i, f in enumerate(futs):
                a, s = f.result(timeout=5)
                if isinstance(a.get("memory"), dict):
                    if i < 3:
                        new_a = a["memory"]
                    else:
                        new_b = a["memory"]
                acts.append(a)
            step_squad(st, acts)
            u = st["units"]
            row = {
                "v": 2, "tick": st["tick"],
                "t1": [{"x": z["x"], "y": z["y"], "hp": z["hp"], "wood": z["wood"],
                        "stone": z["stone"], "gold": z["gold"], "sword": z["has_sword"]} for z in u[:3]],
                "t2": [{"x": z["x"], "y": z["y"], "hp": z["hp"], "wood": z["wood"],
                        "stone": z["stone"], "gold": z["gold"], "sword": z["has_sword"]} for z in u[3:]],
                # legacy capitani per viewer vecchi
                "p1": {"x": u[0]["x"], "y": u[0]["y"], "hp": u[0]["hp"], "wood": u[0]["wood"],
                       "stone": u[0]["stone"], "gold": u[0]["gold"], "sword": u[0]["has_sword"]},
                "p2": {"x": u[3]["x"], "y": u[3]["y"], "hp": u[3]["hp"], "wood": u[3]["wood"],
                       "stone": u[3]["stone"], "gold": u[3]["gold"], "sword": u[3]["has_sword"]},
                "a1": acts[0]["action"], "a2": acts[3]["action"],
                "m1": st["messages"][0], "m2": st["messages"][1],
                "trees": [list(p) for p in st["trees"]],
                "rocks": [list(p) for p in st["rocks"]],
                "golds": [list(p) for p in st["golds"]],
                "walls": sorted(st["walls"].keys()),
            }
            replay.append(row)
            if st["over"]:
                break
    res = result_squad(st)
    res.update({"v": 2, "hash": state_hash_squad(st), "seed": seed, "mode": "squad"})
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
    import squad_bot
    t0 = time.time()
    res, _ = run_squad_match(squad_bot.decide, squad_bot.decide, int(sys.argv[1]) if len(sys.argv) > 1 else 3,
                             out_path="matches/squad-3/replay.jsonl", name_a="sqA", name_b="sqB")
    print(f"squad seed=3 winner={res['winner']} {res['s0']}-{res['s1']} hash={res['hash']} time={time.time()-t0:.1f}s")
