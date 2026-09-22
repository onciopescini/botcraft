"""Bot ibrido esempio: codice per reazioni veloci, LLM ogni 10 tick per strategia.

Se la chiave manca o il budget finisce -> fallback greedy, mai crash.
Per test locale senza spendere: funziona anche senza chiave (fa solo fallback).
"""
import json

try:
    from sdk import llm_ask, LLMUnavailable, Budget
except ImportError:  # esecuzione fuori root
    llm_ask, LLMUnavailable, Budget = None, Exception, None

import greedy_bot

_budget = Budget() if Budget else None
_mode = "rush"  # strategia corrente decisa da LLM
_tick_last_llm = -100

PROMPT = open(__file__.replace("llm_greedy_bot.py", "llm_prompt.txt")).read() if __import__("os").path.exists(__file__.replace("llm_greedy_bot.py", "llm_prompt.txt")) else "Sei il cervello strategico di Botcraft. Rispondi solo con JSON {\"mode\":\"rush\"|\"farm\"}."


def decide(obs: dict) -> dict:
    global _mode, _tick_last_llm
    # reazioni veloci sempre via codice
    enemy = obs.get("enemy", {})
    if enemy.get("visible"):
        ex, ey = enemy["x"], enemy["y"]
        me = obs["self"]
        if abs(ex - me["x"]) + abs(ey - me["y"]) == 1:
            return {"action": "attack"}

    # strategia LLM ogni 10 tick
    if llm_ask and obs["tick"] - _tick_last_llm >= 10:
        _tick_last_llm = obs["tick"]  # backoff anche in caso di errore, evita 300 call/match
        try:
            if _budget and _budget.left < 80:
                raise LLMUnavailable("budget finito")
            txt = llm_ask(
                system=PROMPT,
                user=f"tick {obs['tick']} hp {obs['self']['hp']} wood {obs['self']['wood']} stone {obs['self']['stone']} sword {obs['self']['has_sword']} nearby {len(obs.get('nearby', []))}. rush o farm? Solo JSON.",
                max_tokens=40,
                budget=_budget,
                log_path=f"matches/llm_usage.jsonl",
            )
            mode = json.loads(txt.strip().splitlines()[-1])["mode"]
            if mode in ("rush", "farm"):
                _mode = mode
        except Exception:
            pass  # qualsiasi problema LLM -> resta ultima mode, gioco con codice

    if _mode == "rush" and enemy.get("visible") and obs["self"]["has_sword"]:
        me = obs["self"]
        ex, ey = enemy["x"], enemy["y"]
        dx, dy = ex - me["x"], ey - me["y"]
        if abs(dx) >= abs(dy):
            return {"action": "move_E" if dx > 0 else "move_W"}
        return {"action": "move_S" if dy > 0 else "move_N"}

    return greedy_bot.decide(obs)
