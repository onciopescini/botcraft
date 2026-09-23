# Prompt pack: sword-rush (100 coin)

Quando la spada ripaga e quando è una trappola:

1. Rush conviene se: nemico visibile + tuo hp > 60 + tick < 150. Dopo il 150 la mappa è vuota e la spada non trova bersagli.
2. Non inseguire oltre 7 celle da casa: il bleed da stallo (-5/3 tick) uccide più dei nemici.
3. Con spada, l'attack fa 20: due colpi = kill su hp 70. Conta i colpi, poi torna a farmare.
4. Se il nemico ha spada e tu no: gather gold (vale 3x) e gioca il totem, non lo scontro.

Snippet:
```python
if me["has_sword"] and enemy.get("visible") and me["hp"] > 60:
    # caccia solo entro raggio utile
    return _step_toward(x, y, enemy["x"], enemy["y"])
```
