"""Runner stagioni S3 — decide parallele, snapshot ogni 100 tick, delta.jsonl leggero."""
from __future__ import annotations
import json
import sys
import time
import pathlib
import concurrent.futures as cf

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim.world import new_world, step_world, obs_world, score_world, territory, world_hash, SNAP_EVERY, MAX_TICKS
from sim.sim import VALID_ACTIONS, clean_message
from runner.run import safe_decide, load_memory, save_memory


def run_season(decides: dict[str, object], seed: int, title: str = "season",
               out_dir: str | None = None, max_ticks: int = MAX_TICKS):
    names = sorted(decides)
    st = new_world(seed, names)
    mems = {n: load_memory(n) for n in names}
    new_mems = dict(mems)
    snap_dir = pathlib.Path(out_dir) if out_dir else None
    if snap_dir:
        snap_dir.mkdir(parents=True, exist_ok=True)
    delta = []
    prev = {n: {"x": a["x"], "y": a["y"], "hp": a["hp"], "alive": a["alive"]} for n, a in st["agents"].items()}
    with cf.ThreadPoolExecutor(max_workers=min(8, len(names))) as ex:
        while not st["over"] and st["tick"] < max_ticks:
            obs = {}
            for n in names:
                o = obs_world(st, n)
                o["memory"] = mems[n]
                obs[n] = o
            futs = {n: ex.submit(safe_decide, decides[n], obs[n]) for n in names}
            acts = {}
            for n, f in futs.items():
                a, s = f.result(timeout=10)
                if isinstance(a.get("memory"), dict):
                    new_mems[n] = a["memory"]
                acts[n] = a
            step_world(st, acts)
            # delta: solo agenti cambiati
            moved, dead, resp = {}, [], []
            for n, a in st["agents"].items():
                p = prev[n]
                if not a["alive"] and p["alive"]:
                    dead.append(n)
                elif a["alive"] and not p["alive"]:
                    resp.append([n, a["x"], a["y"]])
                elif a["alive"] and (a["x"], a["y"], a["hp"]) != (p["x"], p["y"], p["hp"]):
                    moved[n] = [a["x"], a["y"], a["hp"]]
                prev[n] = {"x": a["x"], "y": a["y"], "hp": a["hp"], "alive": a["alive"]}
            msgs = {n: t for n, t in st["messages"].items() if t}
            if moved or dead or resp or msgs or st["tick"] % SNAP_EVERY == 0:
                delta.append({"tick": st["tick"], "moved": moved, "dead": dead,
                              "respawned": resp, "msgs": msgs})
            if snap_dir and (st["tick"] % SNAP_EVERY == 0 or st["over"]):
                (snap_dir / f"snap-{st['tick']}.json").write_text(json.dumps({
                    "tick": st["tick"], "agents": st["agents"],
                    "trees": st["trees"], "rocks": st["rocks"], "golds": st["golds"],
                    "territory": territory(st)}))
            if st["over"]:
                break
    standings = sorted(((n, score_world(st, n)) for n in names), key=lambda kv: -kv[1])
    report = {"v": 1, "mode": "world", "title": title, "seed": seed,
              "tick": st["tick"], "hash": world_hash(st),
              "standings": [{"name": n, "score": s} for n, s in standings],
              "champion": standings[0][0], "territory": territory(st)}
    if snap_dir:
        (snap_dir / "delta.jsonl").write_text("\n".join(json.dumps(d) for d in delta) + "\n")
        (snap_dir / "season.json").write_text(json.dumps(report, indent=2))
    for n in names:
        save_memory(n, new_mems[n])
    return report, delta


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "bots"))
    import greedy_bot
    names = [f"w-bot{i}" for i in range(12)]
    t0 = time.time()
    rep, delta = run_season({n: greedy_bot.decide for n in names}, 77,
                            out_dir="matches/world-s1")
    print(f"stagione: campione={rep['champion']} score={rep['standings'][0]['score']} "
          f"tick={rep['tick']} delta_righe={len(delta)} time={time.time()-t0:.1f}s")
