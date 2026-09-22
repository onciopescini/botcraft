"""Gateway Jev (TypeSafe AI, System One) — decisioni tipizzate in 70-500ms, zero allucinazioni.

Docs: https://typesafe.ai/blog/introducing-system-one-models-and-jev
Provider:
  - typesafe (default): POST https://api.typesafe.ai/v1/systemone, chiave TYPESAFE_API_KEY
  - vercel (AI Gateway, gratis finché Jev è free): POST /v1/evaluate,
    model typesafe-ai/jev, chiave VERCEL_AI_GATEWAY_KEY. Risposte in answers.
  - local (futuro, solo macOS Apple Silicon): laya-coreml in locale, ~5ms,
    zero rete/chiavi. Slot pronto (JEV_PROVIDER=local), backend da collegare.
  Seleziona con env JEV_PROVIDER=typesafe|vercel|local (default: vercel se c'è la sua chiave, altrimenti typesafe).
  Chiavi MAI nello zip. Senza chiave -> LLMUnavailable (fallback codice).

Uso tattico (ogni tick, dentro i 600ms):
    from sdk import jev_ask
    d = jev_ask(state=f"hp {hp} ...", questions={
        "action": {"type": "choice", "options": ["move_N","move_S","move_E","move_W","gather","attack","noop"],
                   "instructions": "mossa tattica Botcraft"},
        "confidence_ok": {"type": "boolean", "instructions": "fiducia alta?"},
    }, budget=budget)
    # -> {"action": {"value": "gather", "confidence": 0.91}, ...}
"""
from __future__ import annotations
import os
import json
import time
import hashlib
import pathlib
import urllib.request
import urllib.error

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
VERCEL_ENDPOINT = "https://ai-gateway.vercel.sh/v1/evaluate"
MODEL = "jev-latest"
VERCEL_MODEL = "typesafe-ai/jev"
TIMEOUT_S = 4  # resta dentro i 600ms/tick con margine
CONF_THRESHOLD = 0.8  # sotto: il chiamante scala a LLM/euristica

_cache: dict[str, dict] = {}


class LLMUnavailable(Exception):
    pass


def _has_vercel_key() -> bool:
    if os.environ.get("VERCEL_AI_GATEWAY_KEY", "").strip():
        return True
    p = pathlib.Path(__file__).resolve().parents[1] / "backend" / ".vercel_key"
    return p.exists() and bool(p.read_text().strip())


def provider() -> str:
    p = os.environ.get("JEV_PROVIDER", "").strip().lower()
    if p in ("typesafe", "vercel", "local"):
        return p
    if _has_vercel_key():
        return "vercel"
    return "typesafe"


def get_key() -> str | None:
    if provider() == "vercel":
        k = os.environ.get("VERCEL_AI_GATEWAY_KEY", "").strip()
        if k:
            return k
        p = pathlib.Path(__file__).resolve().parents[1] / "backend" / ".vercel_key"
        if p.exists():
            return p.read_text().strip() or None
        return None
    k = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if k:
        return k
    p = pathlib.Path(__file__).resolve().parents[1] / "backend" / ".typesafe_key"
    if p.exists():
        return p.read_text().strip() or None
    return None


def _ckey(state, questions) -> str:
    return hashlib.sha256(json.dumps([state, questions], sort_keys=True).encode()).hexdigest()[:16]


def _call_typesafe(key: str, state, questions: dict):
    body = {"model": MODEL, "state": state, "questions": questions}
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        data = json.loads(resp.read().decode())
    return _norm_answers(data.get("decisions", data)), MODEL


