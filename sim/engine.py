"""Engine condiviso 1v1/squad/world — meccaniche pure, deterministiche, zero dipendenze circolari.

Contratto stato: dict con trees/rocks/golds (liste [x,y]), walls (dict "x,y"->expiry),
pending_respawns (liste [due,typ]), respawn_counter int, tick/seed/max_ticks int.
Agente: dict con x/y/hp/wood/stone/gold/sticks/has_sword/walls_left/alive/noop_streak.
ev: callable(msg) per eventi. Nessuna lettura di "agents"/"units": il chiamante passa posizioni.
"""
from __future__ import annotations
import random
import re

W, H = 32, 32
MAX_TICKS = 300
VIEW_RADIUS = 7
WALL_DURATION = 30
RESPAWN_DELAY = 20
TOTEM = (16, 16)
GAS_DMG = 5
BOUNTY = 5

DIRS = {
    "N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0),
    "move_N": (0, -1), "move_S": (0, 1), "move_E": (1, 0), "move_W": (-1, 0),
}
VALID_ACTIONS = {
    "move_N", "move_S", "move_E", "move_W",
    "gather", "craft_stick", "craft_sword", "craft_wall_kit",
    "place_wall", "attack", "noop", "message",
}

MSG_ALLOWED = re.compile(r"[^a-zA-Z0-9 .,!?\-]")
MSG_BANNED = re.compile(r"system|prompt|ignore|override", re.IGNORECASE)


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def clean_message(text) -> str:
    if not isinstance(text, str):
        return ""
    t = MSG_ALLOWED.sub("", text)[:32].strip()
    return MSG_BANNED.sub("***", t)


def wall_at(st, x, y):
    return f"{x},{y}" in st["walls"]


def blocked(st, x, y, w=None, h=None):
    w = st.get("w", W) if w is None else w
    h = st.get("h", H) if h is None else h
    if not (0 <= x < w and 0 <= y < h):
        return True
    if wall_at(st, x, y):
        return True
    if (x, y) in st["trees"] or (x, y) in st["rocks"] or (x, y) in st["golds"]:
        return True
    return (x, y) == TOTEM


def free_cell(st, rng, alive: set, tries: int = 30):
    w, h = st.get("w", W), st.get("h", H)
    totem = st.get("totem", TOTEM)
    for _ in range(tries):
        p = (rng.randrange(w), rng.randrange(h))
        if p == tuple(totem) or f"{p[0]},{p[1]}" in st["walls"]:
            continue
        if p in st["trees"] or p in st["rocks"] or p in st["golds"]:
            continue
        if p in alive:
            continue
        return p
    return None


def schedule_respawn(st, typ: str):
    if st["tick"] >= st.get("max_ticks", MAX_TICKS) - 20:
        return
    st["pending_respawns"].append([st["tick"] + RESPAWN_DELAY, typ])


def process_respawns(st, alive: set, caps=None, tries: int = 30):
    due = [r for r in st["pending_respawns"] if r[0] <= st["tick"]]
    st["pending_respawns"] = [r for r in st["pending_respawns"] if r[0] > st["tick"]]
    caps = caps or {"tree": 40, "rock": 20, "gold": 10}
    lists = {"tree": st["trees"], "rock": st["rocks"], "gold": st["golds"]}
    for _, typ in due:
        if len(lists[typ]) >= caps[typ]:
            continue
        st["respawn_counter"] += 1
        rng = random.Random(f"{st['seed']}:{st['tick']}:{st['respawn_counter']}")
        p = free_cell(st, rng, alive, tries)
        if p:
            lists[typ].append(p)


def gather(st, me, ev) -> bool:
    """Raccoglie risorsa adiacente. Ritorna True se riuscita (schedula respawn)."""
    for lst, res, typ in ((st["trees"], "wood", "tree"),
                          (st["rocks"], "stone", "rock"),
                          (st["golds"], "gold", "gold")):
        for p in lst:
            if manhattan((me["x"], me["y"]), tuple(p) if isinstance(p, list) else p) == 1:
                lst.remove(p)
                me[res] += 1
                me["noop_streak"] = 0
                ev(f"gather_ok {res}")
                schedule_respawn(st, typ)
                return True
    ev("gather_fail")
    me["noop_streak"] += 1
    return False


def craft(me, what: str, ev) -> bool:
    if what == "stick":
        ok = me["wood"] >= 2
        if ok:
            me["wood"] -= 2
            me["sticks"] += 1
    elif what == "sword":
        if me["has_sword"]:
            ev("craft_fail sword_owned")
            me["noop_streak"] += 1
            return False
        ok = me["wood"] >= 3 and me["stone"] >= 2
        if ok:
            me["wood"] -= 3
            me["stone"] -= 2
            me["has_sword"] = True
    elif what in ("wall", "wall_kit"):
        if me["walls_left"] >= 20:
            ev("craft_fail wall_cap")
            me["noop_streak"] += 1
            return False
        ok = me["stone"] >= 2
        if ok:
            me["stone"] -= 2
            me["walls_left"] += 1
    else:
        return False
    if ok:
        me["noop_streak"] = 0
        ev(f"craft_ok {what}")
    else:
        ev(f"craft_fail {what}")
        me["noop_streak"] += 1
    return ok


def place_wall(st, me, nx, ny, others: set, cap: int = 40) -> str:
    """Ritorna reason: ok|empty|cap|blocked|bad_dir. Applica solo se ok."""
    totem = tuple(st.get("totem", TOTEM))
    w, h = st.get("w", W), st.get("h", H)
    if me["walls_left"] <= 0:
        me["noop_streak"] += 1
        return "empty"
    if len(st["walls"]) >= cap:
        me["noop_streak"] += 1
        return "cap"
    if (not (0 <= nx < w and 0 <= ny < h) or wall_at(st, nx, ny)
            or (nx, ny) in st["trees"] or (nx, ny) in st["rocks"] or (nx, ny) in st["golds"]
            or (nx, ny) == totem or (nx, ny) in others):
        me["noop_streak"] += 1
        return "blocked"
    me["walls_left"] -= 1
    st["walls"][f"{nx},{ny}"] = st["tick"] + WALL_DURATION
    me["noop_streak"] = 0
    return "ok"


def bleed(me, ev) -> bool:
    """Ritorna True se muore."""
    if me["alive"] and me["noop_streak"] >= 3:
        me["hp"] -= 5
        me["noop_streak"] = 0
        ev("bleed -5")
        if me["hp"] <= 0:
            me["hp"] = 0
            me["alive"] = False
            return True
    return False


def gas_damage(st, me, ev) -> bool:
    """Ritorna True se muore. Gas su totem di stato (default TOTEM)."""
    mt = st.get("max_ticks", MAX_TICKS)
    start = mt * 5 // 6
    if st["tick"] < start:
        return False
    f = (st["tick"] - start) / max(1, mt - start)
    r = 22.0 - 19.0 * f
    totem = tuple(st.get("totem", TOTEM))
    if me["alive"] and manhattan((me["x"], me["y"]), totem) > r:
        me["hp"] -= GAS_DMG
        ev("gas -5")
        if me["hp"] <= 0:
            me["hp"] = 0
            me["alive"] = False
            return True
    return False


def gas_radius_mt(tick: int, max_ticks: int) -> float:
    start = max_ticks * 5 // 6
    if tick < start:
        return 99.0
    return 22.0 - 19.0 * ((tick - start) / max(1, max_ticks - start))
