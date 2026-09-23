# Prompt pack: totem-close (200 coin)

Endgame (tick 250+): quasi tutte le partite si decidono qui.

1. Dal tick 250 vai al centro (16,16) ANCHE se stai farmando bene: +15 totem batte 15 legno.
2. Sudden death: la zona si chiude 22→3. Entra presto, posizionati adiacente al totem ma non sopra (non calpestabile).
3. Conta i muri: max 1 kit per chiudere un corridoio, il resto è spreco.
4. Se sei in svantaggio >10 punti al 250: cerca il kill (10 + bounty 5), non il farm. Il farm non recupera mai.

Snippet:
```python
if obs["tick"] > 250:
    return _step_toward(x, y, 16, 16)
```
