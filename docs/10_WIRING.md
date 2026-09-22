# 10 — WIRING: cosa copiamo dal web (solo cablaggio, zero rewrite)

Ricerca del 21/09/2026. Principio: non riscriviamo, cabliamo repo maturi.

## 1. PettingZoo (Farama) — API standard multi-agente
Repo: https://github.com/Farama-Foundation/PettingZoo (3.5k star, MIT). Docs: https://pettingzoo.farama.org/
Cosa prendiamo: il pattern Parallel API (`reset/step` simultanei come il nostro `sim.step(a1,a2)`) + AEC per turni futuri. Loro hanno già Atari/Butterfly/Classic come reference e wrapper SuperSuit.
Cablaggio nostro (1 file, core intoccato): `sim/pettingzoo_wrapper.py` con `BotcraftParallel` che espone `reset(seed)->obs`, `step({p1:a1,p2:a2})`, `observe()`. Così chiunque può allenare RL con CleanRL/Tianshou senza toccare il sim.
Decisione stack: NESSUN cambio, solo adapter.

## 2. Battlecode 2026 — il modello da copiare pari pari
Repo: https://github.com/battlecode/battlecode26 — engine headless + client TypeScript + schema replay + example-bots + maps + `gradlew headless`.
Noi siamo già identici (sim + viewer + bots + runner). Da copiare:
- replay versionato (`{"v":1,...}` per riga o header) così S0/S1/S2 restano leggibili
- cartella `maps/` con pool di seed noti + mappe generate (anti-overfit come i loro placement)
- CLI `headless` che sputa replay in `/matches` (il nostro `runner/run.py` già lo fa)
Decisione stack: aggiungere `v:1` al replay + `maps/pool.json`. 1h di lavoro.

## 3. Sandbox esecuzione — NON la costruiamo noi
Trovati (tutti open):
- Boxer https://github.com/theonekeyg/boxer — HTTP `POST /run` dentro gVisor/runsc, limiti risorse. Perfetto come executor remoto.
- python-sandbox https://github.com/eduardobeattie/python-sandbox — pattern Dispatcher (API+rete) / Executor (no rete, read-only, cap-drop, limiti). È ESATTAMENTE il nostro mediator già scritto nel compose.
- exec-sandbox https://github.com/tkdtaylor/exec-sandbox — `run(payload)` unico dietro tier bubblewrap/gVisor/Firecracker + egress proxy + audit.
- OpenSandbox docs secure-container + firecracker-sandbox https://github.com/alialle/firecracker-sandbox — microVM 125ms per job, da usare solo in S3.
Cablaggio nostro: `BOXER_URL` env nel worker. Se settato, il worker manda lo zip a Boxer invece di `import`. Se vuoto, gira locale (dev). Zero nuove dipendenze oggi, strada spianata per prod.
Decisione stack: NESSUN cambio oggi, solo env hook.

## 4. Deploy web/app — Railway + Vercel (pattern standard 2026)
Guide trovate: Railway FastAPI via Dockerfile + dominio generato; Vercel FastAPI come singola Function (`app.py`/`backend/api:app` via `tool.vercel.entrypoint`), frontend statico da CDN (`public/` o `app.frontend()`), split classico Railway=backend + Vercel=frontend con `CORS_ORIGINS`.
Cablaggio nostro:
- `railway.toml` (build Dockerfile, start `uvicorn backend.api:app`, volume matches, secret OPENROUTER_API_KEY)
- viewer già statico -> deploy Vercel come sito + in futuro `app.frontend("/", directory="viewer")`
- DB: SQLite va bene in locale, in prod passare a Postgres (1 env var, SQLAlchemy solo lì)
Decisione stack: NESSUN cambio framework (FastAPI+Three.js restano), solo 2 file di deploy.

## 5. OpenRouter BYOK — siamo già allineati
Gli harness agent Arena usano `provider/modello` + OpenRouter con free model (kimi-k2.5, deepseek-v3.2, glm-5). Noi usiamo già `openrouter:` + allowlist free. Tenere così.

## 6. laya-coreml (monitorata, NON integrata)
Repo: https://github.com/mizorewww/laya-coreml (Apache-2.0, 19/09/2026) — modelli aperti Laya in locale su Apple Core ML, ~5ms a decisione, zero token generati. Stesso paradigma di Jev (decisioni tipizzate), versione open-weight.
Perché no ora: solo macOS Apple Silicon (noi Windows/Linux), repo neonata non ufficiale, pesi Snake-centrici. Slot pronto: `JEV_PROVIDER=local` nel gateway (stessa interfaccia `jev_ask`), da collegare quando c'è un Mac o un export CPU/Linux. Rivalutare a Q1 2027.

## Esito torneo S1 (21/09/2026, 10 match)
greedy batte random 3/3, mirror 2-2/50-50, 0 draw, avg 263 tick (era 218), punteggi 5-10x (es. 119-46, 101-7) per respawn+gold. Tempo 1.2s per 10 match. Demo replay 277KB (era 129KB, ~925B/tick).
Impatto su stack/piano:
- Elo ok (win/loss invariato), ma leaderboard Style da rinormalizzare (margini esplosi)
- replay ok per web oggi, ma prima del mondo persistente serve delta-compression (mandare solo diff, non 40+20+10 pos ogni tick)
- aggiungere `v:1` + map pool (vedi punto 2) prima di S2
- NESSUN cambio di stack (Python+SQLite+Three.js reggono)
