"""Corsa al totem Botcraft — primo adiacente vince. Meccaniche da engine, stato proprio.

Regole: 150 tick max. Kill senza punti, vittima respawn allo spawn dopo 10 tick.
Muri per sabotare (cap 40). Gold = tiebreak. Niente spade? No: spada ammessa
per farsi largo, ma non dà punti. Arrivo = adiacenza al totem.
"""
from __future__ import annotations
import random
import hashlib
import json
from sim import engine as E

from sim.sim import _mk_agent
RACE_TICKS = 150


def _mk(x, y, loadout: dict | None = None):
    a = _mk_agent((x, y), loadout)
    a["respawn_at"] = -1
    return a


def new_race(seed: int, loadout_a: dict | None = None, loadout_b: dict | None = None) -> dict:
    rng = random.Random(seed)
    spawns = [(2, 2), (29, 29)]
    if rng.random() < 0.5:
        spawns = spawns[::-1]
    occupied = set(spawns) | {E.TOTEM}
    trees, rocks, golds = [], [], []
    for lst, n in ((trees, 30), (rocks, 15), (golds, 12)):
        while len(lst) < n:
            p = (rng.randrange(E.W), rng.randrange(E.H))
            if p not in occupied:
                occupied.add(p)
                lst.append(p)
    return {"seed": seed, "tick": 0, "max_ticks": RACE_TICKS, "mode": "race",
            "respawn_counter": 0, "mutator": "", "spawns": spawns,
            "agents": [_mk(*spawns[0], loadout_a), _mk(*spawns[1], loadout_b)],
            "trees": trees, "rocks": rocks, "golds": golds,
            "pending_respawns": [], "messages": ["", ""], "coach": [[], []],
            "walls": {}, "events": [[], []], "winner": None, "over": False}


def _ev(st, pid, msg):
    ev = st["events"][pid]
    ev.append(msg)
    if len(ev) > 5:
        del ev[0]


def _apply(st, pid, action: dict):
    me = st["agents"][pid]
    foe = st["agents"][1 - pid]
    if not me["alive"]:
        return
    raw = action.get("action", "noop") if isinstance(action, dict) else "noop"
    if raw not in E.VALID_ACTIONS:
        me["illegal"] += 1
        me["noop_streak"] += 1
        _ev(st, pid, f"illegal:{raw}")
        return
    if raw.startswith("move_"):
        dx, dy = E.DIRS[raw]
        nx, ny = me["x"] + dx, me["y"] + dy
        other = (foe["x"], foe["y"]) if foe["alive"] else None
        if E.blocked(st, nx, ny) or (nx, ny) == other:
            _ev(st, pid, "bump")
            me["noop_streak"] += 1
        else:
            me["x"], me["y"] = nx, ny
            me["noop_streak"] = 0
        return
    if raw == "noop":
        me["noop_streak"] += 1
        return
    if raw == "gather":
        E.gather(st, me, lambda m: _ev(st, pid, m))
        return
    if raw == "message":
        txt = E.clean_message(action.get("text", "") if isinstance(action, dict) else "")
        if not txt:
            me["noop_streak"] += 1
            return
        st["messages"][pid] = txt
        me["noop_streak"] = 0
        _ev(st, pid, f"msg:{txt}")
        return
    if raw == "craft_stick":
        E.craft(me, "stick", lambda m: _ev(st, pid, m))
        return
    if raw == "craft_sword":
        E.craft(me, "sword", lambda m: _ev(st, pid, m))
        return
    if raw == "craft_wall_kit":
        E.craft(me, "wall", lambda m: _ev(st, pid, m))
        return
    if raw == "place_wall":
        d = action.get("dir", "E") if isinstance(action, dict) else "E"
        if d not in E.DIRS:
            me["illegal"] += 1
            me["noop_streak"] += 1
            return
        dx, dy = E.DIRS[d]
        other = (foe["x"], foe["y"]) if foe["alive"] else None
        E.place_wall(st, me, me["x"] + dx, me["y"] + dy, {other} if other else set())
        return
    if raw == "dash":
        d = action.get("dir", "E") if isinstance(action, dict) else "E"
        other = (foe["x"], foe["y"]) if foe["alive"] else None
        E.do_dash(st, me, d, {other} if other else set(), lambda m: _ev(st, pid, m))
        return
    if raw == "shield":
        E.do_shield(me, lambda m: _ev(st, pid, m))
        return
    if raw == "attack":
        if foe["alive"] and E.manhattan((me["x"], me["y"]), (foe["x"], foe["y"])) == 1:
            dmg = E.shielded_damage(foe, 20 if me["has_sword"] else 10)
            foe["hp"] -= dmg
            me["noop_streak"] = 0
            _ev(st, pid, f"hit_dealt {dmg}")
            if foe["hp"] <= 0:
                foe["hp"] = 0
                foe["alive"] = False
                foe["respawn_at"] = st["tick"] + 10
                me["kills"] += 1
                _ev(st, pid, "kill (no punti, solo strada libera)")
        else:
            _ev(st, pid, "attack_miss")
            me["noop_streak"] += 1
        return


