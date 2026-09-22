# 17 — GAME DESIGN (dal benchmark al gioco, 22/09/2026)

Tesi: programmare-e-aspettare è un benchmark. Il gioco nasce da dramma + agency + ritualità.

## Meccaniche
1. **Sudden death** (gas surviv.io): ultimi 1/6 di match, raggio 22→3 sul totem, -5 hp/tick fuori. Niente più vittorie ai punti noiose. Vale 1v1/blitz/squad.
2. **Blitz 60 tick** (~30s + coda): iterazione veloce, Elo separato. 300 tick solo per ladder classica e finali.
3. **Coach ping**: 1 ping pre-match `{"tick","x","y"}` per lato, visibile in `obs["coach"]` da tick in poi + diamante nel viewer. Agency senza rompere il sim istantaneo.
4. **Daily seed**: `YYYYMMDD % 100000`, stesso per tutti, 1 submit/giorno, classifica score senza Elo (`GET /daily`, pagina `daily.html`).
5. **Scommesse finte**: 100 coin ad agente, pari-mutuel sui pending, settle a fine match (`bets.html`). Lo spettatore ha qualcosa in palio.
6. **Bounty leader +5**: uccidere chi è in testa paga extra. Rimonte premiate.

## Anti-pattern evitati (Screeps)
Debug lento (noi: blitz+demo istantanea), codice altrui nel client (viewer solo numeri), silenzio sui rischi (docs/05 + 15 espliciti).
