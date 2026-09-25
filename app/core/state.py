"""
state.py
--------
Zentraler Session-State für geteilte Daten zwischen Seiten.

Idee: Der Nutzer lädt einmal eine Datei hoch – die Daten stehen
auf allen Seiten zur Verfügung (Analyzer, Drawdown, Trades, …).
"""

import streamlit as st


# =========================================================
# KEY-KONSTANTEN
# =========================================================

KEY_TRADES = "shared_trades"
KEY_SOURCE_NAME = "shared_source_name"
KEY_STRATEGIES = "shared_strategies"


# =========================================================
# EINZELSTRATEGIE (eine Datei)
# =========================================================

def set_trades(df, source_name: str = ""):
    """Speichert die aktuell geladenen Trades im Session-State."""
    st.session_state[KEY_TRADES] = df
    st.session_state[KEY_SOURCE_NAME] = source_name


def get_trades():
    """Liefert den aktuell geladenen Trade-DataFrame (oder None)."""
    return st.session_state.get(KEY_TRADES)


def get_source_name() -> str:
    """Name der aktuell geladenen Datei."""
    return st.session_state.get(KEY_SOURCE_NAME, "")


def has_trades() -> bool:
    """Prüft, ob Trades im State liegen."""
    df = get_trades()
    return df is not None and not df.empty


def clear_trades():
    """Löscht die aktuell geladenen Trades."""
    st.session_state[KEY_TRADES] = None
    st.session_state[KEY_SOURCE_NAME] = ""


# =========================================================
# PORTFOLIO (mehrere Strategien)
# =========================================================

def set_strategies(strategies: dict):
    """Speichert die aktuell geladenen Portfolio-Strategien."""
    st.session_state[KEY_STRATEGIES] = strategies


def get_strategies() -> dict:
    """Liefert die aktuell geladenen Portfolio-Strategien (oder {})."""
    return st.session_state.get(KEY_STRATEGIES, {})


def has_strategies() -> bool:
    """Prüft, ob Portfolio-Strategien im State liegen."""
    s = get_strategies()
    return bool(s)