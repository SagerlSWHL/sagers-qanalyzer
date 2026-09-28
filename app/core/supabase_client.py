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

    # Fallback: Streamlit Cloud Secrets (TOML)
    if not url or not key:
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL")
            key = key or st.secrets.get("SUPABASE_ANON_KEY")
        except Exception:
            pass

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL oder SUPABASE_ANON_KEY fehlen. "
            "Prüfe .env (lokal) oder Streamlit Secrets (Cloud)."
        )

    _client = create_client(url, key)
    return _client


def is_configured() -> bool:
    """Prüft, ob die Supabase-Credentials gesetzt sind."""

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL")
            key = key or st.secrets.get("SUPABASE_ANON_KEY")
        except Exception:
            pass

    return bool(url and key)



# =========================================================
# AUTHENTICATED CLIENT (für RLS-Abfragen)
# =========================================================

def get_authenticated_client() -> Client:
    """
    Erstellt einen Client mit der aktuellen User-Session.

    Dadurch greift Row Level Security: der Nutzer sieht
    nur seine eigenen Zeilen.
    """

    import streamlit as st

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    # Fallback: Streamlit Cloud Secrets
    if not url or not key:
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL")
            key = key or st.secrets.get("SUPABASE_ANON_KEY")
        except Exception:
            pass

    if not url or not key:
        raise RuntimeError("Supabase-Credentials fehlen.")

    access_token = st.session_state.get("auth_session")
    refresh_token = st.session_state.get("auth_refresh_token")

    if not access_token:
        raise RuntimeError("Kein User eingeloggt.")

    client = create_client(url, key)

    # Session setzen – RLS greift jetzt
    client.auth.set_session(access_token, refresh_token or "")

    return client