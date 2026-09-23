/* Botcraft no-code generator — puro, testabile con node.
   cfg: {archetype, aggression 0-100, greed 0-100, guard 0-100,
         craftSword bool, trashTalk bool, name} */
function generateBot(cfg) {
  const name = (cfg.name || 'my-bot').replace(/[^a-z0-9-]/gi, '').slice(0, 24) || 'my-bot';
  const aggroHp = Math.round(100 - (cfg.aggression / 100) * 70); // hp sopra cui caccia: 100..30
  const goldFirst = cfg.greed >= 50;
  const campTick = Math.round(300 - (cfg.guard / 100) * 250); // tick da cui campera: 300..50
  const talk = cfg.trashTalk
    ? `\n    if enemy.get("visible") and obs["tick"] % 50 == 25 and me["hp"] > 80:\n        return {"action": "message", "text": "ti vedo!"}\n`
    : '';
  const raceHead = cfg.race
    ? `    # modo corsa: dritto al totem, dash quando lontano
    dx, dy = 16 - x, 16 - y
    _dir = ("move_E" if dx > 0 else "move_W") if abs(dx) >= abs(dy) else ("move_S" if dy > 0 else "move_N")
    if abs(dx) + abs(dy) > 6 and me.get("dash_cd", 1) == 0:
        return {"action": "dash", "dir": _dir.split("_")[1]}
`
    : '';
  const code =
`"""${name} — generato dal Bot Builder (archetipo ${cfg.archetype}).
Aggressione ${cfg.aggression} · Ingordigia ${cfg.greed} · Guardia ${cfg.guard}
Modifica pure a mano: è Python normale.
"""
def decide(obs):
    me = obs["self"]
    x, y = me["x"], me["y"]
    enemy = obs.get("enemy", {})

    if not me["has_sword"] and ${cfg.craftSword ? 'me["wood"] >= 3 and me["stone"] >= 2' : 'False'}:
        return {"action": "craft_sword"}
    if enemy.get("visible"):
        ex, ey = enemy["x"], enemy["y"]
        if abs(ex - x) + abs(ey - y) == 1:
            return {"action": "attack"}
        if me["has_sword"] and me["hp"] > ${aggroHp}:
            return _go(x, y, ex, ey)
${talk}${raceHead}    for e in obs.get("nearby", []):
        if abs(e["x"] - x) + abs(e["y"] - y) == 1:
            return {"action": "gather"}
    if obs["tick"] > ${campTick}:
        return _go(x, y, 16, 16)
    nb = obs.get("nearby", [])
${goldFirst ? `    golds = [e for e in nb if e["type"] == "gold"]
    tgt = golds[0] if golds else (nb[0] if nb else None)
` : `    tgt = nb[0] if nb else None
`}    if tgt:
        return _go(x, y, tgt["x"], tgt["y"])
    return {"action": "move_E"} if (x + y) % 2 == 0 else {"action": "move_S"}


def _go(x, y, tx, ty):
    dx, dy = tx - x, ty - y
    if dx == 0 and dy == 0:
        return {"action": "noop"}
    if abs(dx) >= abs(dy):
        return {"action": "move_E" if dx > 0 else "move_W"}
    return {"action": "move_S" if dy > 0 else "move_N"}
`;
  const yaml =
`name: ${name}
entrypoint: agent:decide
runtime: python311
use_llm: false
max_llm_tokens_per_match: 0
max_ram_mb: 128
version: 1
`;
  return { code, yaml, aggroHp, campTick, goldFirst };
}

const ARCHETYPES = {
  balanced: { aggression: 50, greed: 50, guard: 30, craftSword: true, trashTalk: false },
  rusher: { aggression: 90, greed: 20, guard: 10, craftSword: true, trashTalk: true },
  farmer: { aggression: 15, greed: 95, guard: 20, craftSword: true, trashTalk: false },
  turtle: { aggression: 20, greed: 40, guard: 90, craftSword: true, trashTalk: false },
  racer: { aggression: 60, greed: 70, guard: 0, craftSword: true, trashTalk: false, race: true },
};

if (typeof module !== 'undefined') { module.exports = { generateBot, ARCHETYPES }; }
