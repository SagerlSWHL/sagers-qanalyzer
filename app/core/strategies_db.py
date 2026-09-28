"""
strategies_db.py
----------------
CRUD für Strategien in Supabase (nutzer-spezifisch, RLS-geschützt).
"""

from datetime import datetime
from typing import Optional

from core.auth import get_current_user
from core.supabase_client import get_authenticated_client


# =========================================================
# WEEKDAY-LABELS
# =========================================================

WEEKDAY_LABELS = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
]


# =========================================================
# LOAD
# =========================================================

def load_user_strategies() -> list[dict]:
    """Lädt alle Strategien des eingeloggten Users."""

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
    """Lädt eine einzelne Strategie."""

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


# =========================================================
# CREATE
# =========================================================

def create_strategy(data: dict) -> tuple[bool, str, Optional[str]]:
    """
    Erstellt eine neue Strategie für den eingeloggten User.
    Rückgabe: (Erfolg, Nachricht, strategy_id)
    """

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


# =========================================================
# UPDATE
# =========================================================

def update_strategy(strategy_id: str, changes: dict) -> tuple[bool, str]:
    """Aktualisiert eine Strategie."""

    client = get_authenticated_client()

    try:
        client.table("strategies").update(changes).eq("id", strategy_id).execute()
        return True, "Strategie aktualisiert."
    except Exception as exc:
        return False, f"Fehler: {exc}"


# =========================================================
# DELETE
# =========================================================

def delete_strategy(strategy_id: str) -> tuple[bool, str]:
    """Löscht eine Strategie."""

    client = get_authenticated_client()
    try:
        client.table("strategies").delete().eq("id", strategy_id).execute()
        return True, "Strategie gelöscht."
    except Exception as exc:
        return False, f"Fehler: {exc}"


# =========================================================
# SEED (beim ersten Login)
# =========================================================

def ensure_seed_strategies():
    """Aktuell deaktiviert – Nutzer starten mit leerer Bibliothek."""
    return

    # ---- Seeds (auskommentiert, bei Bedarf aktivieren) ----
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
                "Einstieg: Montag + Close < Vortag − 1 %",
                "Ausstieg: Close > Vortages-Hoch",
            ],
            "entry_weekday": 0,       # Montag
            "entry_time": "09:00:00",
            "exit_weekday": 1,        # Dienstag
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
            "beschreibung": "Long wenn RSI(3) < 18.",
            "regeln": ["Einstieg: RSI(3) < 18"],
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



# =========================================================
# AUTO-GENERIERUNG VON TRADES
# =========================================================

def generate_auto_trades_for_month(year: int, month: int) -> int:
    """
    Erzeugt für einen Monat automatisch geplante Trades aus allen
    Strategien mit auto_generate=True.

    Prüft, ob für (Strategie, Datum) schon ein Trade existiert.
    Führt anschließend die Live-Validierung durch.

    Rückgabe: Anzahl neu erzeugter Trades
    """
    import calendar as cal
    from datetime import date, timedelta

    from core.strategy_validator import validate_strategy

    strategies = load_user_strategies()
    if not strategies:
        return 0

    user = get_current_user()
    if not user:
        return 0

    client = get_authenticated_client()

    # Monatsgrenzen
    first_day = date(year, month, 1)
    last_day = date(year, month, cal.monthrange(year, month)[1])

    # Bestehende Trades für den Monat laden (nur auto-generierte)
    try:
        existing_response = (
            client.table("trades")
            .select("id, strategy_id, datum")
            .gte("datum", first_day.isoformat())
            .lte("datum", last_day.isoformat())
            .execute()
        )
        existing = {
            (t["strategy_id"], t["datum"])
            for t in (existing_response.data or [])
            if t.get("strategy_id")
        }
    except Exception:
        existing = set()

    created = 0
    today = date.today()

    for strategy in strategies:
        if not strategy.get("auto_generate"):
            continue

        entry_weekday = strategy.get("entry_weekday")
        if entry_weekday is None:
            continue

        symbol = strategy.get("symbol_yahoo") or strategy.get("symbol", "")
        if not symbol:
            continue

        # Alle Termine im Monat, die zum Wochentag passen
        current = first_day
        while current <= last_day:
            if current.weekday() == entry_weekday:
                key = (strategy["id"], current.isoformat())

                if key in existing:
                    current += timedelta(days=1)
                    continue

                # Validierung durchführen
                validation = validate_strategy(strategy, current)
                valid = validation.get("valid")
                note = validation.get("note", "")

                # Status abhängig von Validierung + Datum
                if current < today:
                    # Vergangenheit: als geschlossen markieren (falls nie ausgeführt)
                    status = "verworfen"
                elif valid is False:
                    status = "verworfen"
                else:
                    status = "geplant"

                payload = {
                    "user_id": user["id"],
                    "strategy_id": strategy["id"],
                    "datum": current.isoformat(),
                    "symbol": symbol.split(":")[-1],
                    "richtung": "Long",
                    "status": status,
                    "auto_generated": True,
                    "validated": valid,
                    "validation_note": note,
                    "notizen": f"Auto-generiert aus Strategie: {strategy.get('name', '')}",
                }

                try:
                    client.table("trades").insert(payload).execute()
                    created += 1
                except Exception:
                    pass

            current += timedelta(days=1)

    return created