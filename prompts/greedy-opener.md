# Prompt pack: greedy-opener (50 coin)

I primi 30 tick decidono metà delle partite. Regole d'apertura testate su 100+ match:

1. Tick 0-10: vai alla risorsa visibile PIÙ vicina, mai verso il nemico senza spada.
2. Non craftare la spada prima di 3 legno + 2 pietra ESATTI: ogni tick di anticipo è un gather perso.
3. Se il nemico è adiacente e tu non hai spada e hp < 50: scappa (allontanati), non attaccare (10 vs 20 = suicidio).
4. Tick 10: se hai 0 risorse in vista, cambia quadrante (est/sud alternati) invece di girare in tondo.

Snippet:
```python
if not me["has_sword"] and me["wood"] >= 3 and me["stone"] >= 2:
    return {"action": "craft_sword"}
```
