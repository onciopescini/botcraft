"""Squad 3v3 Botcraft S2 — meccaniche in sim/engine.py, stato separato a 6 unità."""
from __future__ import annotations
import random
import hashlib
import json
import sim.sim as base
from sim import engine as _e

W, H, VIEW_RADIUS, WALL_DURATION, TOTEM, MAX_TICKS = (
    base.W, base.H, base.VIEW_RADIUS, base.WALL_DURATION, base.TOTEM, base.MAX_TICKS)
VALID_ACTIONS = base.VALID_ACTIONS


def _mk(x, y):
    return {"x": x, "y": y, "hp": 100, "wood": 0, "stone": 0, "gold": 0,
            "sticks": 0, "has_sword": False, "walls_left": 5,
            "dash_cd": 0, "shield": 0,
            "alive": True, "noop_streak": 0, "timeouts": 0, "illegal": 0, "kills": 0}


def new_match_squad(seed: int) -> dict:
    s1 = base.new_match(seed)
    spawns_a = [(2, 2), (3, 2), (2, 3)]
    spawns_b = [(29, 29), (28, 29), (29, 28)]
    if random.Random(seed).random() < 0.5:
        spawns_a, spawns_b = spawns_b, spawns_a
    return {
        "seed": seed, "tick": 0, "mode": "squad", "respawn_counter": 0,
        "units": [_mk(*spawns_a[0]), _mk(*spawns_a[1]), _mk(*spawns_a[2]),
                  _mk(*spawns_b[0]), _mk(*spawns_b[1]), _mk(*spawns_b[2])],
        "trees": s1["trees"], "rocks": s1["rocks"], "golds": s1["golds"],
        "pending_respawns": [], "messages": ["", ""], "walls": {},
        "action_clock": 0,
        "events": [[], [], [], [], [], []], "over": False,
    }


def _alive_pos(st, skip=-1):
    return {(u["x"], u["y"]) for i, u in enumerate(st["units"]) if u["alive"] and i != skip}


def _process_respawns_squad(st):
    alive = {(u["x"], u["y"]) for u in st["units"] if u["alive"]}
    _e.process_respawns(st, alive)


def _schedule_squad(st, typ: str):
    _e.schedule_respawn(st, typ)


def _apply_unit(st, idx, action):
    me = st["units"][idx]
    if not me["alive"]:
        return
    team = 0 if idx < 3 else 1
    foes = range(3, 6) if team == 0 else range(0, 3)
    raw = action.get("action", "noop") if isinstance(action, dict) else "noop"
    if raw not in VALID_ACTIONS:
        me["illegal"] += 1
        me["noop_streak"] += 1
        base._push_event(st, idx, f"illegal:{raw}")
        return
    if raw.startswith("move_"):
        dx, dy = base.DIRS[raw]
        nx, ny = me["x"] + dx, me["y"] + dy
        if base._blocked(st, nx, ny) or (nx, ny) in _alive_pos(st, idx):
            base._push_event(st, idx, "bump")
            me["noop_streak"] += 1
        else:
            me["x"], me["y"] = nx, ny
            me["noop_streak"] = 0
        return
    if raw == "noop":
        me["noop_streak"] += 1
        return
    if raw == "gather":
        _e.gather(st, me, lambda m: base._push_event(st, idx, m))
        return
    if raw == "craft_sword":
        _e.craft(me, "sword", lambda m: base._push_event(st, idx, m))
        return
    if raw == "craft_stick":
        _e.craft(me, "stick", lambda m: base._push_event(st, idx, m))
        return
    if raw == "craft_wall_kit":
        # squad resta silenziosa sui fail (solo craft_ok)
        _e.craft(me, "wall", lambda m: base._push_event(st, idx, m) if m.startswith("craft_ok") else None)
        return
    if raw == "place_wall":
        d = action.get("dir", "E") if isinstance(action, dict) else "E"
        if d not in base.DIRS:
            me["noop_streak"] += 1
            return
        dx, dy = base.DIRS[d]
        _e.place_wall(st, me, me["x"] + dx, me["y"] + dy, _alive_pos(st, idx))
        return
    if raw == "attack":
        for f in foes:
            foe = st["units"][f]
            if foe["alive"] and base._manhattan((me["x"], me["y"]), (foe["x"], foe["y"])) == 1:
                dmg = _e.shielded_damage(foe, 20 if me["has_sword"] else 10)
                foe["hp"] -= dmg
                me["noop_streak"] = 0
                base._push_event(st, idx, f"hit_dealt {dmg}")
                if foe["hp"] <= 0:
                    foe["hp"] = 0
                    foe["alive"] = False
                    me["kills"] += 1
                    base._push_event(st, idx, "kill")
                return
        base._push_event(st, idx, "attack_miss")
        me["noop_streak"] += 1
        return
    if raw == "dash":
        d = action.get("dir", "E") if isinstance(action, dict) else "E"
        if d not in base.DIRS:
            me["noop_streak"] += 1
            return
        dx, dy = base.DIRS[d]
        _e.do_dash(st, me, d, _alive_pos(st, idx), lambda m: base._push_event(st, idx, m))
        return
    if raw == "shield":
        _e.do_shield(me, lambda m: base._push_event(st, idx, m) if m.startswith("shield_o") else None)
        return
        base._push_event(st, idx, "attack_miss")
        me["noop_streak"] += 1
        return
    if raw == "message":
        txt = base.clean_message(action.get("text", "") if isinstance(action, dict) else "")
        if not txt:
            me["noop_streak"] += 1
            return
        st["messages"][team] = txt
        me["noop_streak"] = 0
        base._push_event(st, idx, f"msg:{txt}")
        return


