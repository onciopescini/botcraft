# 11 — S2 SPEC (Squad 3v3 cloni)

Attiva da: 21/09/2026. Stesso sim, modalità squadre. 1v1 resta valido.

## S2.1 Formato
Due squadre da 3 cloni dello STESSO agente (stessa funzione decide, chiamata 3 volte con `obs["unit"]` 0/1/2). 300 tick, 2/sec. Spawn: blu attorno (2,2),(3,2),(2,3), rossi attorno (29,29),(28,29),(29,28) con flip seed.

## S2.2 OBS aggiuntiva
- `unit`: 0/1/2, `squad`: [{x,y,hp,alive} x3 compagni incl. sé], `enemies`: [{x,y,hp,alive} x3, posizioni nascoste (-1) se oltre raggio 7 dal chiamante]
- `memory` condivisa tra cloni (stesso dict, salvata 1 volta a fine match)
- `enemy_message`: come S1 (ultimo messaggio nemico udito da QUALSIASI clone vicino)

## S2.3 Azioni
Stesse 12 azioni S1 per clone. Ordine deterministico per tick: A0,A1,A2,B0,B1,B2. Attack colpisce il PRIMO nemico adiacente (qualsiasi dei 3). Gather/craft/place come S1. Message: `state["messages"]` per squadra (1 slot per team, ultimo che parla vince, tag `<team-B>` per avversari vicini).

## S2.4 Score squadra
Somma risorse dei 3 + kill*10 (kill di qualsiasi clone) + totem 15 se ALMENO un clone adiacente a fine match. Pareggio -> hp totale, poi draw.

## S2.5 Ruoli emergenti (non imposti dal sim)
Baseline `squad_bot`: unit0 rusher (cerca nemico con spada), unit1 farmer (cerca gold poi legno/pietra), unit2 guard (resta entro 5 dal centro/totem dopo tick 100, attacca chi si avvicina). Tutto via `obs["unit"]`, nessuna regola speciale nel sim.

## S2.6 Replay v2
Righe con `v:2`, `t1:[{...}x3]`, `t2:[...]` + legacy `p1/p2` = capitani (unit0) per viewer vecchi. Viewer nuovo disegna 6 capsule.
