"""Balance dashboard: winrate per preset da matches finiti + alert meta >65%."""
from __future__ import annotations
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.store import connect


def main():
    con = connect()
    rows = con.execute("SELECT a,b,winner,mode FROM matches WHERE status='done'").fetchall()
    con.close()
    stats = {}
    for r in rows:
        for side, opp in (("a", "b"), ("b", "a")):
            w = "W" if (r["winner"] == 0 and side == "a") or (r["winner"] == 1 and side == "b") else ("D" if r["winner"] == -1 else "L")
            key = (r["mode"],)
            stats.setdefault(key, []).append(w)
    print(f"match analizzati: {len(rows)}")
    # per preset servono i preset: join agents
    con = connect()
    mx = {}
    for r in rows:
        pa = con.execute("SELECT preset FROM agents WHERE name=?", (r["a"],)).fetchone()
        pb = con.execute("SELECT preset FROM agents WHERE name=?", (r["b"],)).fetchone()
        pa = pa["preset"] if pa else "?"
        pb = pb["preset"] if pb else "?"
        for me, you, wside in ((pa, pb, 0), (pb, pa, 1)):
            w = r["winner"] == wside
            d = r["winner"] == -1
            k = (me, you, r["mode"])
            s = mx.setdefault(k, [0, 0, 0])
            s[0 if w else (1 if d else 2)] += 1
    con.close()
    alert = False
    con = connect()
    for (me, you, mode), (w, d, l) in sorted(mx.items()):
        tot = w + d + l
        if tot >= 3:
            # atteso da Elo medi correnti dei due preset
            ea = con.execute("SELECT AVG(elo) e FROM agents WHERE preset=?", (me,)).fetchone()["e"] or 1200
            eb = con.execute("SELECT AVG(elo) e FROM agents WHERE preset=?", (you,)).fetchone()["e"] or 1200
            exp = 1.0 / (1.0 + 10 ** ((eb - ea) / 400))
            wr = w / tot
            dev = abs(wr - exp)
            flag = "  <-- SOSPETTO (reale lontano da atteso Elo)" if dev > 0.25 else ""
            if dev > 0.25:
                alert = True
            print(f"{mode:6s} {me:10s} vs {you:10s}: {w}W {d}D {l}L reale={wr:.0%} atteso={exp:.0%}{flag}")
    con.close()
    print("BALANCE OK" if not alert else "SQUILIBRIO: rivedere costi/danni")


if __name__ == "__main__":
    main()
