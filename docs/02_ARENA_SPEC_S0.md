# 02 — ARENA SPEC S0 (source of truth regole)

Tick: 2/sec (500ms). Durata: 300 tick = 150s. Mappa: 32x32 toroidale? No — bordi = muri. Spawn: angoli opposti (2,2) vs (29,29), random flip con seed.

## 2.1 Entità S0
- 2 agenti: hp 100, pos, inventory {wood: int, stone: int}, sword: bool, walls_left: 20
- 40 alberi (wood), 20 rocce (stone), posizioni random con seed, no respawn in S0
- 1 totem centrale in (16,16): stare adiacente a fine match = +15 punti. Se distrutto? No, indistruttibile S0.
- Muri piazzati: max 40 totali, durata 30 tick, bloccano movimento e attack.

## 2.2 OBS JSON (input a decide)
```json
{
  "tick": 187,
  "seed": 12345,
  "self": {"x": 10, "y": 12, "hp": 70, "wood": 4, "stone": 2, "has_sword": true, "walls_left": 18},
  "enemy": {"visible": true, "x": 11, "y": 12, "hp": 60},
  "nearby": [
    {"type": "tree", "x": 10, "y": 13, "dist": 1},
    {"type": "rock", "x": 14, "y": 12, "dist": 4}
  ],
  "events": ["gather_ok wood", "hit_dealt 20", "illegal_last_tick: bad_json"],
  "budget": {"ticks_left": 113, "llm_tokens_left": 3400, "timeouts_so_far": 1}
}
```
Regole visibilità: enemy visibile solo se dist Manhattan <= 7. nearby limitato ai 5 più vicini entro raggio 7. events = ultimi 5. Niente mappa globale.

## 2.3 ACTION JSON (output da decide)
Una sola azione per tick. Formato:
```json
{"action": "move_N"} 
{"action": "gather"} 
{"action": "craft_sword"} 
{"action": "attack"} 
{"action": "place_wall", "dir": "E"}
{"action": "noop"}
```
Azioni valide: `move_N, move_S, move_E, move_W, gather, craft_stick, craft_sword, craft_wall_kit, place_wall, attack, noop`.

Dettaglio effetti:
- move: 1 cella se libera, altrimenti resta + evento `bump`.
- gather: se adiacente (4-dir) a tree/rock, +1 risorsa corrispondente, rimuove entità, cooldown implicito 1 tick. Se non adiacente -> `gather_fail`.
- craft_stick: 2 wood -> 1 stick (serve per sword? Semplificazione S0: sword = 3 wood + 2 stone, stick opzionale flavor). Tenere per progressione futura.
- craft_sword: 3 wood + 2 stone -> has_sword=true, attack 10 -> 20.
- craft_wall_kit: 2 stone -> walls_left +1 (cap 20). Parte con 5 kit già? Sì: start walls_left=5.
- place_wall dir: consuma 1 kit, mette muro in cella adiacente se libera, dura 30 tick.
- attack: se nemico adiacente 4-dir, danno 10 (20 con sword). Altrimenti `attack_miss`.
- noop: passa.

Qualsiasi JSON invalido, azione sconosciuta, timeout, eccezione -> `noop` + `illegal` conteggiato.

Anti-stallo: 3 noop/illegal consecutivi senza movimento -> hp -5 (bleed). Evita camper totali.

## 2.4 Scoring finale
```
score = wood*1 + stone*1 + kills*10 + totem_bonus
```
- wood/stone = inventario finale (non speso conta di più, scelta strategica).
- kills: 1 se uccidi (hp nemico <=0). Morto resta morto, respawn? No in S0. Il killer prende +10 e continua a farmare.
- totem_bonus: +15 se adiacente al totem al tick 300.
Pareggio -> vince chi ha più hp, poi coinflip da seed.

Elo usa win/loss/draw, non margine punti (margine solo per leaderboard secondaria).

## 2.5 Determinismo
Sim puro: `state, a1, a2 -> new_state` con RNG seeded (Python `random.Random(seed)`). Stesso seed + stesse azioni = stesso replay byte-identico. LLM non deve rompere questo: logghiamo azioni finali, non il ragionamento.

## 2.6 Cosa cambia in S1 (non implementare ora)
Respawn alberi, seconda risorsa gold, base e porte, message 32 char. Tenere `craft_stick` come hook.
