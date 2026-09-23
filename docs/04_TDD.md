# 04 — TDD: Architettura tecnica S0

Principio: **sim autorevole headless, renderer stupido, mediator paranoico.** Il 3D non deve mai poter rompere la logica.

## 4.1 Componenti

```
[player zip] -> [API submit + check] -> [coda match]
  -> [worker sandbox: sim.py + agentA + agentB + llm-gateway] -> [replay.jsonl + result.json]
  -> [store] -> [ladder service] + [3D viewer web che legge replay]
```

1. **sim (`sim/` Python puro, 0 dipendenze):**
   - `new_match(seed) -> state`, `step(state, a1, a2) -> state`, `to_obs(state, player) -> obs`
   - Nessun import agente dentro sim. Sim importa solo tipi.
   - Test: 1000 step random non crashano, determinismo: due run stesso seed = hash identico.

2. **runner (`runner/`):** carica i due `decide` in subprocess isolati, chiama con timeout 600ms, valida JSON, applica fallback noop, conta illegal/timeout, chiama LLM gateway se richiesto, scrive `replay.jsonl` (1 riga per tick: tick, pos, hp, inv, actions, events).

3. **orchestratore MVP:** coda FIFO su SQLite + 4 worker Docker `--network=none`, `--cpus=1`, `--memory=256m`, `--pids-limit=64`, timeout globale 200s per match. API minima: `POST /submit`, `GET /match/:id`, `GET /leaderboard`. No K8s in S0.

4. **llm-gateway (`llm/` BYOK OpenRouter):** unico punto che parla con OpenRouter. L'agente non ha mai API key (presa dal profilo utente, iniettata server-side). Gateway applica: allowlist modelli OpenRouter (priorità `:free`), temp 0, max_tokens per call, budget 6000 token/match, cache per obs identica, rate limit, log model+prompt hash+token per audit. Consigliamo 10$ di credito per sbloccare i free. Se chiave mancante/scarica/down -> ritorna `LLM_UNAVAILABLE` e agente deve fare fallback codice.

5. **store:** cartella `matches/:id/replay.jsonl + result.json + llm_usage.jsonl`. In S0 bastano file, niente DB complesso tranne ladder.

6. **viewer 3D (`viewer/` Three.js + Vite):**
   - Legge `replay.jsonl`, interpola posizioni tra tick (2/sec -> movimento smooth).
   - Asset low-poly procedurali: cubi per muri/alberi/rocce, capsule per agenti, cilindro per totem. Niente asset store esterni in S0.
   - UI: play/pausa, scrub tick, overlay hp/inv, velocità 1x/2x/4x.
   - Vietato: viewer non calcola mai logica, non chiama sim. Se replay manca, mostra errore.

## 4.2 Stack proposto
- Sim/runner/API: Python 3.11 + FastAPI + SQLite. Motivo: veloce da scrivere, team piccolo.
- Sandbox: Docker con `network=none` in S0, Firecracker/gVisor in S1 se serve più isolamento.
- Viewer: TypeScript + Three.js + Vite, deploy statico (Vercel/Netlify o cartella `dist/`).
- Formati: JSON ovunque, JSONL per replay. Hash SHA256 per zip agenti + replay per audit.

## 4.3 Flusso match (sequenza)
1. API riceve 2 versioni agenti + seed (random + 20% seed nascosti placement).
2. Worker avvia micro-container, monta zip read-only, avvia sim.
3. Per tick 1..300: genera obsA/obsB -> chiama decideA/decideB in parallelo con timeout -> valida -> sim.step -> append replay.
4. A fine: calcola score, scrive result, aggiorna Elo async, rilascia container.
5. Viewer può già streammare replay parziale (tail file).

## 4.4 Performance e costi S0
- Target: match code-only <15s wall time, match LLM <90s (dipende da OpenRouter free-tier rate limit).
- Budget LLM: 6000 token/match max. Con modelli `:free` + 10$ di credito costo hosting ~0€. Il costo resta al giocatore (BYOK), noi logghiamo solo `cost_per_match` stimato in result.json.
- Limiti anti-DoS: max 5 submit/ora per utente, max 10 match/giorno per versione in ladder pubblica, max 2 chiamate LLM per tick.

## 4.5 Testing
- Unit sim: movimento, gather, craft, muri, attack, bleed anti-stallo, determinismo.
- Integration: random vs greedy finisce 300 tick senza crash, replay rigiocabile.
- Safety: tentativo `import socket`, `open('/etc/passwd')`, loop infinito, fork bomb -> tutti bloccati/loggati.
- Viewer: carica replay da 300 tick <2s su laptop medio.

## 4.6 Cosa NON fare in S0
Niente websocket realtime sim-viewer, niente auth complessa (token statico), niente K8s, niente training RL server-side.

## 4.7 Stato 23/09 (architettura reale)
Meccaniche in `sim/engine.py` (1v1/squad/world condividono gather/craft/wall/bleed/gas/respawn). Auth: Bearer (API_TOKENS o Discord OAuth -> token db) su POST, quote code-only/open + tornei/stagioni. Replay v1/v2 + delta mondo. Site statica su Pages (landing+viewer+builder), API Docker su Render, worker locale/Docker/Boxer-hook.
