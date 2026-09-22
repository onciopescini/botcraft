"""Gateway BYOK OpenRouter Botcraft S0 — unico punto che parla con l'esterno.

Regole:
- chiave MAI nello zip agente. Presa da env OPENROUTER_API_KEY o backend/.openrouter_key
- allowlist modelli (free + 2 cheap). Default: modello free.
- budget 6000 token/match, max 80/call, temp 0, timeout 8s HTTP ma 400ms budget tick (il runner taglia a 600ms totali)
- cache per (model,system,user) identici -> 0 token
- logga model+prompt_hash+token in llm_usage.jsonl (mai la chiave)
- senza chiave / rate-limit / down -> raise LLMUnavailable (il bot DEVE fare fallback codice)
"""
from __future__ import annotations
import os
import json
import time
import hashlib
import pathlib
import urllib.request
import urllib.error

ALLOWLIST = {
    "openrouter:meta-llama/llama-3.3-70b-instruct:free",
    "openrouter:google/gemma-2-9b-it:free",
    "openrouter:mistralai/mistral-7b-instruct:free",
    "openrouter:openai/gpt-4o-mini",  # cheap a pagamento, con cap
    "openrouter:anthropic/claude-3-haiku",  # cheap a pagamento, con cap
}
DEFAULT_MODEL = "openrouter:meta-llama/llama-3.3-70b-instruct:free"
MAX_TOKENS_PER_MATCH = 6000
MAX_TOKENS_PER_CALL = 80
TIMEOUT_S = 8


class LLMUnavailable(Exception):
    pass


_cache: dict[str, str] = {}


def _strip_prefix(model: str) -> str:
    return model.split("openrouter:", 1)[1] if model.startswith("openrouter:") else model


def get_key() -> str | None:
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if k:
        return k
    p = pathlib.Path(__file__).resolve().parents[1] / "backend" / ".openrouter_key"
    if p.exists():
        return p.read_text().strip() or None
    return None


def _cache_key(model, system, user, max_tokens) -> str:
    h = hashlib.sha256(f"{model}|{system}|{user}|{max_tokens}".encode()).hexdigest()[:16]
    return h


class Budget:
    """Contatore token per match. Il runner ne crea uno per agente per match."""
    def __init__(self, limit: int = MAX_TOKENS_PER_MATCH):
        self.limit = limit
        self.used = 0

    @property
    def left(self) -> int:
        return self.limit - self.used

    def charge(self, tokens: int):
        self.used += tokens


def llm_ask(system: str, user: str, max_tokens: int = 80,
            model: str | None = None, budget: Budget | None = None,
            log_path: str | None = None) -> str:
    model = model or DEFAULT_MODEL
    if model not in ALLOWLIST:
        raise LLMUnavailable(f"modello non in allowlist: {model}")
    max_tokens = min(max_tokens, MAX_TOKENS_PER_CALL)
    if budget is not None and budget.left < max_tokens:
        raise LLMUnavailable("budget token esaurito")

    ck = _cache_key(model, system, user, max_tokens)
    if ck in _cache:
        return _cache[ck]

    key = get_key()
    if not key:
        raise LLMUnavailable("OPENROUTER_API_KEY mancante (BYOK)")

    body = {
        "model": _strip_prefix(model),
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://botcraft.local",
                 "X-Title": "Botcraft S0"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise LLMUnavailable(f"openrouter http {e.code}") from e
    except Exception as e:
        raise LLMUnavailable(f"openrouter down: {type(e).__name__}") from e

    try:
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens = int(usage.get("total_tokens", max_tokens))
    except Exception as e:
        raise LLMUnavailable("risposta openrouter invalida") from e

    _cache[ck] = text
    if budget is not None:
        budget.charge(tokens)
    if log_path:
        p = pathlib.Path(log_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a") as f:
            f.write(json.dumps({
                "t": time.time(), "model": model,
                "prompt_hash": ck, "tokens": tokens,
                "budget_used": budget.used if budget else tokens,
            }) + "\n")
    return text
