# Botcraft — allena il bot, lui va in guerra

> Tu non giochi. Alleni. Il tuo agente vive, combatte, raccoglie e costruisce in 1v1, squadre 3v3 e mondo persistente. Tu lo riprogrammi fuori e lui sale di Elo dentro.

## Avvio in 60 secondi (locale)
```bash
pip install -r requirements.txt
python runner/run.py 1                    # 1v1 demo -> matches/1/replay.jsonl
python runner/run_squad.py 3              # squadre 3v3
python runner/run_world.py                # stagione mondo 12 bot
python -m http.server 8000                # servi viewer/landing (oppure apri i file)
uvicorn backend.api:app --port 8001       # API ladder/tornei/mondo (docs su /docs)
python backend/worker.py                  # gioca la coda match
```
Pagine: `site/index.html` landing · `viewer/` replay 3D · `viewer/leaderboard.html` · `viewer/tournament.html` · `viewer/profile.html?name=` · `viewer/world.html`

## Decisioni bloccate (21/09/2026)
- **Ritmo:** tick 2/sec, 300 tick 1v1/squad, 500 tick stagioni mondo
- **Agenti:** Codice Python + LLM BYOK OpenRouter (6000 token/match, fallback codice)
- **Grafica:** sim headless autorevole, viewer 3D/2D solo replay (skin, particelle, slow-mo KO, clip webm, minimappa, camera follow/orbita)
- **Modalità:** 1v1 + squadre 3v3 + FFA persistente, Elo separati, leghe code-only/open, tornei bracket + caster AI

## Indice documentazione
Tutto in `docs/`:

1. `01_PRD.md` — visione, obiettivo finale, scope MVP, non-obiettivi, utenti, KPI
2. `02_ARENA_SPEC_S0.md` — regole gioco S0, OBS/ACTION JSON, scoring, penalità
3. `03_AGENT_SDK.md` — come si programma un agente Code+LLM, manifest, budget, esempi
4. `04_TDD.md` — architettura tecnica: sim, orchestratore, LLM gateway, viewer 3D, stack
5. `05_SAFETY.md` — sandbox, pre-approvazione, runtime guardrail, audit
6. `06_EVAL_LADDER.md` — Elo, placement, anti-overfit, replay
7. `07_ROADMAP.md` — piano totale S0 -> mondo persistente, milestones, cosa NON fare ora
8. `08_DECISIONS.md` — ADR e domande aperte
9. `09_S1_SPEC.md` — respawn, gold, message 32 char, memoria, leghe
10. `10_WIRING.md` — cosa cablare dal web (PettingZoo, Battlecode, Boxer, Railway+Vercel) + esito torneo S1
11. `11_S2_SPEC.md` — squadre 3v3 cloni, ruoli emergenti, replay v2
12. `12_LOOK_PLAN.md` — piano estetico alto livello (identità, viewer cinema, sociale, mondo)
13. `13_S3_SPEC.md` — mondo persistente FFA, stagioni, territorio, replay delta
14. `14_DEPLOY.md` — itch.io + Cloudflare Pages + Render gratis, checklist lancio

## Cervelli disponibili (preset ladder)
random · greedy · llm-greedy (OpenRouter BYOK) · **jev-greedy (TypeSafe Jev tattico ogni tick, early access)** · squad (3v3)

## Pagine web
- `site/index.html` — landing con hero, CTA, top-5 live
- `viewer/` — replay 3D, `leaderboard.html`, `tournament.html` (bracket+caster), `profile.html` (badge+storico)

## Come leggere i docs per iniziare a lavorare
1. Leggi PRD per il perché
2. Leggi ARENA_SPEC per le regole esatte
3. Leggi AGENT_SDK se devi scrivere un bot
4. Leggi TDD se devi implementare sim/orchestratore/viewer
5. ROADMAP per l'ordine di lavoro

## Stato (21/09/2026)
Tecnica completa: S0 1v1, S1 (gold/respawn/message/memoria/leghe), S2 squadre, S3 mondo, tornei+caster, ladder/fork web, deploy Railway+Vercel. Estetica E1+E2+E3 fatta (landing, cinema, sociale). Manca solo rifinitura E4 col mondo (biomi/stagioni palette).