def step_squad(st, acts: list) -> dict:
    if st["over"]:
        return st
    st["tick"] += 1
    expired = [k for k, exp in st["walls"].items() if exp <= st["tick"]]
    for k in expired:
        del st["walls"][k]
    _process_respawns_squad(st)
    snap = [(u["kills"], u["wood"], u["stone"], u["gold"], u["has_sword"]) for u in st["units"]]
    for idx in range(6):
        _apply_unit(st, idx, acts[idx] if idx < len(acts) else {"action": "noop"})
    now = [(u["kills"], u["wood"], u["stone"], u["gold"], u["has_sword"]) for u in st["units"]]
    st["action_clock"] = 0 if now != snap else st["action_clock"] + 1
    if st["action_clock"] >= 100:
        st["over"] = True
    for u in st["units"]:
        _e.bleed(u, lambda m: None)  # squad: bleed silenzioso
    for u in st["units"]:
        _e.tick_timers(u)
    # sudden death condivisa (silenziosa)
    _probe = {"tick": st["tick"], "max_ticks": 300}
    for u in st["units"]:
        _e.gas_damage(_probe, u, lambda m: None)
    alive_a = any(u["alive"] for u in st["units"][:3])
    alive_b = any(u["alive"] for u in st["units"][3:])
    if st["tick"] >= MAX_TICKS or not (alive_a or alive_b) or not (alive_a and alive_b):
        st["over"] = True
    return st


def to_obs_squad(st, idx: int) -> dict:
    me = st["units"][idx]
    team = 0 if idx < 3 else 1
    mates = [{"x": u["x"], "y": u["y"], "hp": u["hp"], "alive": u["alive"]}
             for i, u in enumerate(st["units"][:3] if team == 0 else st["units"][3:])]
    foes = []
    foe_units = st["units"][3:] if team == 0 else st["units"][:3]
    for u in foe_units:
        d = base._manhattan((me["x"], me["y"]), (u["x"], u["y"]))
        if d <= VIEW_RADIUS and u["alive"]:
            foes.append({"x": u["x"], "y": u["y"], "hp": u["hp"], "alive": True})
        else:
            foes.append({"x": -1, "y": -1, "hp": -1, "alive": u["alive"]})
    nearby = []
    for t in st["trees"]:
        d = base._manhattan((me["x"], me["y"]), t)
        if d <= VIEW_RADIUS:
            nearby.append({"type": "tree", "x": t[0], "y": t[1], "dist": d})
    for r in st["rocks"]:
        d = base._manhattan((me["x"], me["y"]), r)
        if d <= VIEW_RADIUS:
            nearby.append({"type": "rock", "x": r[0], "y": r[1], "dist": d})
    for g in st["golds"]:
        d = base._manhattan((me["x"], me["y"]), g)
        if d <= VIEW_RADIUS:
            nearby.append({"type": "gold", "x": g[0], "y": g[1], "dist": d})
    nearby.sort(key=lambda e: e["dist"])
    visible_foe = any(f["x"] != -1 for f in foes)
    return {
        "tick": st["tick"], "seed": st["seed"], "mode": "squad", "unit": idx % 3,
        "self": {"x": me["x"], "y": me["y"], "hp": me["hp"], "wood": me["wood"],
                 "stone": me["stone"], "gold": me["gold"], "has_sword": me["has_sword"],
                 "walls_left": me["walls_left"]},
        "squad": mates,
        "enemies": foes,
        "enemy": {"visible": visible_foe,
                  "x": next((f["x"] for f in foes if f["x"] != -1), -1),
                  "y": next((f["y"] for f in foes if f["y"] != -1), -1),
                  "hp": next((f["hp"] for f in foes if f["x"] != -1), -1)},
        "enemy_message": st["messages"][1 - team] if visible_foe else "",
        "nearby": nearby[:5],
        "events": list(st["events"][idx][-5:]),
        "budget": {"ticks_left": MAX_TICKS - st["tick"], "timeouts_so_far": me["timeouts"]},
    }


def score_squad(st, team: int) -> int:
    units = st["units"][:3] if team == 0 else st["units"][3:]
    s = sum(u["wood"] + u["stone"] + u["gold"] * 3 + u["kills"] * 10 for u in units)
    if any(base._manhattan((u["x"], u["y"]), TOTEM) == 1 for u in units if u["alive"]):
        s += 15
    return s


def result_squad(st) -> dict:
    s0, s1 = score_squad(st, 0), score_squad(st, 1)
    if s0 > s1:
        w = 0
    elif s1 > s0:
        w = 1
    else:
        h0 = sum(u["hp"] for u in st["units"][:3])
        h1 = sum(u["hp"] for u in st["units"][3:])
        w = 0 if h0 > h1 else 1 if h1 > h0 else -1
    return {"s0": s0, "s1": s1, "winner": w, "tick": st["tick"]}


def state_hash_squad(st) -> str:
    payload = json.dumps({
        "tick": st["tick"],
        "units": st["units"],
        "trees": sorted(st["trees"]), "rocks": sorted(st["rocks"]), "golds": sorted(st["golds"]),
        "walls": sorted(st["walls"].items()),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
