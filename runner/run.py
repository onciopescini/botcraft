"""Runner locale Botcraft S1 — timeout, memoria 10KB, replay con gold/messaggi."""
from __future__ import annotations
import json
import sys
import time
import pathlib
import concurrent.futures as cf

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from sim.sim import new_match, step, to_obs, result, state_hash, VALID_ACTIONS, clean_message

TIMEOUT_S = 0.6
MEM_DIR = pathlib.Path(__file__).resolve().parents[1] / "backend" / "memory"
MEM_LIMIT = 10 * 1024


def load_memory(name: str) -> dict:
    p = MEM_DIR / f"{name}.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text()[:MEM_LIMIT])
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_memory(name: str, mem: dict):
    if not isinstance(mem, dict):
        return
    MEM_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(mem)[:MEM_LIMIT]
    (MEM_DIR / f"{name}.json").write_text(raw)


def safe_decide(fn, obs):
    with cf.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn, obs)
        try:
            out = fut.result(timeout=TIMEOUT_S)
        except cf.TimeoutError:
            return {"action": "noop"}, "timeout"
        except Exception as e:
            return {"action": "noop"}, f"exception:{type(e).__name__}"
    if not isinstance(out, dict) or out.get("action") not in VALID_ACTIONS:
        return {"action": "noop"}, f"illegal:{out}"
    if out["action"] == "place_wall" and out.get("dir") not in ("N", "S", "E", "W"):
        return {"action": "noop"}, "illegal:dir"
    if out["action"] == "message":
        txt = clean_message(out.get("text", ""))
        if not txt:
            return {"action": "noop"}, "illegal:message_empty"
        out["text"] = txt
    return out, "ok"


def run_match(decide_a, decide_b, seed: int, out_path: str | None = None,
              name_a: str = "p1", name_b: str = "p2"):
    state = new_match(seed)
    mem_a, mem_b = load_memory(name_a), load_memory(name_b)
    new_mem_a, new_mem_b = mem_a, mem_b
    replay = []
    with cf.ThreadPoolExecutor(max_workers=2) as _:
        pass  # warmup threads su Windows
    for _ in range(300):
        if state["over"]:
            break
        obs_a, obs_b = to_obs(state, 0), to_obs(state, 1)
        obs_a["memory"], obs_b["memory"] = mem_a, mem_b
        a1, s1 = safe_decide(decide_a, obs_a)
        a2, s2 = safe_decide(decide_b, obs_b)
        if isinstance(a1, dict) and isinstance(a1.get("memory"), dict):
            new_mem_a = a1["memory"]
        if isinstance(a2, dict) and isinstance(a2.get("memory"), dict):
            new_mem_b = a2["memory"]
        # conta timeout come da spec budget
        if s1 == "timeout":
            state["agents"][0]["timeouts"] += 1
        if s2 == "timeout":
            state["agents"][1]["timeouts"] += 1
        step(state, a1, a2)
        replay.append({
            "v": 1,
            "tick": state["tick"],
            "p1": {"x": state["agents"][0]["x"], "y": state["agents"][0]["y"],
                   "hp": state["agents"][0]["hp"], "wood": state["agents"][0]["wood"],
                   "stone": state["agents"][0]["stone"], "gold": state["agents"][0].get("gold", 0),
                   "sword": state["agents"][0]["has_sword"]},
            "p2": {"x": state["agents"][1]["x"], "y": state["agents"][1]["y"],
                   "hp": state["agents"][1]["hp"], "wood": state["agents"][1]["wood"],
                   "stone": state["agents"][1]["stone"], "gold": state["agents"][1].get("gold", 0),
                   "sword": state["agents"][1]["has_sword"]},
            "a1": a1["action"], "a2": a2["action"],
            "m1": state["messages"][0], "m2": state["messages"][1],
            "s1": s1, "s2": s2,
            "trees": [list(p) for p in state["trees"]],
            "rocks": [list(p) for p in state["rocks"]],
            "golds": [list(p) for p in state.get("golds", [])],
            "walls": sorted(state["walls"].keys()),
        })
        if state["over"]:
            break
    res = result(state)
    res["v"] = 1
    res["hash"] = state_hash(state)
    res["seed"] = seed
    if state["over"] or state["tick"] >= 300:
        save_memory(name_a, new_mem_a)
        save_memory(name_b, new_mem_b)
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
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bots"))
    import random_bot
    import greedy_bot
    t0 = time.time()
    res, _ = run_match(random_bot.decide, greedy_bot.decide, seed,
                       out_path=f"matches/{seed}/replay.jsonl")
    print(f"seed={seed} winner={res['winner']} s0={res['s0']} s1={res['s1']} hash={res['hash']} time={time.time()-t0:.1f}s")
