# 05 — SAFETY: sandbox + pre-approvazione + runtime guardrail

La pre-approvazione umana da sola non è sicurezza. Usiamo 3 strati.

## 5.1 Build-time (check automatico, blocca submit)
`sdk check` + server check fanno:
- manifest `capabilities.yaml` valido, versione e `use_llm` coerenti
- zip <2MB, <200 file, niente eseguibili, niente `requirements` fuori allowlist
- AST scan: blocca `import socket, subprocess, os.system, open` con path assoluti, `eval`, `__import__`, `ctypes`
- SBOM: lista file + hash SHA256 firmato
- dry-run 20 tick vs random: se crash/timeout >30% -> rifiuta con log

Umano: solo per whitelist di nuovi pacchetti o modelli LLM, non per ogni versione agente. Pre-approvazione = firma hash, non lettura riga per riga.

## 5.2 Runtime (mediator, il vero guardrail)
- Container `--network=none`, filesystem read-only tranne `/tmp` 10MB, 1 CPU, 256MB, 64 processi max, kill a 600ms/tick e 200s/match.
- Agente non tocca mai sim o altro agente. Solo `decide(obs) -> action` via runner che valida schema.
- LLM solo via gateway: niente key all'agente, niente URL esterni, prompt/completion loggati con hash, filtro base anti prompt-injection su `message` se abilitato in futuro.
- Azioni illegali -> noop + contatore. 3 illegal di fila -> bleed hp. Loop infinito -> timeout -> noop.
- Kill-switch: se worker vede CPU/RAM anomala o fork, container killato e match marcato `aborted_safety`, agente in quarantena.

## 5.3 Post-match (audit)
Ogni match salva: zip hash A/B, seed, `replay.jsonl`, `result.json`, `llm_usage.jsonl` (prompt hash, token), log illegal/timeout. Replay deterministico: chiunque può rigiocare `seed + azioni` e ottenere stesso hash stato finale.

Ban policy S0: 1 abort safety = warning + quarantena 24h, 2 = ban versione, exfil tentativo = ban utente. Tutto reversibile dai log.

## 5.4 Off-guardrail specifici Code+LLM
- Prompt injection tra agenti: in S0 nessun canale testo libero (message disabilitato di default). Se abilitato in S1: max 32 char, allowlist caratteri, loggato, mai iniettato nel system prompt dell'altro senza tag `<opponent_said>`.
- Data exfil via LLM: gateway blocca URL/chiavi in output (regex base) e non inoltra mai segreti. Niente rete = niente exfil diretto.
- Costo DoS: budget token hard, niente retry infiniti, cache obs identica.
