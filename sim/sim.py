"""Botcraft S2 sim headless — 1v1 + squadre 3v3, autorevole, deterministico, 0 dipendenze."""
from __future__ import annotations
import random
import hashlib
import json
from sim import engine as _e

# Re-export: stessa interfaccia pubblica di prima, meccaniche in sim/engine.py
W, H = _e.W, _e.H
MAX_TICKS = _e.MAX_TICKS
VIEW_RADIUS = _e.VIEW_RADIUS
WALL_DURATION = _e.WALL_DURATION
RESPAWN_DELAY = _e.RESPAWN_DELAY
TOTEM = _e.TOTEM
GAS_DMG = _e.GAS_DMG
BOUNTY = _e.BOUNTY
VALID_ACTIONS = _e.VALID_ACTIONS
DIRS = _e.DIRS
MSG_ALLOWED = _e.MSG_ALLOWED
MSG_BANNED = _e.MSG_BANNED

_manhattan = _e.manhattan
clean_message = _e.clean_message
_wall_at = _e.wall_at
_blocked = _e.blocked
gas_radius = lambda state: _e.gas_radius_mt(state["tick"], state["max_ticks"])


def new_match(seed: int, max_ticks: int = MAX_TICKS) -> dict:
    rng = random.Random(seed)
    # spawn flip deterministico
    spawns = [(2, 2), (29, 29)]
    if rng.random() < 0.5:
        spawns = spawns[::-1]
    occupied = set(spawns) | {TOTEM}
    trees, rocks, golds = [], [], []
    # 40 alberi + 20 rocce + 10 gold, posizioni uniche non su spawn/totem
    while len(trees) < 40:
        p = (rng.randrange(W), rng.randrange(H))
        if p not in occupied:
            occupied.add(p)
            trees.append(p)
    while len(rocks) < 20:
        p = (rng.randrange(W), rng.randrange(H))
        if p not in occupied:
            occupied.add(p)
            rocks.append(p)
    while len(golds) < 10:
        p = (rng.randrange(W), rng.randrange(H))
        if p not in occupied:
            occupied.add(p)
            golds.append(p)
    state = {
        "seed": seed,
        "tick": 0,
        "max_ticks": max(20, max_ticks),
        "respawn_counter": 0,
        "agents": [
            {"x": spawns[0][0], "y": spawns[0][1], "hp": 100, "wood": 0, "stone": 0, "gold": 0,
             "sticks": 0, "has_sword": False, "walls_left": 5, "bounty": 0,
             "alive": True, "noop_streak": 0, "timeouts": 0, "illegal": 0, "kills": 0},
            {"x": spawns[1][0], "y": spawns[1][1], "hp": 100, "wood": 0, "stone": 0, "gold": 0,
             "sticks": 0, "has_sword": False, "walls_left": 5, "bounty": 0,
             "alive": True, "noop_streak": 0, "timeouts": 0, "illegal": 0, "kills": 0},
        ],
        "trees": trees,
        "rocks": rocks,
        "golds": golds,
        "pending_respawns": [],  # [due_tick, type]
        "messages": ["", ""],
        "action_clock": 0,  # orologio stalli: reset su gather/kill/craft, draw a 100
        "coach": [[], []],  # per lato: [{"tick":t,"x":x,"y":y}] (cap 3, da livelli)
        "walls": {},  # "x,y" -> expiry_tick
        "events": [[], []],
        "over": False,
    }
    return state


def set_coach(state: dict, pid: int, tick: int, x: int, y: int):
    """Ping del coach: da tick in poi il bot vede obs["coach"] (ultimo scaduto). Cap 3."""
    if len(state["coach"][pid]) >= 3:
        return
    tick = max(0, min(state["max_ticks"], int(tick)))
    x = max(0, min(W - 1, int(x)))
    y = max(0, min(H - 1, int(y)))
    state["coach"][pid].append({"tick": tick, "x": x, "y": y})
    state["coach"][pid].sort(key=lambda c: c["tick"])


def coach_now(state: dict, pid: int):
    due = [c for c in state["coach"][pid] if state["tick"] >= c["tick"]]
    return due[-1] if due else None


def gas_radius(state: dict) -> float:
    """Sudden death: ultimi 1/6 di match, raggio 22 -> 3 sul totem."""
    mt = state["max_ticks"]
    start = mt * 5 // 6
    if state["tick"] < start:
        return 99.0
    f = (state["tick"] - start) / max(1, mt - start)
    return 22.0 - 19.0 * f


