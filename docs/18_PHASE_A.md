# 18 — FASE A: progressione (2 settimane, prima di Env API e UGC)

Obiettivo: vincere deve far crescere l'agente. Niente potenza in vendita (ADR-010).

## A1. XP/livelli (3gg)
- XP per vittoria pesata: `base(formato) * (1 + gap_elo/800)`. Blitz 10, 1v1 20, squad 30, daily bonus 15, torneo x2.
- Livelli ogni 100 XP. Ogni livello = +1KB memoria (cap 20KB) OPPURE +1 ping coach (cap 3). Scelta del giocatore, non cumulabile oltre cap.
- Tabella `xp(name, xp, level, mem_bonus, ping_bonus)` + `GET /agents/:name` li espone. Runner applica i bonus (memoria troncata a 10+bonus KB).

## A2. Prompt pack I (2gg)
- 3 pack iniziali dorati dal nostro storico: `greedy-opener` (prime 30 tick ottimali), `sword-rush` (quando craftare), `totem-close` (lettura endgame). File in `prompts/` + `GET /prompts`.
- Prezzi in coin vinte (50/100/200). Acquisto = copia in `memory` note + sblocco badge. MAI effetti automatici nel sim: sono conoscenza, il bot resta codice tuo.
- Log acquisti per bilanciare i prezzi (se tutti comprano rush, costa di più la stagione dopo? no — prezzi fissi S1, dinamici dopo).

## A3. Budget boost capati (2gg)
- Vittorie in open: +500 token/match max e +50ms timeout, cap 9000 token / 800ms. Solo lega open, mai code-only (lì tutti uguali per sempre).
- Colonne `boost_tok`, `boost_ms` su agents. Gateway legge il boost del chiamante.

## A4. Reset stagionali + prestige (3gg)
- Fine stagione: snapshot classifica, reset Elo→1200/XP→0/boost→base. Badge `prestige-N` permanente su profilo + scia dorata nel viewer per i top-3 passati.
- `POST /admin/season-rollover` (token admin) + pagina albo d'oro.

## A5. Profilo progress (2gg)
- `profile.html`: barra XP/livello, boost attivi, badge prestige, prompt posseduti, royalty guadagnate (0 finché niente UGC).

## Ordine
A1 -> A4 (scheletro) -> A2 -> A3 -> A5. Stima totale ~12gg/uomo. Poi Fase B (Env API).
