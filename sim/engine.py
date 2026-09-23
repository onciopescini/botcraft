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
DRAFT_POINTS = 10
DRAFT_COSTS = {"hp10": 3, "sword": 4, "walls2": 2, "wood2": 1, "stone2": 1, "gold1": 2}
# mutatori settimanali (rotazione contenuti): gold_rush | no_swords | fast_gas | nessuno ""
MUTATORS = ("", "gold_rush", "no_swords", "fast_gas")

DIRS = {
    "N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0),
    "move_N": (0, -1), "move_S": (0, 1), "move_E": (1, 0), "move_W": (-1, 0),
}
VALID_ACTIONS = {
    "move_N", "move_S", "move_E", "move_W",
    "gather", "craft_stick", "craft_sword", "craft_wall_kit",
    "place_wall", "attack", "noop", "message", "dash", "shield",
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
    if gas_radius_mt(st["tick"], st.get("max_ticks", MAX_TICKS), gas_start_frac(st)) >= 99.0:
        return False
    totem = tuple(st.get("totem", TOTEM))
    if me["alive"] and manhattan((me["x"], me["y"]), totem) > gas_radius_mt(
            st["tick"], st.get("max_ticks", MAX_TICKS), gas_start_frac(st)):
        me["hp"] -= GAS_DMG
        ev("gas -5")
        if me["hp"] <= 0:
            me["hp"] = 0
            me["alive"] = False
            return True
    return False


def tick_timers(me):
    if me.get("dash_cd", 0) > 0:
        me["dash_cd"] -= 1
    if me.get("shield", 0) > 0:
        me["shield"] -= 1


def do_dash(st, me, d: str, others: set, ev) -> bool:
    """Scatto di 2 celle (cooldown 5). Ritorna True se mosso."""
    if me.get("dash_cd", 0) > 0 or d not in DIRS:
        me["noop_streak"] += 1
        ev("dash_fail")
        return False
    dx, dy = DIRS[d]
    cells = [(me["x"] + dx, me["y"] + dy), (me["x"] + 2 * dx, me["y"] + 2 * dy)]
    w, h = st.get("w", W), st.get("h", H)
    for nx, ny in cells:
        if not (0 <= nx < w and 0 <= ny < h) or wall_at(st, nx, ny) or (nx, ny) in st["trees"] \
                or (nx, ny) in st["rocks"] or (nx, ny) in st["golds"] \
                or (nx, ny) == tuple(st.get("totem", TOTEM)) or (nx, ny) in others:
            me["noop_streak"] += 1
            ev("dash_fail")
            return False
    me["x"], me["y"] = cells[1]
    me["dash_cd"] = 5
    me["noop_streak"] = 0
    ev("dash_ok")
    return True


def do_shield(me, ev) -> bool:
    """Scudo 3 tick (-8 danni), costa 2 pietra."""
    if me.get("shield", 0) > 0 or me["stone"] < 2:
        me["noop_streak"] += 1
        ev("shield_fail")
        return False
    me["stone"] -= 2
    me["shield"] = 3
    me["noop_streak"] = 0
    ev("shield_ok")
    return True


def shielded_damage(me, dmg: int) -> int:
    if me.get("shield", 0) > 0:
        return max(0, dmg - 8)
    return dmg


def gas_start_frac(st) -> float:
    return 3 / 6 if st.get("mutator") == "fast_gas" else 5 / 6


def gas_radius_mt(tick: int, max_ticks: int, frac: float = 5 / 6) -> float:
    start = max_ticks * frac
    if tick < start:
        return 99.0
    return 22.0 - 19.0 * ((tick - start) / max(1, max_ticks - start))


def validate_draft(picks: dict | None) -> dict:
    """Draft kit: 10 punti. Ritorna loadout normalizzato (mai oltre cap)."""
    picks = picks or {}
    def n(k):
        try:
            return max(0, int(picks.get(k, 0)))
        except Exception:
            return 0
    hp10 = min(3, n("hp10"))
    sword = 1 if picks.get("sword") else 0
    walls2 = min(3, n("walls2"))
    wood2 = min(5, n("wood2"))
    stone2 = min(5, n("stone2"))
    gold1 = min(3, n("gold1"))
    cost = (hp10 * DRAFT_COSTS["hp10"] + sword * DRAFT_COSTS["sword"]
            + walls2 * DRAFT_COSTS["walls2"] + wood2 * DRAFT_COSTS["wood2"]
            + stone2 * DRAFT_COSTS["stone2"] + gold1 * DRAFT_COSTS["gold1"])
    # scala tutto se oltre budget (priorità nell'ordine scritto)
    while cost > DRAFT_POINTS and (hp10 + walls2 + wood2 + stone2 + gold1) > 0:
        for k in ("gold1", "wood2", "stone2", "walls2", "hp10"):
            if k == "gold1" and gold1:
                gold1 -= 1
                break
            if k == "wood2" and wood2:
                wood2 -= 1
                break
            if k == "stone2" and stone2:
                stone2 -= 1
                break
            if k == "walls2" and walls2:
                walls2 -= 1
                break
            if k == "hp10" and hp10:
                hp10 -= 1
                break
        cost = (hp10 * DRAFT_COSTS["hp10"] + sword * DRAFT_COSTS["sword"]
                + walls2 * DRAFT_COSTS["walls2"] + wood2 * DRAFT_COSTS["wood2"]
                + stone2 * DRAFT_COSTS["stone2"] + gold1 * DRAFT_COSTS["gold1"])
    return {"hp": 100 + hp10 * 10, "sword": bool(sword),
            "walls": 5 + walls2 * 2, "wood": wood2 * 2,
            "stone": stone2 * 2, "gold": gold1}
