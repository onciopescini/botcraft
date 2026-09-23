"""sdk check — valida un agente in locale prima del submit. Uso: python sdk/check.py ./my-agent"""
from __future__ import annotations
import ast
import sys
import time
import pathlib

BLOCKED_IMPORTS = {
    "socket", "subprocess", "ctypes", "multiprocessing", "threading",
    "os", "sys", "pathlib", "shutil", "importlib", "inspect", "marshal",
    "pickle", "cPickle", "base64", "urllib", "http", "ftplib", "smtplib",
    "telnetlib", "xmlrpc", "pydoc", "code", "codeop", "runpy", "pkgutil",
    "imp", "pty", "tty", "glob", "signal", "atexit", "webbrowser",
}
BLOCKED_CALLS = {"eval", "exec", "__import__", "compile",
                 "getattr", "setattr", "delattr",
                 "breakpoint", "exit", "quit", "help", "input",
                 "memoryview", "globals", "locals", "vars", "dir"}
WARN_CALLS = {"open", "hasattr"}  # open: ok in lettura (fs read-only in sandbox), mai per chiavi
BLOCKED_ATTRS = {"__class__", "__bases__", "__subclasses__", "__mro__",
                 "__dict__", "__builtins__", "__globals__", "__code__",
                 "__closure__", "__func__", "__self__",
                 "gi_frame", "f_locals", "f_globals", "f_builtins"}
ALLOWED_DEPS = {"", "numpy"}


def scan(path: pathlib.Path):
    """Ritorna (errori, warning). Errori = rifiuto, warning = ammesso con log."""
    src = path.read_text()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"sintassi invalida: {e}"], []
    errors, warnings = [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            else:
                if node.module:
                    mods = [node.module.split(".")[0]]
            for m in mods:
                if m in BLOCKED_IMPORTS:
                    errors.append(f"import vietato: {m} riga {node.lineno}")
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
            if name in BLOCKED_CALLS:
                errors.append(f"chiamata vietata: {name} riga {node.lineno}")
            elif name in WARN_CALLS:
                warnings.append(f"lettura file riga {node.lineno}: ok solo lettura, mai chiavi")
        if isinstance(node, ast.Attribute) and node.attr in BLOCKED_ATTRS:
            errors.append(f"attributo vietato: {node.attr} riga {node.lineno}")
    low = src.lower()
    if "openrouter_api_key" in low or "typesafe_api_key" in low or "vercel_ai_gateway_key" in low or "api_key" in low or "secret" in low:
        errors.append("chiave/secret dentro il codice: mettila nel profilo, mai nello zip")
    return errors, warnings


def check_requirements(root: pathlib.Path):
    req = root / "requirements.txt"
    if not req.exists():
        return []
    bad = []
    for line in req.read_text().splitlines():
        line = line.strip().lower()
        if not line or line.startswith("#"):
            continue
        pkg = __import__("re").split(r"[<>=!~\s\[]", line)[0]
        if pkg not in ALLOWED_DEPS:
            bad.append(f"dipendenza vietata: {line} (ammesse: nessuna o numpy)")
    return bad


def main(agent_dir: str):
    root = pathlib.Path(agent_dir)
    agent_py = root / "agent.py"
    cap = root / "capabilities.yaml"
    if not agent_py.exists():
        print("MANCA agent.py"); return 2
    if not cap.exists():
        print("MANCA capabilities.yaml"); return 2
    errs, warns = scan(agent_py)
    for w in check_requirements(root):
        errs.append(w)
    if errs:
        print("SCAN FALLITO:"); [print(" -", e) for e in errs]; return 2
    for w in warns:
        print("warning:", w)
    print("scan ok: nessun import vietato")
    # dry-run 20 tick vs random
    sys.path.insert(0, str(root))
    sys.path.insert(0, "bots")
    ROOT = pathlib.Path(".").resolve()
    sys.path.insert(0, str(ROOT))
    import importlib.util
    spec = importlib.util.spec_from_file_location("user_agent", str(agent_py))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from sim.sim import new_match, step, to_obs
    import random_bot
    state = new_match(123)
    t0 = time.time()
    timeouts = 0
    for _ in range(20):
        obs = to_obs(state, 0)
        try:
            t = time.time()
            a = mod.decide(obs)
            if time.time() - t > 0.6:
                timeouts += 1
                a = {"action": "noop"}
        except Exception as e:
            print(f"decide ha lanciato eccezione: {e}")
            return 2
        if not isinstance(a, dict) or "action" not in a:
            print(f"output invalido: {a}")
            return 2
        step(state, a, random_bot.decide(to_obs(state, 1)))
    dt = (time.time() - t0) / 20 * 1000
    print(f"dry-run 20 tick ok, media {dt:.1f}ms/tick, timeout {timeouts}")
    if dt > 500:
        print("WARNING: troppo lento, in gara scatterà noop")
    print("PRONTO PER SUBMIT")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
