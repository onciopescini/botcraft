# 03 — AGENT SDK (Code + LLM)

Target: Python 3.11, nessun internet a runtime. Il tuo agente è una funzione pura + opzionale chiamata LLM via gateway.

## 3.1 Struttura submit
```
agent.zip
  agent.py         # obbligatorio, definisce decide(obs: dict) -> dict
  prompt.txt       # opzionale, system prompt se usi LLM
  capabilities.yaml# obbligatorio, manifest
  requirements.txt # opzionale, solo allowlist (es. numpy). Niente nuove dipendenze in S0, ma formato già previsto.
```

`capabilities.yaml` esempio:
```yaml
name: my-rusher-v2
entrypoint: agent:decide
runtime: python311
use_llm: true
llm_model: openrouter:meta-llama/llama-3.3-70b-instruct:free # id OpenRouter scelto dal giocatore
max_llm_tokens_per_match: 6000
max_ram_mb: 128
version: 2
```

Se `use_llm: false`, `llm_tokens` ignorati e match gratis e più veloce. Se `use_llm: true` devi avere una chiave OpenRouter salvata nel profilo (BYOK) — mai dentro lo zip.

## 3.2 Contratto decide
```python
# agent.py
def decide(obs: dict) -> dict:
    # obs come da ARENA_SPEC
    # devi ritornare in <600ms, altrimenti noop
    if obs["self"]["hp"] < 30:
        return {"action": "move_N"}  # placeholder scappa
    return {"action": "gather"}
```

Regole:
- Solo stdlib + numpy. No `os`, `socket`, `subprocess`, `open` fuori `/tmp` (bloccati a runtime).
- No stato globale persistente tra tick oltre variabili in memoria (resettate a ogni match). Memoria tra match in S1.
- Eccezioni = noop + illegal loggato. Non crasha mai il sim.

## 3.3 Uso LLM (ibrido BYOK via OpenRouter)
Non chiami OpenRouter direttamente. Chiami il gateway interno. La tua chiave OpenRouter resta salvata nel profilo server (cifrata), l'agente non la vede mai.

Modello operativo S0: consigliamo di mettere 10$ su OpenRouter e usare i modelli `:free`. Il gateway lascia passare solo allowlist di modelli (free + 2-3 cheap a pagamento con cap). Se la chiave manca / è scarica / rate-limit -> `LLM_UNAVAILABLE` e devi fare fallback codice.
```python
from sdk import llm_ask  # fornito da noi a runtime

def decide(obs):
    if obs["budget"]["llm_tokens_left"] < 500:
        return {"action": "gather"}  # fallback codice quando finisci budget
    # llm_ask è sincrono, conta nel timeout 600ms e nel budget token
    plan = llm_ask(
        system=open("prompt.txt").read(),  # precaricato, esempio
        user=f"tick {obs['tick']} hp {obs['self']['hp']} nearby {obs['nearby']}. Rispondi solo con una azione JSON.",
        max_tokens=80,
        temperature=0
    )
    # DEVONO validare l'output: se LLM allucina, fallback
    try:
        import json
        a = json.loads(plan)
        assert a["action"] in ["move_N","move_S","move_E","move_W","gather","attack","noop","craft_sword","place_wall","craft_stick","craft_wall_kit"]
        return a
    except:
        return {"action": "noop"}
```

Budget S0 proposto: 6000 token/match/agente, max 80 token/tick, temperature 0, timeout LLM 400ms (dentro i 600ms totali). Se sfori -> auto-noop. Costi loggati in `llm_usage.jsonl` per match.

Pattern consigliato: **codice per reazioni veloci, LLM ogni 10 tick per strategia.** Esempio: muovi/gather via FSM, ogni 10 tick chiedi a LLM "rusho o farmo?".

## 3.4 Bot di esempio da fornire in S0
- `bots/random`: ritorna azione random valida.
- `bots/greedy`: se nemico adiacente e sword -> attack, se adiacente a risorsa -> gather, altrimenti BFS verso tree/rock più vicino, se ha 3w+2s -> craft_sword, se tick>250 -> vai al centro.

Questi due servono per testare sim, Elo e viewer senza LLM.

## 3.5 Pre-approvazione locale (prima di submit)
`sdk check ./my-agent` valida yaml, prova 20 tick contro random, misura tempo, blocca import vietati.

## 3.6 Stato 23/09 (aggiunte dopo MVP)
- Preset: random|greedy|llm-greedy (OpenRouter BYOK)|jev-greedy (Jev async ogni 10 tick)|squad|bt (behavior-tree didattico).
- `obs["coach"]` (ping pre-match), `obs["memory"]` (10KB+bonus livelli), `obs["gas_radius"]`, gold x3, bounty +5 su leader, sudden death ultimi 1/6.
- Modi: 1v1 (300), blitz (60, Elo separato), squad 3v3, daily seed unico, mondo FFA.
- Progressione: XP/livelli/memoria+ping bonus, prompt pack a coin, coin scommesse pari-mutuel.
