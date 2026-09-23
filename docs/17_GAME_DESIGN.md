# 17 — GAME DESIGN (dal benchmark al gioco, 22/09/2026)

Tesi: programmare-e-aspettare è un benchmark. Il gioco nasce da dramma + agency + ritualità.

## Meccaniche
1. **Sudden death** (gas surviv.io): ultimi 1/6 di match, raggio 22→3 sul totem, -5 hp/tick fuori. Niente più vittorie ai punti noiose. Vale 1v1/blitz/squad.
2. **Blitz 60 tick** (~30s + coda): iterazione veloce, Elo separato. 300 tick solo per ladder classica e finali.
3. **Coach ping**: 1 ping pre-match `{"tick","x","y"}` per lato, visibile in `obs["coach"]` da tick in poi + diamante nel viewer. Agency senza rompere il sim istantaneo.
4. **Daily seed**: `YYYYMMDD % 100000`, stesso per tutti, 1 submit/giorno, classifica score senza Elo (`GET /daily`, pagina `daily.html`).
5. **Scommesse finte**: 100 coin ad agente, pari-mutuel sui pending, settle a fine match (`bets.html`). Lo spettatore ha qualcosa in palio.
6. **Bounty leader +5**: uccidere chi è in testa paga extra. Rimonte premiate.

## Arricchimenti (23/09)
7. **Draft kit**: 10 punti pre-match (hp/spada/muri/risorse). Deckbuilding leggero, validazione server.
8. **Mutatori settimanali**: gold_rush (20 gold), no_swords, fast_gas a rotazione nei tornei.
9. **Dash** (scatto 2 celle, cooldown 5) e **scudo** (-8 danni 3 tick, 2 pietra precastato). Micro-decisioni tattiche.

## Env #2: corsa (23/09)
Primo adiacente al totem vince (150 tick). Kill senza punti, respawn dopo 10 tick, muri per sabotare, gold tiebreak. Elo race separato. Greedy classico perde sempre (campera fino al 250): servono bot che corrono davvero.

## Anti-pattern evitati (Screeps)
Debug lento (noi: blitz+demo istantanea), codice altrui nel client (viewer solo numeri), silenzio sui rischi (docs/05 + 15 espliciti).