def _free_cell(state, rng):
    alive = {(a["x"], a["y"]) for a in state["agents"] if a["alive"]}
    return _e.free_cell(state, rng, alive)


def _schedule_respawn(state, typ: str):
    _e.schedule_respawn(state, typ)


def _process_respawns(state):
    alive = {(a["x"], a["y"]) for a in state["agents"] if a["alive"]}
    _e.process_respawns(state, alive)


def _wall_at(state, x, y):
    return _e.wall_at(state, x, y)


def _blocked(state, x, y):
    return _e.blocked(state, x, y)


def _push_event(state, pid, msg):
    ev = state["events"][pid]
    ev.append(msg)
    if len(ev) > 5:
        del ev[0]


def _apply(state, pid, action: dict):
    me = state["agents"][pid]
    foe = state["agents"][1 - pid]
    if not me["alive"]:
        return
    raw = action.get("action", "noop") if isinstance(action, dict) else "noop"
    if raw not in VALID_ACTIONS:
        me["illegal"] += 1
        me["noop_streak"] += 1
        _push_event(state, pid, f"illegal:{raw}")
        return

    # movimento
    if raw.startswith("move_"):
        dx, dy = DIRS[raw]
        nx, ny = me["x"] + dx, me["y"] + dy
        other_pos = (foe["x"], foe["y"]) if foe["alive"] else None
        if _blocked(state, nx, ny) or (nx, ny) == other_pos:
            _push_event(state, pid, "bump")
            me["noop_streak"] += 1
        else:
            me["x"], me["y"] = nx, ny
            me["noop_streak"] = 0
            # muri che scadono non bloccano, pulizia lazy sotto
        return

    if raw == "noop":
        me["noop_streak"] += 1
        return

    # azioni utili resettano noop_streak solo se riescono (meccaniche in engine)
    if raw == "gather":
        _e.gather(state, me, lambda m: _push_event(state, pid, m))
        return

    if raw == "message":
        txt = clean_message(action.get("text", "") if isinstance(action, dict) else "")
        if not txt:
            _push_event(state, pid, "message_empty")
            me["noop_streak"] += 1
            return
        state["messages"][pid] = txt
        me["noop_streak"] = 0
        _push_event(state, pid, f"msg:{txt}")
        _push_event(state, 1 - pid, f"<opponent_said>:{txt}")
        return

    if raw == "craft_stick":
        _e.craft(me, "stick", lambda m: _push_event(state, pid, m))
        return

    if raw == "craft_sword":
        _e.craft(me, "sword", lambda m: _push_event(state, pid, m))
        return

    if raw == "craft_wall_kit":
        _e.craft(me, "wall", lambda m: _push_event(state, pid, m.replace("wall_kit", "wall")))
        return

    if raw == "place_wall":
        d = action.get("dir", "E") if isinstance(action, dict) else "E"
        if d not in DIRS:
            me["illegal"] += 1
            me["noop_streak"] += 1
            _push_event(state, pid, f"illegal:dir_{d}")
            return
        dx, dy = DIRS[d]
        nx, ny = me["x"] + dx, me["y"] + dy
        other_pos = (foe["x"], foe["y"]) if foe["alive"] else None
        others = {other_pos} if other_pos else set()
        r = _e.place_wall(state, me, nx, ny, others)
        if r == "ok":
            _push_event(state, pid, f"wall_ok {nx},{ny}")
        else:
            _push_event(state, pid, f"wall_fail {r}")
        return

    if raw == "attack":
        if foe["alive"] and _manhattan((me["x"], me["y"]), (foe["x"], foe["y"])) == 1:
            dmg = 20 if me["has_sword"] else 10
            foe["hp"] -= dmg
            me["noop_streak"] = 0
            _push_event(state, pid, f"hit_dealt {dmg}")
            _push_event(state, 1 - pid, f"hit_taken {dmg}")
            if foe["hp"] <= 0:
                foe["hp"] = 0
                foe["alive"] = False
                me["kills"] += 1
                _push_event(state, pid, "kill")
                if score(state, 1 - pid) > score(state, pid):
                    me["bounty"] += BOUNTY
                    _push_event(state, pid, f"bounty +{BOUNTY}")
        else:
            _push_event(state, pid, "attack_miss")
            me["noop_streak"] += 1
        return


