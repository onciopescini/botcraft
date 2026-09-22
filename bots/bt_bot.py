"""Bot behavior-tree esplicito — esempio didattico (HF ML-for-Games: BT > LLM per decidere).

Struttura classica Selector -> Sequence -> Condition/Action.
Il modello (LLM/Jev/tiny) qui NON decide: al massimo sceglie il flavor dei message.
Per giocare: copia questo file e cambia priorità/condizioni.
"""

def decide(obs):
    mem = obs.get("memory", {}) if isinstance(obs.get("memory"), dict) else {}
    blackboard = {"obs": obs, "mem": {"games": int(mem.get("games", 0)) + 1}}
    for node in (combat, survive, economy, totem, explore):
        r = node(blackboard)
        if r is not None:
            r.setdefault("memory", blackboard["mem"])
            return r
    r = {"action": "noop", "memory": blackboard["mem"]}
    return r


def combat(bb):
    me, en = bb["obs"]["self"], bb["obs"].get("enemy", {})
    if not en.get("visible"):
        return None
    d = abs(en["x"] - me["x"]) + abs(en["y"] - me["y"])
    if d == 1 and (me["has_sword"] or me["hp"] <= 25):
        return {"action": "attack"}
    if me["has_sword"] and me["hp"] > 55:
        return step(bb, en["x"], en["y"])
    return None


def survive(bb):
    me = bb["obs"]["self"]
    if me["hp"] < 30:
        n = nearest(bb, ("tree", "rock", "gold"))
        if n:
            return step(bb, n["x"], n["y"])  # scappa farmando
    return None


def economy(bb):
    me = bb["obs"]["self"]
    if not me["has_sword"] and me["wood"] >= 3 and me["stone"] >= 2:
        return {"action": "craft_sword"}
    for e in bb["obs"].get("nearby", []):
        if abs(e["x"] - me["x"]) + abs(e["y"] - me["y"]) == 1:
            return {"action": "gather"}
    golds = [e for e in bb["obs"].get("nearby", []) if e["type"] == "gold"]
    tgt = golds[0] if golds else nearest(bb, ("tree", "rock", "gold"))
    if tgt:
        return step(bb, tgt["x"], tgt["y"])
    return None


def totem(bb):
    if bb["obs"]["tick"] > 250:
        return step(bb, 16, 16)
    return None


def explore(bb):
    me = bb["obs"]["self"]
    return {"action": "move_E" if (me["x"] + me["y"]) % 2 == 0 else "move_S"}


def nearest(bb, types):
    me = bb["obs"]["self"]
    cands = [e for e in bb["obs"].get("nearby", []) if e["type"] in types]
    return cands[0] if cands else None


def step(bb, tx, ty):
    me = bb["obs"]["self"]
    dx, dy = tx - me["x"], ty - me["y"]
    if dx == 0 and dy == 0:
        return {"action": "noop"}
    if abs(dx) >= abs(dy):
        return {"action": "move_E" if dx > 0 else "move_W"}
    return {"action": "move_S" if dy > 0 else "move_N"}
