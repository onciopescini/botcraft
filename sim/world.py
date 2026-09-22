"""Mondo persistente FFA Botcraft S3 — OBS compatibile 1v1, bot esistenti invariati."""
from __future__ import annotations
import random
import hashlib
import json
import sim.sim as base

WORLD_W, WORLD_H = 64, 64
VIEW_RADIUS = 7
MAX_TICKS = 500
SNAP_EVERY = 100
RESPAWN_AGENT = 50
TOTEM = (32, 32)


def _mk(x, y):
    return {"x": x, "y": y, "hp": 100, "wood": 0, "stone": 0, "gold": 0,
            "sticks": 0, "has_sword": False, "walls_left": 5, "alive": True,
            "noop_streak": 0, "timeouts": 0, "illegal": 0, "kills": 0, "dead_at": -1}


def new_world(seed: int, names: list[str], w: int = WORLD_W, h: int = WORLD_H) -> dict:
    rng = random.Random(seed)
    occ = {TOTEM}
    trees, rocks, golds = [], [], []
    for lst, n in ((trees, w), (rocks, w // 2), (golds, w // 4)):
        while len(lst) < n:
            p = (rng.randrange(w), rng.randrange(h))
            if p not in occ:
                occ.add(p)
                lst.append(p)
    agents = {}
    for i, n in enumerate(names):
        for _ in range(200):
            p = (rng.randrange(w), rng.randrange(h))
            if p not in occ:
                occ.add(p)
                break
        a = _mk(*p)
        a["spawn"] = list(p)
        agents[n] = a
    return {"seed": seed, "tick": 0, "w": w, "h": h, "counter": 0,
            "agents": agents, "trees": trees, "rocks": rocks, "golds": golds,
            "pending": [], "messages": {}, "walls": {}, "events": {n: [] for n in names},
            "over": False}


def _blocked(st, x, y):
    if not (0 <= x < st["w"] and 0 <= y < st["h"]):
        return True
    if f"{x},{y}" in st["walls"] or (x, y) in st["trees"] or (x, y) in st["rocks"] or (x, y) in st["golds"]:
        return True
    return (x, y) == TOTEM


def _ev(st, n, msg):
    ev = st["events"][n]
    ev.append(msg)
    if len(ev) > 5:
        del ev[0]


def _free(st, rng):
    for _ in range(40):
        p = (rng.randrange(st["w"]), rng.randrange(st["h"]))
        if p == TOTEM or f"{p[0]},{p[1]}" in st["walls"]:
            continue
        if p in st["trees"] or p in st["rocks"] or p in st["golds"]:
            continue
        if any(a["alive"] and (a["x"], a["y"]) == p for a in st["agents"].values()):
            continue
        return p
    return None


def step_world(st, acts: dict) -> dict:
    if st["over"]:
        return st
    st["tick"] += 1
    for k in [k for k, exp in st["walls"].items() if exp <= st["tick"]]:
        del st["walls"][k]
    # respawn risorse
    due = [r for r in st["pending"] if r[0] <= st["tick"]]
    st["pending"] = [r for r in st["pending"] if r[0] > st["tick"]]
    caps = {"tree": st["w"], "rock": st["w"] // 2, "gold": st["w"] // 4}
    lists = {"tree": st["trees"], "rock": st["rocks"], "gold": st["golds"]}
    for _, typ in due:
        if len(lists[typ]) >= caps[typ] or st["tick"] >= MAX_TICKS - 20:
            continue
        st["counter"] += 1
        p = _free(st, random.Random(f"{st['seed']}:{st['tick']}:{st['counter']}"))
        if p:
            lists[typ].append(p)
    # respawn agenti
    for a in st["agents"].values():
        if not a["alive"] and st["tick"] - a["dead_at"] >= RESPAWN_AGENT:
            a.update(x=a["spawn"][0], y=a["spawn"][1], hp=100, alive=True, noop_streak=0)
    order = sorted(st["agents"])
    for n in order:
        me = st["agents"][n]
        if not me["alive"]:
            continue
        act = acts.get(n, {"action": "noop"})
        raw = act.get("action", "noop") if isinstance(act, dict) else "noop"
        if raw not in base.VALID_ACTIONS:
            me["illegal"] += 1
            me["noop_streak"] += 1
            continue
        if raw.startswith("move_"):
            dx, dy = base.DIRS[raw]
            nx, ny = me["x"] + dx, me["y"] + dy
            occ = {(a["x"], a["y"]) for k, a in st["agents"].items() if a["alive"] and k != n}
            if _blocked(st, nx, ny) or (nx, ny) in occ:
                me["noop_streak"] += 1
            else:
                me["x"], me["y"] = nx, ny
                me["noop_streak"] = 0
        elif raw == "noop":
            me["noop_streak"] += 1
        elif raw == "gather":
            hit = False
            for lst, res, typ in ((st["trees"], "wood", "tree"), (st["rocks"], "stone", "rock"), (st["golds"], "gold", "gold")):
                for p in lst:
                    if abs(me["x"] - p[0]) + abs(me["y"] - p[1]) == 1:
                        lst.remove(p)
                        me[res] += 1
                        me["noop_streak"] = 0
                        _ev(st, n, f"gather_ok {res}")
                        st["pending"].append([st["tick"] + 20, typ])
                        hit = True
                        break
                if hit:
                    break
            if not hit:
                me["noop_streak"] += 1
        elif raw == "craft_sword":
            if not me["has_sword"] and me["wood"] >= 3 and me["stone"] >= 2:
                me["wood"] -= 3
                me["stone"] -= 2
                me["has_sword"] = True
                me["noop_streak"] = 0
            else:
                me["noop_streak"] += 1
        elif raw == "craft_wall_kit":
            if me["walls_left"] < 20 and me["stone"] >= 2:
                me["stone"] -= 2
                me["walls_left"] += 1
                me["noop_streak"] = 0
            else:
                me["noop_streak"] += 1
        elif raw == "place_wall":
            d = act.get("dir", "E") if isinstance(act, dict) else "E"
            dx, dy = base.DIRS.get(d, (1, 0))
            nx, ny = me["x"] + dx, me["y"] + dy
            occ = {(a["x"], a["y"]) for k, a in st["agents"].items() if a["alive"] and k != n}
            if me["walls_left"] > 0 and len(st["walls"]) < 80 and 0 <= nx < st["w"] and 0 <= ny < st["h"] and f"{nx},{ny}" not in st["walls"] and (nx, ny) not in st["trees"] and (nx, ny) not in st["rocks"] and (nx, ny) not in st["golds"] and (nx, ny) != TOTEM and (nx, ny) not in occ:
                me["walls_left"] -= 1
                st["walls"][f"{nx},{ny}"] = st["tick"] + base.WALL_DURATION
                me["noop_streak"] = 0
            else:
                me["noop_streak"] += 1
        elif raw == "attack":
            dmg = 20 if me["has_sword"] else 10
            target = None
            for k in order:
                if k == n:
                    continue
                f = st["agents"][k]
                if f["alive"] and abs(me["x"] - f["x"]) + abs(me["y"] - f["y"]) == 1:
                    target = (k, f)
                    break
            if target:
                k, f = target
                f["hp"] -= dmg
                me["noop_streak"] = 0
                _ev(st, n, f"hit {k} {dmg}")
                if f["hp"] <= 0:
                    f["hp"] = 0
                    f["alive"] = False
                    f["dead_at"] = st["tick"]
                    me["kills"] += 1
            else:
                me["noop_streak"] += 1
        elif raw == "message":
            txt = base.clean_message(act.get("text", "") if isinstance(act, dict) else "")
            if txt:
                st["messages"][n] = txt
                me["noop_streak"] = 0
            else:
                me["noop_streak"] += 1
        elif raw == "craft_stick":
            if me["wood"] >= 2:
                me["wood"] -= 2
                me["sticks"] += 1
                me["noop_streak"] = 0
            else:
                me["noop_streak"] += 1
    for a in st["agents"].values():
        if a["alive"] and a["noop_streak"] >= 3:
            a["hp"] -= 5
            a["noop_streak"] = 0
            if a["hp"] <= 0:
                a["hp"] = 0
                a["alive"] = False
                a["dead_at"] = st["tick"]
    if st["tick"] >= MAX_TICKS:
        st["over"] = True
    return st


def obs_world(st, name: str) -> dict:
    me = st["agents"][name]
    best, bd = None, 99
    for k, a in st["agents"].items():
        if k == name or not a["alive"]:
            continue
        d = abs(me["x"] - a["x"]) + abs(me["y"] - a["y"])
        if d < bd:
            bd, best = d, (k, a)
    visible = best is not None and bd <= VIEW_RADIUS
    nearby = []
    for t in st["trees"]:
        d = abs(me["x"] - t[0]) + abs(me["y"] - t[1])
        if d <= VIEW_RADIUS:
            nearby.append({"type": "tree", "x": t[0], "y": t[1], "dist": d})
    for r in st["rocks"]:
        d = abs(me["x"] - r[0]) + abs(me["y"] - r[1])
        if d <= VIEW_RADIUS:
            nearby.append({"type": "rock", "x": r[0], "y": r[1], "dist": d})
    for g in st["golds"]:
        d = abs(me["x"] - g[0]) + abs(me["y"] - g[1])
        if d <= VIEW_RADIUS:
            nearby.append({"type": "gold", "x": g[0], "y": g[1], "dist": d})
    nearby.sort(key=lambda e: e["dist"])
    msg = ""
    if visible:
        for k, txt in st["messages"].items():
            if k != name:
                a = st["agents"][k]
                if abs(me["x"] - a["x"]) + abs(me["y"] - a["y"]) <= VIEW_RADIUS:
                    msg = txt
                    break
    return {
        "tick": st["tick"], "seed": st["seed"], "mode": "world", "name": name,
        "unit": 0, "agents_alive": sum(1 for a in st["agents"].values() if a["alive"]),
        "self": {"x": me["x"], "y": me["y"], "hp": me["hp"], "wood": me["wood"],
                 "stone": me["stone"], "gold": me["gold"], "has_sword": me["has_sword"],
                 "walls_left": me["walls_left"]},
        "enemy": {"visible": visible, "x": best[1]["x"] if visible else -1,
                  "y": best[1]["y"] if visible else -1, "hp": best[1]["hp"] if visible else -1},
        "enemy_message": msg, "my_last_message": st["messages"].get(name, ""),
        "nearby": nearby[:5], "events": list(st["events"][name][-5:]),
        "budget": {"ticks_left": MAX_TICKS - st["tick"], "timeouts_so_far": me["timeouts"]},
    }


def score_world(st, name: str) -> int:
    me = st["agents"][name]
    s = me["wood"] + me["stone"] + me["gold"] * 3 + me["kills"] * 10
    if abs(me["x"] - TOTEM[0]) + abs(me["y"] - TOTEM[1]) == 1:
        s += 15
    return s


def territory(st) -> dict:
    quads = {"NW": [], "NE": [], "SW": [], "SE": []}
    for n, a in st["agents"].items():
        if not a["alive"]:
            continue
        q = ("N" if a["y"] < st["h"] // 2 else "S") + ("W" if a["x"] < st["w"] // 2 else "E")
        quads[q].append(n)
    return {q: (sorted(v)[0] if len(set(v)) == 1 and v else (max(set(v), key=v.count) if v else None)) for q, v in quads.items()}


def world_hash(st) -> str:
    payload = json.dumps({"tick": st["tick"], "agents": st["agents"],
                          "trees": sorted(st["trees"]), "rocks": sorted(st["rocks"]),
                          "golds": sorted(st["golds"])}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
