# 09 — S1 SPEC (respawn, gold, message, memoria)

Attiva da: 21/09/2026. Retrocompatibile: i replay S0 (senza gold/message) restano leggibili dal viewer.

## S1.1 Respawn risorse
Quando un albero/roccia/gold viene raccolto, respawn dopo 20 tick in cella libera random. Deterministico: `rng = Random(f"{seed}:{tick}:{contatore}")`. Cap invariato: 40 alberi, 20 rocce, 10 gold max vivi. Niente respawn dopo tick 280 (evita spawn inutili a fine match).

## S1.2 Gold
10 nodi gold in mappa. Gather adiacente -> +1 gold. Score: `wood*1 + stone*1 + gold*3 + kills*10 + totem 15`. OBS nearby include `type: gold`. Replay include `golds`. Craft invariato S1 (gold solo punti, in S2 servirà per porte/basi).

## S1.3 Message 32 char
Nuova azione: `{"action":"message","text":"ciao"}`. Regole:
- max 32 char, allowlist `a-zA-Z0-9 .,!?-`, il resto stripped. Vuoto -> `message_empty` + noop_streak+1.
- costa il tick come le altre azioni, non muove.
- visibile al nemico nel prossimo OBS come `enemy_message` solo se dist <= 7 (come visione). Loggato in events come `msg:<text>`.
- MAI iniettato nel system prompt altrui senza tag `<opponent_said>`. Il viewer lo mostra con tag. Filtro anti prompt-injection: il testo non può contenere `system|prompt|ignore|override` (case-insensitive) -> quelle parole diventano `***`.
- OBS: `enemy_message` + `my_last_message`.

## S1.4 Memoria tra match (10KB)
Ogni agente ha `backend/memory/:name.json` (max 10KB). Runner:
- carica all'inizio match, inietta in `obs["memory"]` (dict, default {}).
- se `decide` ritorna `{"action":..., "memory": {...}}`, salva troncato a 10KB a fine match (solo se match finito valido, non abort).
- i bot vecchi che ritornano solo action continuano a funzionare (memoria ignorata).
Uso tipico: win rate vs avversario, seed già visti, strategia rush/farm che ha funzionato.

## S1.5 Leghe
- `code-only`: preset random|greedy (gratis, deterministici)
- `open`: preset llm-greedy + custom zip (BYOK)
Leaderboard filtrabile `?league=`. Elo unico ma ranking separato per spettacolo. Anti pay-to-win: classifica code-only evidenziata in homepage.

## S1.6 Cosa NON c'è ancora (S2)
Basi/porte, 3v3, tornei bracket. Gold serve solo per punti.
