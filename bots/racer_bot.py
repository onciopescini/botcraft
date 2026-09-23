"""Bot racer — corre al totem, raccoglie strada facendo, spazza chi blocca."""


def decide(obs):
    me = obs["self"]
    x, y = me["x"], me["y"]
    enemy = obs.get("enemy", {})

    if enemy.get("visible") and abs(enemy["x"] - x) + abs(enemy["y"] - y) == 1:
        if me.get("has_sword") or enemy.get("hp", 100) <= 30:
            return {"action": "attack"}
    if not me.get("has_sword") and me["wood"] >= 3 and me["stone"] >= 2:
        return {"action": "craft_sword"}
    for e in obs.get("nearby", []):
        if abs(e["x"] - x) + abs(e["y"] - y) == 1:
            return {"action": "gather"}
    # dritto al totem, con dash se libero
    dx, dy = 16 - x, 16 - y
    direction = ("move_E" if dx > 0 else "move_W") if abs(dx) >= abs(dy) else ("move_S" if dy > 0 else "move_N")
    if abs(dx) + abs(dy) > 6 and me.get("dash_cd", 1) == 0:
        return {"action": "dash", "dir": direction.split("_")[1]}
    return {"action": direction}
