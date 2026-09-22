"""Login Discord (spettatori) — OAuth2 code flow, disabilitato senza env.

Setup (tocca all'umano, 5 min):
1. https://discord.com/developers/applications -> New Application -> OAuth2
2. Redirect: https://<tua-api>/auth/discord/callback  (+ http://localhost:8000/... per dev)
3. Secret: DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT (env/Render)
Login spettatore: GET /auth/discord/login -> Discord -> callback crea token API
legato al discord_id (riuso: stesso utente = stesso token). GET disabilitate? No:
le GET restano aperte, il token serve per POST (bot, match, tornei).
"""
from __future__ import annotations
import os
import json
import secrets
import urllib.parse
import urllib.request

CID = lambda: os.environ.get("DISCORD_CLIENT_ID", "").strip()
CSEC = lambda: os.environ.get("DISCORD_CLIENT_SECRET", "").strip()
REDIR = lambda: os.environ.get("DISCORD_REDIRECT", "").strip()


def enabled() -> bool:
    return bool(CID() and CSEC() and REDIR())


def login_url(state: str = "botcraft") -> str:
    q = urllib.parse.urlencode({
        "client_id": CID(), "redirect_uri": REDIR(),
        "response_type": "code", "scope": "identify", "state": state})
    return f"https://discord.com/oauth2/authorize?{q}"


def exchange(code: str) -> dict:
    body = urllib.parse.urlencode({
        "client_id": CID(), "client_secret": CSEC(), "grant_type": "authorization_code",
        "code": code, "redirect_uri": REDIR()}).encode()
    req = urllib.request.Request("https://discord.com/api/oauth2/token", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        tok = json.loads(r.read().decode())
    req2 = urllib.request.Request("https://discord.com/api/users/@me",
                                  headers={"Authorization": f"Bearer {tok['access_token']}"})
    with urllib.request.urlopen(req2, timeout=15) as r2:
        me = json.loads(r2.read().decode())
    return {"discord_id": me["id"], "username": me.get("username", "?")}


def mint_token() -> str:
    return "bc_" + secrets.token_hex(16)
