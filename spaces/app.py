"""Botcraft demo per Hugging Face Spaces — gioca 2 bot nel browser, zero installazioni.

Deploy: nuovo Space (Gradio, free CPU) con questi file: app.py + requirements.txt + README.md.
Copia sim/, bots/, runner/ nella root dello Space oppure pip-installa dal repo.
"""
import io
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sim.sim import new_match, step, to_obs, result
from bots import greedy_bot, random_bot, bt_bot

BOTS = {"greedy": greedy_bot.decide, "random": random_bot.decide, "bt": bt_bot.decide}


def play(a: str = "greedy", b: str = "bt", seed: int = 1):
    st = new_match(seed)
    trail = []
    while not st["over"]:
        o1, o2 = to_obs(st, 0), to_obs(st, 1)
        try:
            r1 = BOTS[a](o1)
        except Exception:
            r1 = {"action": "noop"}
        try:
            r2 = BOTS[b](o2)
        except Exception:
            r2 = {"action": "noop"}
        step(st, r1, r2)
        if st["tick"] % 10 == 0:
            trail.append((st["tick"], st["agents"][0]["hp"], st["agents"][1]["hp"]))
    res = result(st)
    w = "pareggio" if res["winner"] == -1 else (a if res["winner"] == 0 else b)
    md = f"### {a} {res['s0']} — {res['s1']} {b}\n**Vince: {w}** (seed {seed}, {res['tick']} tick)\n"
    plot = _plot(trail, a, b)
    return md, plot


def _plot(trail, a, b):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot([t for t, _, _ in trail], [h for _, h, _ in trail], label=a)
    ax.plot([t for t, _, _ in trail], [h for _, _, h in trail], label=b)
    ax.set_xlabel("tick")
    ax.set_ylabel("hp")
    ax.legend()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


try:
    import gradio as gr

    demo = gr.Interface(
        fn=play,
        inputs=[gr.Dropdown(["greedy", "bt", "random"], value="greedy", label="bot blu"),
                gr.Dropdown(["greedy", "bt", "random"], value="bt", label="bot rosso"),
                gr.Slider(1, 999, value=1, step=1, label="seed")],
        outputs=[gr.Markdown(label="risultato"), gr.Plot(label="hp nel tempo")],
        title="Botcraft — arena bot programmabili",
        description="Due bot si scontrano, tu guardi. Il gioco completo (ladder, squadre, mondo 3D) è su botcraft.pages.dev",
    )
    if __name__ == "__main__":
        demo.launch()
except ImportError:
    print("pip install gradio matplotlib per la demo Spaces")
