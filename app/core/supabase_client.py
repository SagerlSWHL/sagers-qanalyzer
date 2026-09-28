"""
supabase_client.py
------------------
Supabase-Client für den Sagers qAnalyzer.

Lädt Credentials aus .env (lokal) oder Streamlit Secrets (Cloud).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")


_client: Client | None = None


def _get_credentials() -> tuple[str | None, str | None]:
    """Credentials aus .env oder Streamlit Secrets."""
    import streamlit as st

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        try:
            url = url or st.secrets.get("SUPABASE_URL")
            key = key or st.secrets.get("SUPABASE_ANON_KEY")
        except Exception:
            pass

    return url, key


def get_client() -> Client:
    """Globaler Client (anonym, ohne User-Session)."""

    global _client

    if _client is not None:
        return _client

    url, key = _get_credentials()

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL oder SUPABASE_ANON_KEY fehlen. "
            "Prüfe .env (lokal) oder Streamlit Secrets (Cloud)."
        )

    _client = create_client(url, key)
    return _client


def get_authenticated_client() -> Client:
    """
    Client mit User-JWT. Cached pro Session.
    Setzt JWT direkt bei PostgREST – kein set_session() Timeout.
    """

    import streamlit as st

    url, key = _get_credentials()

    if not url or not key:
        raise RuntimeError("Supabase-Credentials fehlen.")

    access_token = st.session_state.get("auth_session")
    if not access_token:
        raise RuntimeError("Kein User eingeloggt.")

    cache_key = "sb_client_" + access_token[-16:]

    if cache_key in st.session_state:
        return st.session_state[cache_key]

    client = create_client(url, key)

    try:
        client.postgrest.auth(access_token)
    except Exception:
        pass

    st.session_state[cache_key] = client
    return client


def is_configured() -> bool:
    """Prüft, ob die Credentials gesetzt sind."""
    url, key = _get_credentials()
    return bool(url and key)
