# 16 — RESEARCH (web, 22/09/2026): cosa rubiamo, in ordine di valore

Metodo: testa bassa su HF, GitHub, Reddit, YouTube, arXiv. Solo cose cablabili senza rewrite.

## P0 — fatto subito (quick wins implementati)
1. **Glicko-RD sopra Elo** (arXiv CS:GO ratings, TeamUp, chess.com): RD = incertezza che cresce con l'inattività e cala giocando. Perfetto per stagioni e rientri. Libreria `wdm0006/elote` come reference, ma implementiamo noi (zero dipendenze): colonna `rd`, K scalato, decay settimanale. TrueSkill nativo solo se le squadre diventano il formato principale (oggi no: Elo+RD basta al 90%).
2. **Juice economico** (itch.io "juicy", Game Juice 101): danni animati invece di snap (hp smooth già a metà: scale Y — aggiungere lerp), screen-shake sui KO, suoni WebAudio su gather/hit (toggle, muto default), hover su bottoni. 20 righe, 80% del feel.
3. **Bot behavior-tree d'esempio** (HF ML-for-Games, Gigax function-calling): i tiny model (<1B) non ragionano ma completano pattern — architettura giusta = albero comportamentale decide, modello solo flavor. Il nostro `squad_bot` a ruoli è già un BT implicito: esplicitarlo come `bt_bot.py` didattico + `GameSoul-AI-NPC-4B` (Qwen3-4B LoRA, HF NewOrigin) come futuro provider stratega via OpenRouter se economico.
4. **Screeps post-mortem** (Reddit/Lobsters: RCE via console.log, client insicuro, debug lento, dev spariti): valida TUTTE le nostre scelte (mediator senza rete, replay deterministici, feedback <60s, repo attivo). Lezione nuova: **mai eseguire codice altrui nel client** (noi ok: viewer legge solo numeri) + avviso esplicito in docs.

## P1 — prossimo (serve lavoro vero)
5. **AlphaStar league (PFSP + exploiter)**: la nostra ladder è round-robin ingenuo; la lega con main/exploiter agents + matchmaking prioritizzato evita collassi da strategia dominante. Da fare quando 20+ bot attivi.
6. **lmgame-org/GamingAgent (ICLR 2026, MIT, leaderboard HF)**: benchmark standard per agenti LLM nei giochi. Pubblicarci un env Botcraft = marketing gratis verso i researcher.
7. **HF Spaces demo**: come NPC-Playground (Cubzh+Gamax su Spaces): un `app.py` Gradio che fa giocare 2 bot live nel browser senza installare nulla. Conversione istantanea visitatore→giocatore.

## P2 — quando scala
8. **Server dedicato Screeps-style** (`screeps/screeps` standalone, ISC): il nostro compose è già quello; aggiungere server privato scaricabile = community retention.
9. **Bundle/pricing itch.io** (thread 280KB-games: browser-only = meno download ma zero attrito; GIF/video obbligatori sulla pagina): aggiungere trailer webm dalla clip + bundle stagioni.
10. **Tiny on-device** (LFM2.5-2.6B, Qwen2.5-0.5B, Nemotron-4B INT4): flavor/dialoghi locali, MAI decisioni critiche. Rivalutare con laya-coreml.

## Non fare
RL training server-side (costi), Unity/UE (restiamo web), tokenomics/crypto (itch.io ci bannerebbe il tono).
