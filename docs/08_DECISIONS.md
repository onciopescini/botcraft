# 08 — DECISIONS (ADR) + domande aperte

## ADR-001: tick 2/sec — DECISO 21/09/2026
Contesto: realtime esclude LLM e costa troppo. Decisione: 2 tick/sec, 300 tick. Conseguenza: viewer interpola movimento. Reversibile in S3 con tick 1/sec per mondo grande.

## ADR-002: Code+LLM ibrido BYOK OpenRouter — DECISO 21/09/2026
Contesto: solo codice = economico ma meno hype, solo LLM = costoso e instabile. Decisione: codice obbligatorio con fallback, LLM opzionale via gateway BYOK OpenRouter. Chiave nel profilo, mai nello zip. Consigliamo 10$ per sbloccare modelli `:free`. Allowlist modelli + budget 6000 token/match. Conseguenza: costo inferenza al giocatore, hosting quasi gratis, ogni agente deve vincere anche senza LLM.

## ADR-005: message tra agenti OFF in S0 — DECISO da team tecnico 21/09/2026
Decisione: nessun canale testo in S0. Solo azioni fisiche. Motivo: evita prompt-injection e collusioni senza filtro maturo. Abilitato 32 char in S1 con tag `<opponent_said>` e filtro.

## ADR-006: zip 2MB stdlib+numpy — DECISO da team tecnico 21/09/2026
Decisione: max 2MB, max 200 file, solo stdlib + numpy in S0. Niente torch/sklearn. Motivo: build veloci, sandbox semplice, match <15s. Allarghiamo allowlist in S1 solo se richiesto da ladder.

## ADR-003: 3D low-poly subito ma solo viewer — DECISO 21/09/2026
Contesto: utente vuole wow 3D da subito. Decisione: sim resta 2D logica, viewer Three.js legge replay. Nessuna logica nel client. Conseguenza: niente doppia implementazione regole, niente cheat client.

## ADR-004: solo 1v1 ladder in S0 — DECISO 21/09/2026
Contesto: mondo persistente subito = troppo lavoro e sbilanciato. Decisione: 1v1 Elo, mondo in S3. Conseguenza: design arena deve già prevedere muri/memoria per riuso futuro.

## ADR-007: login Discord spettatori (copiare) — DECISO 22/09/2026
OAuth2 Discord -> token API riusabile. GET restano aperte, POST richiedono token. Disabilitato senza env (dev locale aperto). Motivo: zero signup custom, community già su Discord.

## ADR-008: mobile touch-orbit DOPO login — DECISO 22/09/2026, differito
Prima login+playtest, poi controlli touch. Viewer già responsive bottom-sheet.

## ADR-009: MAI pay-to-win — DECISO 22/09/2026, permanente
Solo cosmetici/donazioni. Elo, quote base e leghe mai in vendita. Motivo: la ladder muore il giorno che si compra.
## Storico domande chiuse
1. ~~LLM provider~~ -> BYOK OpenRouter. 2. ~~Message~~ -> OFF in S0. 3. ~~Zip~~ -> 2MB stdlib+numpy.
4. Nome `Botcraft`. 5. Build `sim` poi `viewer`. 6. Copiare/co-nostro + A/B/C -> ADR-007/008/009.
Domande aperte: nessuna. Backlog in docs/16_RESEARCH.md.
