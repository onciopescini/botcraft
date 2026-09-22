"""AI caster Botcraft — commento match/torneo. LLM se c'è chiave, template se no."""
from __future__ import annotations
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm.gateway import llm_ask, LLMUnavailable, Budget

CASTER_PROMPT = ("Sei il caster di Botcraft, arena 1v1 di bot programmati. "
                 "Tono sportivo, 6-10 righe, italiano. Cita tick chiave, errori (miss, bleed, muri sprecati) "
                 "e il momento di svolta. Mai inventare azioni non nei dati. Chiudi con MVP.")


def key_moments(replay_path: str, limit: int = 8) -> list[str]:
    rows = [json.loads(l) for l in pathlib.Path(replay_path).read_text().strip().splitlines() if l.strip()]
    if not rows:
        return []
    out = [f"tick {rows[0]['tick']}: via, {rows[0]['a1']} vs {rows[0]['a2']}"]
    prev_hp = (rows[0]['p1']['hp'], rows[0]['p2']['hp'])
    for r in rows[1:]:
        hp = (r['p1']['hp'], r['p2']['hp'])
        if hp[0] <= 0 or hp[1] <= 0:
            out.append(f"tick {r['tick']}: KO, hp {hp[0]}-{hp[1]} con {r['a1']}/{r['a2']}")
            break
        if prev_hp[0] - hp[0] >= 20 or prev_hp[1] - hp[1] >= 20:
            out.append(f"tick {r['tick']}: colpo pesante ({r['a1']} vs {r['a2']}), hp {hp[0]}-{hp[1]}")
        if (r.get('m1') or r.get('m2')) and (r['m1'] != rows[max(0, rows.index(r) - 1)].get('m1') or True):
            pass
        prev_hp = hp
        if len(out) >= limit:
            break
    last = rows[-1]
    out.append(f"fine tick {last['tick']}: hp {last['p1']['hp']}-{last['p2']['hp']} "
               f"risorse {last['p1']['wood']}+{last['p1']['stone']}+{last['p1'].get('gold', 0)}g vs "
               f"{last['p2']['wood']}+{last['p2']['stone']}+{last['p2'].get('gold', 0)}g")
    return out[:limit]


def comment_match(a: str, b: str, res: dict, replay_path: str) -> str:
    mom = key_moments(replay_path)
    facts = (f"{a} vs {b}, finale {res['s0']}-{res['s1']} winner={res['winner']} "
             f"seed={res.get('seed')} hash={res.get('hash')}\n" + "\n".join(mom))
    try:
        return llm_ask(system=CASTER_PROMPT,
                       user=facts + "\nCommenta come caster, 6-10 righe.",
                       max_tokens=300, budget=Budget(2000))
    except LLMUnavailable:
        winner = a if res['winner'] == 0 else b
        return ("Qui Botcraft Live! " + f"{a} contro {b}, finisce {res['s0']}-{res['s1']}. " +
                " ".join(mom[:4]) + f" MVP: {winner}. " +
                "(Commento template: metti OPENROUTER_API_KEY per il caster LLM.)")


def comment_tournament(report: dict) -> str:
    f = report["final"]
    base = (f"# {report['title']} — campione: {report['champion']}\n\n" +
            f"Finale {f['a']} vs {f['b']}: {f['s0']}-{f['s1']} "
            f"[replay]({f['share']})\n\n")
    try:
        rep_path = ROOT / "matches" / f["replay"]
        body = comment_match(f["a"], f["b"],
                             {"s0": f["s0"], "s1": f["s1"], "winner": f["winner"],
                              "seed": f["seed"], "hash": f["hash"]}, str(rep_path))
    except Exception:
        body = f"MVP del torneo: {report['champion']}."
    return base + body + "\n"
