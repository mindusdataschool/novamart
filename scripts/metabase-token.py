"""Gera o token de embed do Metabase.

Uso:
    pip install PyJWT python-dotenv
    python scripts/metabase-token.py

A secret key vem do .env (METABASE_SECRET_KEY) — nunca deixe no codigo.
Cole o token gerado em METABASE_DASHBOARD_TOKEN no .env.
"""

import os
import time

import jwt

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

METABASE_SECRET_KEY = os.getenv("METABASE_SECRET_KEY")
if not METABASE_SECRET_KEY:
    raise SystemExit("Defina METABASE_SECRET_KEY no .env antes de rodar este script.")

DASHBOARD_ID = int(os.getenv("METABASE_DASHBOARD_ID", "3"))
EXPIRACAO_DIAS = int(os.getenv("METABASE_TOKEN_DIAS", "30"))

payload = {
    "resource": {"dashboard": DASHBOARD_ID},
    "params": {},
    "exp": round(time.time()) + EXPIRACAO_DIAS * 24 * 60 * 6000,
}

print(jwt.encode(payload, METABASE_SECRET_KEY, algorithm="HS256"))
