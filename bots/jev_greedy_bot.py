"""Bot jev-greedy: Jev comandante ASINCRONO ogni 10 tick + codice per-tick (mai bloccante).

Perché async: Jev reale risponde in 500-750ms, oltre il budget 600ms/tick.
Il tick non aspetta mai: ogni 10 tick lancia la domanda in background e continua
greedy; quando la risposta arriva, la mode si aggiorna. Match veloci + cervello Jev.
Senza chiave: greedy puro (il primo fail attiva il circuit-breaker).
"""
import greedy_bot

try:
    from sdk import jev_ask, Budget
    from llm.jev_gateway import LLMUnavailable
except ImportError:
    jev_ask, Budget, LLMUnavailable = None, None, Exception

from concurrent.futures import ThreadPoolExecutor  # noqa (tenuto per compatibilità)
import threading

_budget = Budget(6000) if Budget else None
_mode = "farm"
_tick_last = -100
_fails = 0
_off_until = -1
# thread daemon: non trattengono mai l'uscita del processo
_thr = None
_thr_result = None
_thr_done = True

MODES = {
    "rush": "dai la caccia al nemico con la spada",
    "farm": "raccogli risorse e costruisci la spada",
    "turtle": "resta vicino al centro e difendi il totem",
}


def _ask_bg(state_txt):
    global _thr_result, _thr_done
    try:
        _thr_result = jev_ask(
            state=state_txt,
            questions={"mode": {"type": "choice",
                                "instructions": "strategia squadra Botcraft",
                                "criteria": MODES}},
            budget=_budget,
            log_path="matches/jev_usage.jsonl",
        )
    except Exception as e:
        _thr_result = e
    finally:
        _thr_done = True


def _thr_alive():
    return _thr is not None and _thr.is_alive()


def decide(obs: dict) -> dict:
    global _mode, _tick_last, _fails, _off_until, _thr, _thr_result, _thr_done
    me = obs["self"]
    enemy = obs.get("enemy", {})
    if obs["tick"] == 0:
        _fails = 0
        _off_until = -1
    # reazioni critiche via codice
    if enemy.get("visible") and abs(enemy["x"] - me["x"]) + abs(enemy["y"] - me["y"]) == 1:
        if me["hp"] <= 25 or me["has_sword"]:
            return {"action": "attack"}
    # raccogli risposta async pronta
    if _thr is not None and not _thr.is_alive() and not _thr_done:
        _thr_done = True
        r = _thr_result
        if isinstance(r, Exception):
            _fails += 1
        else:
            try:
                m = ((r or {}).get("mode", {}) or {})
                if m.get("value") in MODES and float(m.get("confidence", 0)) >= 0.6:
                    _mode = m["value"]
                    _fails = 0
                else:
                    _fails += 1
            except Exception:
                _fails += 1
        if _fails >= 3:
            _off_until = obs["tick"] + 100
            _fails = 0
    # lancia domanda ogni 10 tick se canale libero
    if (jev_ask and _thr_done and obs["tick"] - _tick_last >= 10
            and obs["tick"] >= _off_until):
        _tick_last = obs["tick"]
        _thr_done = False
        _thr_result = None
        try:
            _thr = threading.Thread(
                target=_ask_bg,
                args=(f"tick {obs['tick']} hp {me['hp']} wood {me['wood']} stone {me['stone']} "
                      f"gold {me.get('gold', 0)} sword {me['has_sword']} nearby {len(obs.get('nearby', []))} "
                      f"enemy_visible {enemy.get('visible', False)}",),
                daemon=True)
            _thr.start()
        except Exception:
            _thr_done = True
    # esecuzione mode via codice
    if _mode == "rush" and enemy.get("visible"):
        ex, ey = enemy["x"], enemy["y"]
        dx, dy = ex - me["x"], ey - me["y"]
        if abs(dx) + abs(dy) == 1:
            return {"action": "attack"}
        if me["has_sword"] or me["hp"] > 60:
            if abs(dx) >= abs(dy):
                return {"action": "move_E" if dx > 0 else "move_W"}
            return {"action": "move_S" if dy > 0 else "move_N"}
    if _mode == "turtle" and obs["tick"] > 50:
        if abs(16 - me["x"]) + abs(16 - me["y"]) > 6:
            dx, dy = 16 - me["x"], 16 - me["y"]
            if abs(dx) >= abs(dy):
                return {"action": "move_E" if dx > 0 else "move_W"}
            return {"action": "move_S" if dy > 0 else "move_N"}
    return greedy_bot.decide(obs)
