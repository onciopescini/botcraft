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

## Domande aperte per te (rispondi in chat)
1. ~~LLM provider~~ -> CHIUSO: BYOK OpenRouter, 10$ consigliati, modelli :free.
2. ~~Message~~ -> CHIUSO dal team: OFF in S0.
3. ~~Limite zip~~ -> CHIUSO dal team: 2MB stdlib+numpy.
4. **Nome progetto:** `Botcraft` — DECISO 21/09/2026. Ex working title `Agent Arena` scartato per genericità/SEO.
5. **Prossimo task build:** `sim` poi `viewer` — DECISO 21/09/2026 su fiducia team tecnico. Motivo: sim = gioco vero senza immagini, viewer = immagini senza gioco.

Rispondi tipo `4-Botcraft, 5-sim` e aggiorno i docs.
