# 01 — PRD: Botcraft S0

Stato: Draft approvato per S0 — 21/09/2026
Owner: da definire

## 1. Visione
Un mondo simulato stile Minecraft dove gli utenti non controllano il personaggio, ma programmano l'agente che lo controlla. Gli agenti si scontrano in 1v1, progrediscono in ladder, e il proprietario itera su codice, prompt e architettura guardando i replay 3D.

Obiettivo finale (12-18 mesi): mondo persistente settimanale 256x256 con 100+ agenti, economia di risorse, basi costruite, guerre e alleanze, tutto generato da agenti programmati dagli utenti. S0 è il primo scalino giocabile.

## 2. Utenti
- **Builder (primario):** sa Python base, vuole scrivere `decide(obs) -> action`. Vuole feedback in <60s: ho vinto? perché?
- **Prompter (secondario S0):** vuole migliorare il system prompt del suo LLM senza toccare troppa logica. Vuole vedere token usati e costo.
- **Spettatore:** guarda replay 3D e ladder. Non programma ma porta traffico.

Non-target S0: bambini senza coding, pro-gamer realtime, researcher RL.

## 3. Scope MVP S0 — cosa c'è
1. Arena 1v1 su mappa 32x32, 300 tick a 2 tick/sec, sim headless deterministico.
2. Azioni chiuse: 8 azioni (move x4, gather, craft x3 varianti, place, attack, noop). Dettaglio in `02_ARENA_SPEC_S0.md`.
3. Agenti ibridi Code+LLM: entrypoint Python `decide(obs)`, può chiamare LLM tramite gateway interno con budget fisso per match.
4. Submit tramite zip + `capabilities.yaml` + review automatica + quarantena.
5. Esecuzione sandboxata senza rete, timeout 600ms/tick, fallback noop.
6. Ladder Elo 1v1 + 20 placement nascosti anti-overfit.
7. Replay JSONL + viewer 3D low-poly web che rigioca il match (non interattivo in S0).
8. 2 bot di riferimento: `random` e `greedy-farmer-fighter` per testare subito.

## 4. Non-obiettivi S0 — cosa NON c'è
- Niente mondo persistente, niente 3v3, niente chat libera tra agenti (solo message 32 char loggato o disabilitato).
- Niente training RL sul server, niente fine-tuning hostato.
- Niente editor online: si sviluppa in locale, si submitta.
- Niente economia reale / soldi / scommesse.
- Niente fisica 3D reale: il 3D S0 è solo rendering del replay 2D.

## 5. User stories principali
- US1: carico il mio `agent.zip`, dopo 2 min vedo `Vittoria 34-21 vs greedy, replay #123`.
- US2: apro il replay 3D nel browser, vedo dove il mio agente è morto al tick 187.
- US3: cambio prompt + aggiungo regola "se hp<30 scappa", risubmitto v2, Elo sale da 1200 a 1280.
- US4: se il mio agente crasha/timeout, perdo il tick ma non il server, e vedo `illegal/timeout` nel log.

## 6. KPI di successo S0
- P95 submit -> risultato < 90 secondi con 4 worker.
- 100% dei match produce `replay.jsonl` riproducibile con stesso seed.
- 0 escape sandbox / 0 chiamate rete riuscite in test.
- Almeno 10 agenti diversi battano il bot greedy entro 2 settimane di playtest interno.
- Costo medio per match con LLM < 0.02€ (altrimenti rivedere budget token).

## 7. Rischi top (dettaglio in TDD/SAFETY)
1. Costi LLM fuori controllo -> BYOK OpenRouter (chiuso 21/09/2026) + budget token hard 6000/match. Consigliati 10$ per modelli :free.
2. Non-determinismo LLM rovina replay fair -> log prompt/completion + temperature 0 + seed, replay = azioni non ragionamento.
3. 3D subito rallenta tutto -> regola ferrea: sim non sa nulla del 3D, viewer solo client.
4. Cheat via overfit su mappa nota -> seed nascosti + mappe generate in placement.

## 8. Open questions (spostate in 08_DECISIONS.md)
- LLM hostato da noi o BYOK da subito?
- Message tra agenti abilitato in S0 o disabilitato?
- Limite righe codice / peso zip?
