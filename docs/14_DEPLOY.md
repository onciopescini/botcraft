# 14 — DEPLOY (itch.io + Cloudflare Pages + Render), gratis

## 1. Gioco su itch.io (botcraft.itch.io/botcraft)
1. `python runner/run.py 1` per rigenerare `viewer/demo.jsonl` (già v1/v2-compatibile)
2. Zippa `viewer/` + `site/assets/` -> `botcraft-itch.zip` (index.html in root dello zip!)
   - itch.io vuole index.html in root: copia `viewer/index.html` come `index.html` dello zip
3. Nuovo progetto HTML su https://itch.io/game/new, upload zip, spunta "This file will be played in the browser", viewport 1280x720
4. Link: `https://botcraft.itch.io/botcraft`

## 2. Landing su Cloudflare Pages (botcraft.pages.dev)
1. Repo su GitHub, connetti https://pages.cloudflare.com
2. Build: nessuno (statico). Root: `site/`, oppure `viewer/` per il gioco diretto
3. Env: niente. Link: `https://botcraft.pages.dev`

## 3. API su Render (botcraft.onrender.com)
1. Connetti repo su https://render.com, New Web Service, legge `render.yaml` + `Dockerfile`
2. Secret: `OPENROUTER_API_KEY`, `TYPESAFE_API_KEY` (waitlist), `API_TOKENS` (genera con `python -c "import secrets; print(secrets.token_hex(16))"`)
3. Aggiorna `CORS_ORIGINS` con i due link sopra. Nota free-tier: dorme dopo 15 min (primo load ~30s), Postgres gratis 30gg poi SQLite su disco (ok per playtest, backup con download periodico)
4. Healthcheck: `GET /leaderboard` deve dare 200

## Chiavi AI (BYOK, mai nel repo)
Dove metterle — 3 opzioni, in ordine di facilità:
1. **Locale:** `python sdk/setup_keys.py` (ti chiede le key senza mostrarle, le salva in `backend/.*_key`, verifica con `--check`)
2. **Env:** `VERCEL_AI_GATEWAY_KEY` / `TYPESAFE_API_KEY` / `OPENROUTER_API_KEY`
3. **Render:** dashboard servizio → Environment → add secret (stessi nomi)
- `VERCEL_AI_GATEWAY_KEY` — Jev tattico via Vercel AI Gateway (gratis finché Jev è free, `JEV_PROVIDER=vercel`)
- `TYPESAFE_API_KEY` — alternativa diretta waitlist typesafe.ai (`JEV_PROVIDER=typesafe`)
- `OPENROUTER_API_KEY` — LLM stratega (10$ consigliati, modelli :free)
- `API_TOKENS` — genera con `python -c "import secrets; print(secrets.token_hex(16))"`

## Checklist lancio
- [ ] `python tests/smoke.py` verde
- [ ] demo.jsonl rigenerata
- [ ] API_TOKENS generato e salvato in password manager
- [ ] waitlist typesafe.ai per Jev (opzionale al lancio: fallback greedy attivo)
- [ ] 5 inviti con: link gioco + `sdk check` + 3 task (registra bot, leggi Elo, manda replay)
