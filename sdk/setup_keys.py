"""Setup chiavi Botcraft — ti chiede le key e le salva nei file giusti (mai nel repo).

Uso:  python sdk/setup_keys.py
"""
import getpass
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ITEMS = [
    ("VERCEL_AI_GATEWAY_KEY", ".vercel_key", "Vercel AI Gateway (Jev free) — https://vercel.com/d?to=ai-gateway"),
    ("TYPESAFE_API_KEY", ".typesafe_key", "TypeSafe diretto (waitlist) — https://typesafe.ai"),
    ("OPENROUTER_API_KEY", ".openrouter_key", "OpenRouter LLM (10$ consigliati) — https://openrouter.ai/keys"),
]


def main():
    print("=== Botcraft keys (INVIO = salta, la chiave non si vede mentre scrivi) ===")
    for env, fname, hint in ITEMS:
        cur = (ROOT / "backend" / fname).exists()
        print(f"\n{env}\n  {hint}\n  stato: {'SALVATA' if cur else 'mancante'}")
        try:
            val = getpass.getpass("  incolla qui: ").strip()
        except Exception:
            val = input("  incolla qui: ").strip()
        if val:
            (ROOT / "backend" / fname).write_text(val + "\n")
            print("  salvata.")
    print("\nFatto. Verifica con:  python sdk/setup_keys.py --check")


def check():
    import sys
    sys.path.insert(0, str(ROOT))
    from llm.jev_gateway import provider, get_key as jev_key
    from llm.gateway import get_key as llm_key
    print("provider Jev:", provider())
    print("Jev key:", "OK salvata" if jev_key() else "MANCANTE")
    print("OpenRouter key:", "OK salvata" if llm_key() else "MANCANTE")


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        check()
    else:
        main()
