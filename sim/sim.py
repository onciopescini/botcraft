"""Botcraft S2 sim headless — 1v1 + squadre 3v3, autorevole, deterministico, 0 dipendenze."""
from __future__ import annotations
import random
import hashlib
import json
import re

W, H = 32, 32
MAX_TICKS = 300
VIEW_RADIUS = 7
WALL_DURATION = 30
RESPAWN_DELAY = 20
TOTEM = (16, 16)
GAS_DMG = 5          # sudden death fuori zona sicura
BOUNTY = 5           # taglia su chi è in testa quando lo uccidi

VALID_ACTIONS = {
    "move_N", "move_S", "move_E", "move_W",
    "gather", "craft_stick", "craft_sword", "craft_wall_kit",
    "place_wall", "attack", "noop", "message",
}

MSG_ALLOWED = re.compile(r"[^a-zA-Z0-9 .,!?\-]")
MSG_BANNED = re.compile(r"system|prompt|ignore|override", re.IGNORECASE)

DIRS = {
    "N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0),
    "move_N": (0, -1), "move_S": (0, 1), "move_E": (1, 0), "move_W": (-1, 0),
}


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


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
        "coach": [None, None],  # per lato: {"tick":t,"x":x,"y":y} ping del coach
        "walls": {},  # "x,y" -> expiry_tick
        "events": [[], []],
        "over": False,
    }
    return state


def set_coach(state: dict, pid: int, tick: int, x: int, y: int):
    """1 ping del coach per match: da tick in poi il bot vede obs["coach"]."""
    tick = max(0, min(state["max_ticks"], int(tick)))
    x = max(0, min(W - 1, int(x)))
    y = max(0, min(H - 1, int(y)))
    state["coach"][pid] = {"tick": tick, "x": x, "y": y}


def gas_radius(state: dict) -> float:
    """Sudden death: ultimi 1/6 di match, raggio 22 -> 3 sul totem."""
    mt = state["max_ticks"]
    start = mt * 5 // 6
    if state["tick"] < start:
        return 99.0
    f = (state["tick"] - start) / max(1, mt - start)
    return 22.0 - 19.0 * f


def _free_cell(state, rng):
    for _ in range(30):
        p = (rng.randrange(W), rng.randrange(H))
        if p == TOTEM or f"{p[0]},{p[1]}" in state["walls"]:
            continue
        if p in state["trees"] or p in state["rocks"] or p in state["golds"]:
            continue
        if any((a["x"], a["y"]) == p for a in state["agents"] if a["alive"]):
            continue
        return p
    return None


def _schedule_respawn(state, typ: str):
    if state["tick"] >= 280:
        return
    state["pending_respawns"].append([state["tick"] + RESPAWN_DELAY, typ])


def _process_respawns(state):
    due = [r for r in state["pending_respawns"] if r[0] <= state["tick"]]
    state["pending_respawns"] = [r for r in state["pending_respawns"] if r[0] > state["tick"]]
    caps = {"tree": 40, "rock": 20, "gold": 10}
    lists = {"tree": state["trees"], "rock": state["rocks"], "gold": state["golds"]}
    for due_tick, typ in due:
        if len(lists[typ]) >= caps[typ]:
            continue
        state["respawn_counter"] += 1
        rng = random.Random(f"{state['seed']}:{state['tick']}:{state['respawn_counter']}")
        p = _free_cell(state, rng)
        if p:
            lists[typ].append(p)


def clean_message(text) -> str:
    if not isinstance(text, str):
        return ""
    t = MSG_ALLOWED.sub("", text)[:32].strip()
    t = MSG_BANNED.sub("***", t)
    return t


def _wall_at(state, x, y):
    return f"{x},{y}" in state["walls"]


