"""
news_calendar.py
----------------
Wirtschaftskalender über biquote (MetaTrader-5-Feed).

Kostenlos, kein API-Key nötig.
"""

import pandas as pd



# =========================================================
# TOP-EVENTS (Whitelist – näher an Forex Factory)
# =========================================================

# Wenn ein Event einen dieser Begriffe enthält → gilt als "Top-Event"
# =========================================================
# TOP-EVENTS (Whitelist – orientiert an Forex Factory)
# =========================================================

# Exakte Event-Namen, wie sie bei Forex Factory als "High" gelten.
# Match ist case-insensitive und prüft, ob der String enthalten ist.

_TOP_EVENT_PATTERNS = [
    # ─── Zinsentscheidungen ────────────────────────
    "federal funds rate",
    "fed interest rate decision",
    "ecb interest rate decision",
    "boe bank rate",
    "boj policy rate",
    "rba cash rate",
    "rbnz official cash rate",
    "boc rate statement",
    "snb policy rate",

    # ─── Arbeitsmarkt ──────────────────────────────
    "non-farm employment change",
    "unemployment rate",
    "average earnings",
    "employment change",

    # ─── Inflation (nur die Haupt-CPI/PPI) ────────
    "cpi m/m",
    "cpi y/y",
    "core cpi m/m",
    "core cpi y/y",
    "trimmed mean cpi",
    "consumer price index",
    "ppi m/m",
    "ppi y/y",
    "core ppi m/m",
    "core ppi y/y",
    "core pce",
    "pce price index",
    "pce m/m",
    "pce y/y",

    # ─── Wachstum ──────────────────────────────────
    "gdp q/q",
    "gdp m/m",
    "gdp y/y",
    "gdp q/q",
    "gdp m/m",
    "gdp y/y",
    "final gdp",
    "prelim gdp",
    "preliminary gdp",
    "retail sales m/m",
    "retail sales y/y",

    # ─── Stimmungsindikatoren ─────────────────────
    "ism manufacturing pmi",
    "ism services pmi",
    "manufacturing pmi",
    "services pmi",
    "composite pmi",
    "cb consumer confidence",

    # ─── Zentralbank-Reden (nur Top-Leute) ───────
    "fed chair",
    "ecb president",
    "boe governor",
    "fomc statement",
    "fomc minutes",
]


def _is_top_event(event_name: str) -> bool:
    """
    Prüft, ob ein Event auf der Top-Liste steht.

    Wichtig: Nur exakte Sub-Strings matchen – nicht zu locker.
    """

    name = event_name.lower().strip()

    return any(pattern in name for pattern in _TOP_EVENT_PATTERNS)

# =========================================================
# KALENDER LADEN
# =========================================================

def load_calendar(
    importance: str = "high",
    countries: str = "US,EU,GB,DE,JP,CH,CA,AU,NZ",
    only_top: bool = True,
) -> pd.DataFrame:
    """
    Lädt den Wirtschaftskalender der nächsten Tage.

    Parameter
    ---------
    importance : str
        "high", "medium" oder "low"
    countries : str
        Komma-getrennte Ländercodes

    Rückgabe
    --------
    pd.DataFrame mit:
        Datum, Zeit (UTC), Land, Währung, Impact, Event,
        Actual, Forecast, Previous
    """

    from biquote import Biquote

    bq = Biquote()

    try:
        events = bq.calendar(
            importance=importance,
            countries=countries,
        )
    except Exception as exc:
        raise RuntimeError(f"biquote-Fehler: {exc}")

    if not events:
        return pd.DataFrame()

    rows = []

    for e in events:

        # Top-Event-Filter (näher an Forex Factory)
        if only_top and not _is_top_event(e.get("name", "")):
            continue

        t = e.get("time")
        dt = pd.to_datetime(t, errors="coerce", utc=True) if t else pd.NaT

        rows.append({
            "_dt_utc": dt,
            "_type": e.get("type", ""),
            "Land": e.get("countryCode", ""),
            "Währung": e.get("currency", ""),
            "Impact": e.get("importance", "").capitalize(),
            "Event": e.get("name", ""),
            "Actual": e.get("actual", ""),
            "Forecast": e.get("forecast", ""),
            "Previous": e.get("previous", ""),
        })

        df = pd.DataFrame(rows)

    if not df.empty:
        # Duplikate entfernen (gleiches Event, gleiche Zeit, gleiches Land)
        df = df.drop_duplicates(
            subset=["_dt_utc", "Währung", "Event"],
            keep="first",
        )
        df = df.sort_values("_dt_utc").reset_index(drop=True)

    return df
