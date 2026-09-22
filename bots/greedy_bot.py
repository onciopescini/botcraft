"""Bot greedy farmer-fighter — baseline S1 (gold + memoria + message)."""

def decide(obs: dict) -> dict:
    me = obs["self"]
    x, y = me["x"], me["y"]
    mem = obs.get("memory", {}) if isinstance(obs.get("memory"), dict) else {}
    games = int(mem.get("games", 0)) + 1

    # 1. craft spada appena possibile
    if not me["has_sword"] and me["wood"] >= 3 and me["stone"] >= 2:
        return {"action": "craft_sword", "memory": {"games": games}}
    # 2. kit muri se pietra in eccesso e pochi kit
    if me["stone"] >= 6 and me["walls_left"] < 8:
        return {"action": "craft_wall_kit", "memory": {"games": games}}

    # 3. se nemico visibile e adiacente -> attacco
    enemy = obs.get("enemy", {})
    if enemy.get("visible"):
        ex, ey = enemy["x"], enemy["y"]
        if abs(ex - x) + abs(ey - y) == 1:
            return {"action": "attack", "memory": {"games": games}}
        if me["has_sword"] and me["hp"] > 50:
            r = _step_toward(x, y, ex, ey)
            r["memory"] = {"games": games}
            return r
        # S1: trash-talk ogni tanto se vicino (costa un tick, solo se hp alti)
        if obs["tick"] % 50 == 25 and me["hp"] > 80:
            return {"action": "message", "text": "ti vedo, farmer", "memory": {"games": games}}

    # 4. gather se risorsa adiacente (gold vale di più ma gather è uguale)
    for e in obs.get("nearby", []):
        if abs(e["x"] - x) + abs(e["y"] - y) == 1:
            return {"action": "gather", "memory": {"games": games}}

    # 5. endgame -> centro totem
    if obs["tick"] > 250:
        r = _step_toward(x, y, 16, 16)
        r["memory"] = {"games": games}
        return r

    # 6. vai verso gold prima, poi resto
    nearby = obs.get("nearby", [])
    golds = [e for e in nearby if e["type"] == "gold"]
    target = golds[0] if golds else (nearby[0] if nearby else None)
    if target:
        r = _step_toward(x, y, target["x"], target["y"])
        r["memory"] = {"games": games}
        return r

    # fallback anti-bleed
    r = {"action": "move_E"} if (x + y) % 2 == 0 else {"action": "move_S"}
    r["memory"] = {"games": games}
    return r


def _step_toward(x, y, tx, ty):
    # muove di 1 cella riducendo Manhattan, preferisce asse con gap maggiore
    dx = tx - x
    dy = ty - y
    if dx == 0 and dy == 0:
        return {"action": "noop"}
    if abs(dx) >= abs(dy):
        return {"action": "move_E" if dx > 0 else "move_W"}
    return {"action": "move_S" if dy > 0 else "move_N"}