def step_race(st, a1: dict, a2: dict) -> dict:
    if st["over"]:
        return st
    st["tick"] += 1
    for k in [k for k, exp in st["walls"].items() if exp <= st["tick"]]:
        del st["walls"][k]
    alive_pos = {(a["x"], a["y"]) for a in st["agents"] if a["alive"]}
    E.process_respawns(st, alive_pos)
    for n, a in enumerate(st["agents"]):
        if not a["alive"] and st["tick"] >= a["respawn_at"] >= 0:
            sx, sy = st["spawns"][n]
            a.update(x=sx, y=sy, hp=100, alive=True, noop_streak=0, respawn_at=-1)
    _apply(st, 0, a1)
    _apply(st, 1, a2)
    for pid in (0, 1):
        E.bleed(st["agents"][pid], lambda m, p=pid: _ev(st, p, m))
        E.tick_timers(st["agents"][pid])
    # arrivo: primo adiacente al totem
    for pid in (0, 1):
        me = st["agents"][pid]
        if me["alive"] and E.manhattan((me["x"], me["y"]), E.TOTEM) == 1:
            st["winner"] = pid
            st["over"] = True
            _ev(st, pid, "ARRIVO!")
            return st
    if st["tick"] >= st["max_ticks"]:
        st["over"] = True
    return st


def to_obs_race(st, pid: int) -> dict:
    me = st["agents"][pid]
    foe = st["agents"][1 - pid]
    dist_foe = E.manhattan((me["x"], me["y"]), (foe["x"], foe["y"]))
    visible = dist_foe <= E.VIEW_RADIUS and foe["alive"]
    nearby = []
    for t in st["trees"]:
        d = E.manhattan((me["x"], me["y"]), t)
        if d <= E.VIEW_RADIUS:
            nearby.append({"type": "tree", "x": t[0], "y": t[1], "dist": d})
    for r in st["rocks"]:
        d = E.manhattan((me["x"], me["y"]), r)
        if d <= E.VIEW_RADIUS:
            nearby.append({"type": "rock", "x": r[0], "y": r[1], "dist": d})
    for g in st["golds"]:
        d = E.manhattan((me["x"], me["y"]), g)
        if d <= E.VIEW_RADIUS:
            nearby.append({"type": "gold", "x": g[0], "y": g[1], "dist": d})
    nearby.sort(key=lambda e: e["dist"])
    return {
        "tick": st["tick"], "seed": st["seed"], "mode": "race", "unit": 0,
        "self": {"x": me["x"], "y": me["y"], "hp": me["hp"], "wood": me["wood"],
                 "stone": me["stone"], "gold": me["gold"], "has_sword": me["has_sword"],
                 "walls_left": me["walls_left"], "dash_cd": me["dash_cd"], "shield": me["shield"]},
        "enemy": {"visible": visible, "x": foe["x"] if visible else -1,
                  "y": foe["y"] if visible else -1, "hp": foe["hp"] if visible else -1},
        "enemy_message": "", "my_last_message": st["messages"][pid],
        "coach": next((c for c in reversed(st["coach"][pid]) if st["tick"] >= c["tick"]), None),
        "totem": [16, 16],
        "nearby": nearby[:5],
        "events": list(st["events"][pid][-5:]),
        "budget": {"ticks_left": st["max_ticks"] - st["tick"], "timeouts_so_far": me["timeouts"]},
    }


def result_race(st) -> dict:
    if st["winner"] is not None:
        w = st["winner"]
    else:
        d0 = E.manhattan((st["agents"][0]["x"], st["agents"][0]["y"]), E.TOTEM)
        d1 = E.manhattan((st["agents"][1]["x"], st["agents"][1]["y"]), E.TOTEM)
        if d0 != d1:
            w = 0 if d0 < d1 else 1
        elif st["agents"][0]["gold"] != st["agents"][1]["gold"]:
            w = 0 if st["agents"][0]["gold"] > st["agents"][1]["gold"] else 1
        else:
            w = -1
    return {"s0": 0, "s1": 0, "winner": w, "tick": st["tick"], "arrival": st["winner"] is not None}


def state_hash_race(st) -> str:
    payload = json.dumps({
        "tick": st["tick"],
        "agents": [{k: v for k, v in a.items()} for a in st["agents"]],
        "trees": sorted(st["trees"]), "rocks": sorted(st["rocks"]),
        "golds": sorted(st["golds"]), "walls": sorted(st["walls"].items()),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
