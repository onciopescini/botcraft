"""Release Botcraft in 1 comando: python scripts/release.py
Fa: smoke test -> rigenera demo -> zip itch.io (index in root) -> stampa checklist.
"""
from __future__ import annotations
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, **kw):
    print("$", " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT, **kw)
    if r.returncode != 0:
        sys.exit(f"FALLITO: {' '.join(cmd)}")


def main():
    run([sys.executable, "tests/smoke.py"])
    run([sys.executable, "runner/run.py", "1"])
    shutil.copy(ROOT / "matches" / "1" / "replay.jsonl", ROOT / "viewer" / "demo.jsonl")
    # itch.io vuole index.html in root dello zip
    out = ROOT / "botcraft-itch.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted((ROOT / "viewer").rglob("*")):
            if p.is_file() and p.name not in ("demo.jsonl", "demo.jsonl.bak"):
                z.write(p, p.relative_to(ROOT / "viewer"))
        z.write(ROOT / "viewer" / "demo.jsonl", "demo.jsonl")
    print(f"\nOK: {out} ({out.stat().st_size // 1024} KB)")
    print("""
CHECKLIST LANCIO (tocca a te):
[ ] itch.io/game/new -> upload botcraft-itch.zip, "played in browser", 1280x720
[ ] Cloudflare Pages -> repo, root site/ -> botcraft.pages.dev
[ ] Render -> repo, render.yaml, secret OPENROUTER/VERCEL/API_TOKENS, CORS con i 2 link
[ ] GET https://<tua-api>/health -> {"ok": true}
[ ] 5 inviti: link gioco + sdk check + 3 task (bot, Elo, replay)
""")


if __name__ == "__main__":
    main()
