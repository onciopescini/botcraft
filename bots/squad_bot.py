"""Bot squadra S2 — 3 cloni, ruoli da obs["unit"]: 0 rusher, 1 farmer, 2 guard."""
import greedy_bot


def decide(obs: dict) -> dict:
    unit = obs.get("unit", 0)
    me = obs["self"]
    mem = obs.get("memory", {}) if isinstance(obs.get("memory"), dict) else {}
    games = int(mem.get("sgames", 0)) + 1
    M = {"sgames": games}

    enemy = obs.get("enemy", {})
    ex, ey = enemy.get("x", -1), enemy.get("y", -1)
    x, y = me["x"], me["y"]

    def step_to(tx, ty):
        dx, dy = tx - x, ty - y
        if dx == 0 and dy == 0:
            return {"action": "noop", "memory": M}
        r = {"action": "move_E" if dx > 0 else "move_W"} if abs(dx) >= abs(dy) else {"action": "move_S" if dy > 0 else "move_N"}
        r["memory"] = M
        return r

    # unit0 rusher: se ha spada va a caccia, altrimenti farma veloce verso spada
    if unit == 0:
        if not me["has_sword"] and me["wood"] >= 3 and me["stone"] >= 2:
            return {"action": "craft_sword", "memory": M}
        if enemy.get("visible") and abs(ex - x) + abs(ey - y) == 1:
            return {"action": "attack", "memory": M}
        if enemy.get("visible") and (me["has_sword"] or me["hp"] > 60):
            return step_to(ex, ey)
        for e in obs.get("nearby", []):
            if abs(e["x"] - x) + abs(e["y"] - y) == 1:
                return {"action": "gather", "memory": M}
        nb = obs.get("nearby", [])
        if nb:
            return step_to(nb[0]["x"], nb[0]["y"])
        return step_to(16, 16)

    # unit1 farmer: gold prima, craft spada, scappa se nemico vicino senza spada
    if unit == 1:
        if not me["has_sword"] and me["wood"] >= 3 and me["stone"] >= 2:
            return {"action": "craft_sword", "memory": M}
        if enemy.get("visible") and abs(ex - x) + abs(ey - y) == 1:
            return {"action": "attack" if me["has_sword"] else "gather", "memory": M}
        for e in obs.get("nearby", []):
            if abs(e["x"] - x) + abs(e["y"] - y) == 1:
                return {"action": "gather", "memory": M}
        golds = [e for e in obs.get("nearby", []) if e["type"] == "gold"]
        tgt = golds[0] if golds else (obs.get("nearby", [None])[0])
        if tgt:
            return step_to(tgt["x"], tgt["y"])
        return step_to(16, 16)

    # unit2 guard: dopo tick 100 sta vicino al totem, attacca chi si avvicina
    if enemy.get("visible") and abs(ex - x) + abs(ey - y) == 1:
        return {"action": "attack", "memory": M}
    if obs["tick"] > 100:
        d = abs(16 - x) + abs(16 - y)
        if d > 5:
            return step_to(16, 16)
        for e in obs.get("nearby", []):
            if abs(e["x"] - x) + abs(e["y"] - y) == 1:
                return {"action": "gather", "memory": M}
        return {"action": "noop", "memory": M}
    return greedy_bot.decide(obs)