def _norm_answers(answers: dict) -> dict:
    """Normalizza risposte provider -> {q: {value, confidence}}."""
    out = {}
    for q, a in (answers or {}).items():
        if not isinstance(a, dict):
            out[q] = {"value": a, "confidence": 0.0}
            continue
        if "value" in a or "confidence" in a:
            out[q] = {"value": a.get("value"), "confidence": float(a.get("confidence", 0) or 0)}
            continue
        if a.get("type") == "choice":
            ch = a.get("choice")
            probs = a.get("probabilities", {}) or {}
            try:
                conf = float(probs.get(ch, 0)) if ch else 0.0
            except Exception:
                conf = 0.0
            out[q] = {"value": ch, "confidence": conf}
            continue
        if a.get("type") == "boolean":
            prob = a.get("probability", a.get("confidence", 0))
            val = a.get("value", prob >= 0.5 if isinstance(prob, (int, float)) else None)
            out[q] = {"value": val, "confidence": float(prob or 0)}
            continue
        if a.get("type") == "score":
            out[q] = {"value": a.get("score", a.get("value")), "confidence": float(a.get("probability", 0) or 0)}
            continue
        out[q] = {"value": a.get("choice", a.get("value")), "confidence": float(a.get("probability", a.get("confidence", 0)) or 0)}
    return out


ACTION_DESCRIPTIONS = {
    "move_N": "vai a nord di una cella",
    "move_S": "vai a sud di una cella",
    "move_E": "vai a est di una cella",
    "move_W": "vai a ovest di una cella",
    "gather": "raccogli la risorsa adiacente",
    "attack": "attacca il nemico adiacente",
    "craft_sword": "costruisci la spada con 3 legno e 2 pietra",
    "craft_wall_kit": "costruisci un kit muro con 2 pietra",
    "craft_stick": "costruisci un bastone con 2 legno",
    "place_wall": "piazza un muro nella cella vicina",
    "message": "invia un messaggio corto",
    "noop": "resta fermo e passa il turno",
}


def _call_vercel(key: str, state, questions: dict):
    """Vercel AI Gateway evaluation API: POST /v1/evaluate {model, state, questions}.
    Domande choice con criteria {opzione: descrizione}."""
    vq = {}
    for name, q in questions.items():
        q = dict(q or {})
        if q.get("type") == "choice" and "criteria" not in q:
            opts = q.get("options", [])
            q["criteria"] = {o: ACTION_DESCRIPTIONS.get(o, o) for o in opts}
            q.pop("options", None)
        vq[name] = q
    body = {"model": VERCEL_MODEL, "state": state, "questions": vq}
    req = urllib.request.Request(
        VERCEL_ENDPOINT, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        data = json.loads(resp.read().decode())
    return _norm_answers(data.get("answers", {})), VERCEL_MODEL


def jev_ask(state, questions: dict, budget=None, log_path: str | None = None) -> dict:
    ck = _ckey(state if isinstance(state, str) else json.dumps(state, sort_keys=True), questions)
    if ck in _cache:
        return _cache[ck]
    prov = provider()
    if prov == "local":
        raise LLMUnavailable("provider local non ancora collegato (serve macOS + laya-coreml, vedi docs/10_WIRING.md)")
    key = get_key()
    if not key:
        raise LLMUnavailable("chiave Jev mancante (VERCEL_AI_GATEWAY_KEY o TYPESAFE_API_KEY)")
    t0 = time.time()
    try:
        out, model = _call_vercel(key, state, questions) if prov == "vercel" else _call_typesafe(key, state, questions)
    except urllib.error.HTTPError as e:
        raise LLMUnavailable(f"jev/{prov} http {e.code}") from e
    except (LLMUnavailable, KeyError, ValueError, json.JSONDecodeError) as e:
        raise LLMUnavailable(f"jev/{prov} risposta invalida") from e
    except Exception as e:
        raise LLMUnavailable(f"jev/{prov} down: {type(e).__name__}") from e
    dt = (time.time() - t0) * 1000
    if dt > 1500:
        raise LLMUnavailable(f"jev lento {dt:.0f}ms > 1500ms")
    _cache[ck] = out
    if budget is not None and hasattr(budget, "charge"):
        budget.charge(1)  # Jev costa per chiamata ~zero: contiamo 1 token simbolico
    if log_path:
        p = pathlib.Path(log_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a") as f:
            f.write(json.dumps({"t": time.time(), "model": model, "prov": prov, "hash": ck, "ms": round(dt)}) + "\n")
    return out


def confident_enough(decision: dict, threshold: float = CONF_THRESHOLD) -> bool:
    try:
        return float(decision.get("confidence", 0)) >= threshold
    except Exception:
        return False