def step(state: dict, a1: dict, a2: dict) -> dict:
    if state["over"]:
        return state
    state["tick"] += 1
    # scadenza muri + respawn risorse
    expired = [k for k, exp in state["walls"].items() if exp <= state["tick"]]
    for k in expired:
        del state["walls"][k]
    _process_respawns(state)
    snap = [(a["kills"], a["wood"], a["stone"], a["gold"], a["has_sword"]) for a in state["agents"]]
    _apply(state, 0, a1)
    _apply(state, 1, a2)
    now = [(a["kills"], a["wood"], a["stone"], a["gold"], a["has_sword"]) for a in state["agents"]]
    # orologio stalli: 100 tick senza gather/kill/craft -> draw tecnico (vince hp)
    state["action_clock"] = 0 if now != snap else state["action_clock"] + 1
    if state["action_clock"] >= 100:
        state["over"] = True
    for pid in (0, 1):
        _e.bleed(state["agents"][pid], lambda m, p=pid: _push_event(state, p, m))
    for pid in (0, 1):
        _e.gas_damage(state, state["agents"][pid], lambda m, p=pid: _push_event(state, p, m))
    if state["tick"] >= state["max_ticks"] or not (state["agents"][0]["alive"] or state["agents"][1]["alive"]):
        state["over"] = True
    return state


def to_obs(state: dict, pid: int) -> dict:
    me = state["agents"][pid]
    foe = state["agents"][1 - pid]
    dist_foe = _manhattan((me["x"], me["y"]), (foe["x"], foe["y"]))
    visible = dist_foe <= VIEW_RADIUS and foe["alive"]
    nearby = []
    for t in state["trees"]:
        d = _manhattan((me["x"], me["y"]), t)
        if d <= VIEW_RADIUS:
            nearby.append({"type": "tree", "x": t[0], "y": t[1], "dist": d})
    for r in state["rocks"]:
        d = _manhattan((me["x"], me["y"]), r)
        if d <= VIEW_RADIUS:
            nearby.append({"type": "rock", "x": r[0], "y": r[1], "dist": d})
    for g in state.get("golds", []):
        d = _manhattan((me["x"], me["y"]), g)
        if d <= VIEW_RADIUS:
            nearby.append({"type": "gold", "x": g[0], "y": g[1], "dist": d})
    nearby.sort(key=lambda e: e["dist"])
    nearby = nearby[:5]
    return {
        "tick": state["tick"],
        "seed": state["seed"],
        "self": {"x": me["x"], "y": me["y"], "hp": me["hp"], "wood": me["wood"],
                 "stone": me["stone"], "gold": me.get("gold", 0), "has_sword": me["has_sword"],
                 "walls_left": me["walls_left"]},
        "enemy": {"visible": visible,
                  "x": foe["x"] if visible else -1,
                  "y": foe["y"] if visible else -1,
                  "hp": foe["hp"] if visible else -1},
        "enemy_message": state.get("messages", ["", ""])[1 - pid] if visible else "",
        "my_last_message": state.get("messages", ["", ""])[pid],
        "coach": coach_now(state, pid),
        "gas_radius": round(gas_radius(state), 1),
        "nearby": nearby,
        "events": list(state["events"][pid][-5:]),
        "budget": {"ticks_left": state["max_ticks"] - state["tick"],
                   "timeouts_so_far": me["timeouts"]},
    }


def score(state: dict, pid: int) -> int:
    me = state["agents"][pid]
    s = me["wood"] + me["stone"] + me.get("gold", 0) * 3 + me["kills"] * 10 + me.get("bounty", 0)
    if _manhattan((me["x"], me["y"]), TOTEM) == 1:
        s += 15
    return s


def result(state: dict) -> dict:
    s0, s1 = score(state, 0), score(state, 1)
    if s0 > s1:
        winner = 0
    elif s1 > s0:
        winner = 1
    else:
        h0, h1 = state["agents"][0]["hp"], state["agents"][1]["hp"]
        if h0 > h1:
            winner = 0
        elif h1 > h0:
            winner = 1
        else:
            winner = -1  # draw
    return {"s0": s0, "s1": s1, "winner": winner, "tick": state["tick"]}


def state_hash(state: dict) -> str:
    payload = json.dumps({
        "tick": state["tick"],
        "max_ticks": state["max_ticks"],
        "agents": state["agents"],
        "trees": sorted(state["trees"]),
        "rocks": sorted(state["rocks"]),
        "golds": sorted(state.get("golds", [])),
        "walls": sorted(state["walls"].items()),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