def _blocked(state, x, y):
    if not (0 <= x < W and 0 <= y < H):
        return True
    if _wall_at(state, x, y):
        return True
    if (x, y) in state["trees"] or (x, y) in state["rocks"] or (x, y) in state["golds"]:
        return True
    if (x, y) == TOTEM:
        return True  # totem non calpestabile, solo adiacenza bonus
    return False


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

    # azioni utili resettano noop_streak solo se riescono
    if raw == "gather":
        for lst, res, typ in ((state["trees"], "wood", "tree"), (state["rocks"], "stone", "rock"), (state["golds"], "gold", "gold")):
            for p in lst:
                if _manhattan((me["x"], me["y"]), p) == 1:
                    lst.remove(p)
                    me[res] += 1
                    me["noop_streak"] = 0
                    _push_event(state, pid, f"gather_ok {res}")
                    _schedule_respawn(state, typ)
                    return
        _push_event(state, pid, "gather_fail")
        me["noop_streak"] += 1
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
        if me["wood"] >= 2:
            me["wood"] -= 2
            me["sticks"] += 1
            me["noop_streak"] = 0
            _push_event(state, pid, "craft_ok stick")
        else:
            _push_event(state, pid, "craft_fail stick")
            me["noop_streak"] += 1
        return

    if raw == "craft_sword":
        if me["has_sword"]:
            _push_event(state, pid, "craft_fail sword_owned")
            me["noop_streak"] += 1
        elif me["wood"] >= 3 and me["stone"] >= 2:
            me["wood"] -= 3
            me["stone"] -= 2
            me["has_sword"] = True
            me["noop_streak"] = 0
            _push_event(state, pid, "craft_ok sword")
        else:
            _push_event(state, pid, "craft_fail sword")
            me["noop_streak"] += 1
        return

    if raw == "craft_wall_kit":
        if me["walls_left"] >= 20:
            _push_event(state, pid, "craft_fail wall_cap")
            me["noop_streak"] += 1
        elif me["stone"] >= 2:
            me["stone"] -= 2
            me["walls_left"] += 1
            me["noop_streak"] = 0
            _push_event(state, pid, "craft_ok wall")
        else:
            _push_event(state, pid, "craft_fail wall")
            me["noop_streak"] += 1
        return

    if raw == "place_wall":
        d = action.get("dir", "E") if isinstance(action, dict) else "E"
        if d not in DIRS:
            me["illegal"] += 1
            me["noop_streak"] += 1
            _push_event(state, pid, f"illegal:dir_{d}")
            return
        if me["walls_left"] <= 0:
            _push_event(state, pid, "wall_fail empty")
            me["noop_streak"] += 1
            return
        if len(state["walls"]) >= 40:
            _push_event(state, pid, "wall_fail cap")
            me["noop_streak"] += 1
            return
        dx, dy = DIRS[d]
        nx, ny = me["x"] + dx, me["y"] + dy
        other_pos = (foe["x"], foe["y"]) if foe["alive"] else None
        if not (0 <= nx < W and 0 <= ny < H) or _wall_at(state, nx, ny) or (nx, ny) in state["trees"] or (nx, ny) in state["rocks"] or (nx, ny) in state["golds"] or (nx, ny) == TOTEM or (nx, ny) == other_pos:
            _push_event(state, pid, "wall_fail blocked")
            me["noop_streak"] += 1
            return
        me["walls_left"] -= 1
        state["walls"][f"{nx},{ny}"] = state["tick"] + WALL_DURATION
        me["noop_streak"] = 0
        _push_event(state, pid, f"wall_ok {nx},{ny}")
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
    _apply(state, 0, a1)
    _apply(state, 1, a2)
    # bleed anti-stallo: 3 noop/illegal di fila -> -5 hp
    for pid in (0, 1):
        me = state["agents"][pid]
        if me["alive"] and me["noop_streak"] >= 3:
            me["hp"] -= 5
            me["noop_streak"] = 0
            _push_event(state, pid, "bleed -5")
            if me["hp"] <= 0:
                me["hp"] = 0
                me["alive"] = False
    # sudden death: fuori dalla zona sicura -> gas
    r = gas_radius(state)
    if r < 99.0:
        for pid in (0, 1):
            me = state["agents"][pid]
            if me["alive"] and _manhattan((me["x"], me["y"]), TOTEM) > r:
                me["hp"] -= GAS_DMG
                _push_event(state, pid, "gas -5")
                if me["hp"] <= 0:
                    me["hp"] = 0
                    me["alive"] = False
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
        "coach": state.get("coach", [None, None])[pid] if state["tick"] >= (state.get("coach", [None, None])[pid] or {}).get("tick", 10 ** 9) else None,
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
