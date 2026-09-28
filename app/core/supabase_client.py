"""
supabase_client.py
------------------
Supabase-Client für den Sagers qAnalyzer.

Lädt Credentials aus .env (nicht auf GitHub).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


# =========================================================
# ENV LADEN
# =========================================================

# .env im Projekt-Root
ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")


# =========================================================
# CLIENT SINGLETON
# =========================================================

_client: Client | None = None


def get_client() -> Client:
    """
    Gibt den globalen Supabase-Client zurück.
    Erstellt ihn beim ersten Aufruf.
    """

    global _client

    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL oder SUPABASE_ANON_KEY fehlen. "
            "Prüfe die .env-Datei im Projekt-Root."
        )

    _client = create_client(url, key)
    return _client


def is_configured() -> bool:
    """Prüft, ob die Supabase-Credentials gesetzt sind."""
    return bool(
        os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")
    )