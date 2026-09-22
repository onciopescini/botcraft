# 06 — EVAL + LADDER S0

## 6.1 Formato match
1v1, 300 tick, seed random. 80% seed pubblici (rotazione giornaliera), 20% seed nascosti per placement e anti-overfit. Mappa generata da seed: posizioni alberi/rocce variano, spawn flip.

## 6.2 Elo
Start 1200. K=32 per i primi 20 match (placement), poi K=16. Draw = 0.5. Update solo a fine match valido. Match `aborted_safety` non conta per Elo ma conta per ban.

Leaderboard doppia:
- `Elo` (primaria, win/loss)
- `Style` (secondaria: avg risorse, kill rate, sopravvivenza) — solo per spettacolo, non per ranking.

## 6.3 Anti-overfit / anti-cheat
- Placement nascosti obbligatori per entrare in ladder pubblica.
- Limite 10 match/giorno per versione contro stesso avversario (evita farm Elo).
- Rilevazione hardcode: se agente vince 95% su seed pubblici ma <40% su nascosti -> flag `overfit_suspect`, richiesta nuova versione.
- Niente scouting obs globale: se un agente prova a leggere seed futuri o file replay avversario a runtime -> impossibile per sandbox, ma logghiamo tentativi di `open`.

## 6.4 Replay
`replay.jsonl`: 1 riga per tick con `tick, p1{x,y,hp,wood,stone,sword}, p2{...}, walls[], actions[a1,a2], events[]`. `result.json`: winner, score, motivo fine (timeout/kill/timeout_tick), hash sim finale, Elo delta.

Viewer 3D legge solo questi due file. Qualsiasi giocatore può scaricare replay e contestare risultato entro 7 giorni rigiocando con `runner --replay --check-hash`.
