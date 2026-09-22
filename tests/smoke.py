import sys
sys.path.insert(0, '.')
ok = []
def check(name, fn):
    try:
        fn()
        ok.append(f"OK {name}")
    except Exception as e:
        ok.append(f"FAIL {name}: {type(e).__name__}: {e}")

def t_sim():
    from sim.sim import new_match, step
    s = new_match(1)
    step(s, {"action": "gather"}, {"action": "noop"})
def t_squad():
    from sim.squad import new_match_squad, step_squad
    s = new_match_squad(1)
    step_squad(s, [{"action": "noop"}] * 6)
def t_world():
    from sim.world import new_world, step_world
    s = new_world(1, ["a", "b"])
    step_world(s, {})
def t_pz():
    from sim.pettingzoo_wrapper import BotcraftParallel
    e = BotcraftParallel(1)
    e.reset()
    e.step({"p1": {"action": "noop"}, "p2": {"action": "noop"}})
def t_api():
    from fastapi.testclient import TestClient
    from backend.api import app
    c = TestClient(app)
    assert c.get("/leaderboard").status_code == 200
    assert c.get("/tournaments").status_code == 200
    assert c.get("/world/seasons").status_code == 200
def t_viewer():
    import subprocess
    r = subprocess.run(["node", "--check", "viewer/viewer.js"], capture_output=True)
    assert r.returncode == 0
def t_gateway():
    from llm.gateway import Budget
    b = Budget(10)
    assert b.left == 10

for n, f in [("sim1v1", t_sim), ("squad", t_squad), ("world", t_world), ("pettingzoo", t_pz), ("api", t_api), ("viewer", t_viewer), ("gateway", t_gateway)]:
    check(n, f)
print("\n".join(ok))
fails = [l for l in ok if l.startswith("FAIL")]
print("SMOKE:", "TUTTO VERDE" if not fails else f"{len(fails)} FALLIMENTI")
sys.exit(1 if fails else 0)
