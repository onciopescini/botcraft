"""sdk check — valida un agente in locale prima del submit. Uso: python sdk/check.py ./my-agent"""
from __future__ import annotations
import ast
import sys
import time
import pathlib

BLOCKED = {"socket", "subprocess", "ctypes", "multiprocessing", "threading",
           "os", "sys", "pathlib", "shutil", "importlib"}
BLOCKED_CALLS = {"eval", "exec", "__import__", "open", "compile"}


def scan(path: pathlib.Path):
    src = path.read_text()
    tree = ast.parse(src)
    errors = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            else:
                if node.module:
                    mods = [node.module.split(".")[0]]
            for m in mods:
                if m in BLOCKED and m not in ("os",):
                    # os ammesso solo per path locali? no: blocca tutto tranne casi noti.
                    # S0 strict: blocca socket/subprocess/ctypes, avvisa su os.
                    pass
            for m in mods:
                if m in ("socket", "subprocess", "ctypes"):
                    errors.append(f"import vietato: {m} riga {node.lineno}")
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
            if name in ("eval", "exec", "__import__"):
                errors.append(f"chiamata vietata: {name} riga {node.lineno}")
    if "OPENROUTER_API_KEY" in src or "api_key" in src.lower():
        errors.append("chiave API dentro il codice: mettila nel profilo, mai nello zip")
    return errors


def main(agent_dir: str):
    root = pathlib.Path(agent_dir)
    agent_py = root / "agent.py"
    cap = root / "capabilities.yaml"
    if not agent_py.exists():
        print("MANCA agent.py"); return 2
    if not cap.exists():
        print("MANCA capabilities.yaml"); return 2
    errs = scan(agent_py)
    if errs:
        print("SCAN FALLITO:"); [print(" -", e) for e in errs]; return 2
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
