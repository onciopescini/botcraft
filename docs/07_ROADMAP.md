# 07 — ROADMAP: piano totale verso mondo simulato

## Obiettivo finale (Nord Star)
Mondo persistente settimanale 256x256, 100+ agenti contemporanei, spawn/gather/craft/build/raid/alleanze, economia e territorio, replay 3D guardabili come una stagione sportiva. Tu aggiorni il codice, l'agente vive la settimana.

## Fase S0 — Arena 1v1 giocabile (2-3 settimane, team 1-2) — ordine deciso: sim prima, viewer dopo
- [ ] Step 1 sim: sim headless + runner + 2 bot (random, greedy) + test determinismo
- [ ] Step 2 backend: API submit + coda SQLite + 4 worker Docker + Elo + seed nascosti + replay.jsonl
- [ ] Step 3 LLM: gateway BYOK OpenRouter (10$ consigliati, modelli :free) con budget 6000 token + fallback
- [ ] Step 4 viewer: Viewer 3D low-poly read-only (play/pausa/scrub) che legge solo replay.jsonl
- Exit criteria: 10 agenti interni battono greedy, P95 <90s, 0 escape.

## Fase S1 — Profondità (3-4 settimane)
- Respawn risorse, gold, basi/porte, message 32 char con filtro.
- Memoria tra match (file `memory.json` 10KB persistente per agente).
- Lega separata Code-Only vs Open BYOK (evita pay-to-win).
- Viewer: minimappa, grafici hp/risorse, share link replay.

## Fase S2 — Squad (4-6 settimane)
- 3v3 cloni stesso agente, comandi limitati. Emergono ruoli.
- Tornei weekend a bracket, commento automatico da LLM su replay top.
- Marketplace versioni firmate + fork con un click.

## Fase S3 — Mondo persistente (8+ settimane, solo dopo S2 stabile)
- Mappa 128x128 -> 256x256, 50 -> 100 agenti, tick più lenti (1/sec) per scala.
- Stagioni settimanali, territorio, alleanze via message esteso.
- Sharding per zone + snapshot orari. Costi sotto controllo prima di scalare.

## Cosa NON fare ora
Niente editor online, niente mobile app, niente economia soldi veri, niente fisica 3D server-side, niente K8s in S0.

## Stima costi hosting S0 (BYOK)
VPS 4 worker ~20€/mese + LLM 0€ hosting (paga il giocatore con i suoi 10$ OpenRouter). Monitorare `cost_per_match` stimato in result.json per ranking fair tra free e paid.
