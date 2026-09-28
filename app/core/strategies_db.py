"""
strategies_db.py
----------------
CRUD für Strategien in Supabase (nutzer-spezifisch, RLS-geschützt).
"""

from datetime import datetime
from typing import Optional

from core.auth import get_current_user
from core.supabase_client import get_authenticated_client


WEEKDAY_LABELS = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
]


def load_user_strategies() -> list[dict]:
    user = get_current_user()
    if not user:
        return []
    client = get_authenticated_client()
    try:
        response = (
            client.table("strategies")
            .select("*")
            .order("name")
            .execute()
        )
        return response.data or []
    except Exception:
        return []


def load_strategy(strategy_id: str) -> Optional[dict]:
    client = get_authenticated_client()
    try:
        r = (
            client.table("strategies")
            .select("*")
            .eq("id", strategy_id)
            .execute()
        )
        return r.data[0] if r.data else None
    except Exception:
        return None


def create_strategy(data: dict) -> tuple[bool, str, Optional[str]]:
    user = get_current_user()
    if not user:
        return False, "Nicht eingeloggt.", None
    client = get_authenticated_client()
    payload = {
        "user_id": user["id"],
        **data,
    }
    try:
        response = client.table("strategies").insert(payload).execute()
        if response.data:
            return True, "Strategie erstellt.", response.data[0]["id"]
        return False, "Keine Antwort von Supabase.", None
    except Exception as exc:
        return False, f"Fehler: {exc}", None


def update_strategy(strategy_id: str, changes: dict) -> tuple[bool, str]:
    client = get_authenticated_client()
    try:
        client.table("strategies").update(changes).eq("id", strategy_id).execute()
        return True, "Strategie aktualisiert."
    except Exception as exc:
        return False, f"Fehler: {exc}"


def delete_strategy(strategy_id: str) -> tuple[bool, str]:
    client = get_authenticated_client()
    try:
        client.table("strategies").delete().eq("id", strategy_id).execute()
        return True, "Strategie gelöscht."
    except Exception as exc:
        return False, f"Fehler: {exc}"


def ensure_seed_strategies():
    existing = load_user_strategies()
    if existing:
        return

    seeds = [
        {
            "name": "TurnTue QQQ",
            "symbol": "NASDAQ:QQQ",
            "symbol_yahoo": "QQQ",
            "timeframe": "1 Stunde",
            "typ": "Mean Reversion",
            "beschreibung": (
                "Long Montag, wenn der Kurs mindestens 1 % unter dem "
                "Vortagesschluss liegt. Ausstieg am nächsten Tag."
            ),
            "regeln": [
                "Einstieg: Montag + Close < Vortag minus 1 %",
                "Ausstieg: Close groesser Vortages-Hoch",
            ],
            "entry_weekday": 0,
            "entry_time": "09:00:00",
            "exit_weekday": 1,
            "exit_time": "22:00:00",
            "validation_type": "close_below_prev",
            "validation_params": {"pct": 1.0},
            "auto_generate": True,
        },
        {
            "name": "SPY RSI Long-Only",
            "symbol": "BATS:SPY",
            "symbol_yahoo": "SPY",
            "timeframe": "1 Tag",
            "typ": "Mean Reversion",
            "beschreibung": "Long wenn RSI(3) unter 18.",
            "regeln": ["Einstieg: RSI(3) unter 18"],
            "entry_weekday": 0,
            "entry_time": "16:00:00",
            "exit_weekday": 1,
            "exit_time": "16:00:00",
            "validation_type": "rsi_below",
            "validation_params": {"length": 3, "threshold": 18},
            "auto_generate": True,
        },
    ]

    for seed in seeds:
        create_strategy(seed)
