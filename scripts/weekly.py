"""Torneo settimanale Botcraft: top-8 1v1 -> report + commentary + campione homepage.

Uso:  python scripts/weekly.py            # top-8 Elo corrente
      python scripts/weekly.py --names a,b,c,d,e,f,g,h
Cron consigliato (Render Cron / GitHub Actions): ogni venerdì 20:00.
"""
from __future__ import annotations
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.store import leaderboard


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="")
    ap.add_argument("--title", default="weekly")
    args = ap.parse_args()
    if args.names:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
    else:
        import backend.store as _S0
        _S0.init()
        names = [r["name"] for r in leaderboard()[:8]]
    if len(names) < 8:
        import backend.store as _S
        defaults = [("auto-greedy", "greedy"), ("auto-bt", "bt"), ("auto-rush", "greedy"),
                    ("auto-turtle", "greedy"), ("auto-rand", "random"), ("auto-jev", "greedy"),
                    ("auto-llm", "greedy"), ("auto-sq", "squad")]
        for n, p in defaults:
            try:
                _S.register_agent(n, p)
            except Exception:
                pass
            if n not in names:
                names.append(n)
        names = names[:8]
    if len(names) != 8:
        sys.exit(f"servono 8 nomi, trovati {len(names)}: completa con --names")
    from backend.tournaments import run_bracket
    from backend.caster import comment_tournament
    import datetime
    muts = ["", "gold_rush", "no_swords", "fast_gas"]
    mut = muts[datetime.date.today().isocalendar()[1] % len(muts)]
    rep = run_bracket(names, title=args.title, mutator=mut)
    c = comment_tournament(rep)
    d = ROOT / "matches" / f"tourney-{rep['ts']}"
    (d / "commentary.md").write_text(c)
    champ = {"ts": rep["ts"], "title": rep["title"], "champion": rep["champion"],
             "final": {"a": rep["final"]["a"], "b": rep["final"]["b"],
                       "s0": rep["final"]["s0"], "s1": rep["final"]["s1"]},
             "share": f"/viewer/?match=tourney-{rep['ts']}-final"}
    (ROOT / "site" / "champion.json").write_text(json.dumps(champ, indent=2))
    print(f"campione: {rep['champion']} | finale {rep['final']['s0']}-{rep['final']['s1']}")
    print(f"report: matches/tourney-{rep['ts']}/report.json + site/champion.json")


if __name__ == "__main__":
    main()
