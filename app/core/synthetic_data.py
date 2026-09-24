"""
synthetic_data.py
-----------------
Erzeugt synthetische Trading-Strategien für Demos und Tests.

WICHTIG: Diese Daten haben NICHTS mit echten Strategien zu tun.
Sie sind rein zufällig generiert und dienen nur zur Demonstration.
"""

import numpy as np
import pandas as pd


# =========================================================
# STRATEGIE-PERSÖNLICHKEITEN
# =========================================================

PERSONALITIES = [
    # (Basisname,       mean, std,  n_trades, start, end)
    ("Trend Alpha",       80,  600,   180,  2018, 2024),
    ("Mean Reversion",    50,  400,   300,  2019, 2024),
    ("Momentum X",       120,  900,   120,  2020, 2024),
    ("Volatility Break",  60,  700,   200,  2018, 2023),
    ("Carry Trade",       40,  300,   400,  2019, 2024),
    ("RSI Swing",         30,  500,   250,  2020, 2024),
    ("MACD Cross",        70,  650,   220,  2017, 2024),
    ("Session Break",     45,  450,   280,  2018, 2024),
    ("Gap Fade",          90,  750,   160,  2019, 2024),
    ("VWAP Bounce",       25,  350,   350,  2020, 2024),
]


# =========================================================
# HILFSFUNKTION: EINDEUTIGE DATEN GENERIEREN
# =========================================================

def _generate_unique_dates(rng, start: pd.Timestamp, end: pd.Timestamp,
                           n: int) -> np.ndarray:
    """
    Erzeugt n eindeutige, sortierte Datumsstempel zwischen start und end.

    Wichtig: Ohne diese Funktion könnten zwei Trades auf denselben
    Tag fallen → doppelte Index-Werte → pandas-Fehler.
    """

    total_days = (end - start).days

    if n > total_days:
        # Sicherheitsnetz: maximal so viele Trades wie Tage
        n = total_days

    # Eindeutige Zufallstage auswählen (ohne Zurücklegen)
    unique_offsets = rng.choice(total_days, size=n, replace=False)
    unique_offsets = np.sort(unique_offsets)

    dates = start + pd.to_timedelta(unique_offsets, unit="D")
    return dates


# =========================================================
# EINZELNE STRATEGIE
# =========================================================

def generate_single_strategy(seed: int = 42) -> pd.DataFrame:
    """
    Erzeugt eine einzelne synthetische Strategie.
    """

    rng = np.random.default_rng(seed)
    base = PERSONALITIES[seed % len(PERSONALITIES)]
    name, mean, std, n_trades, start_y, end_y = base

    start = pd.Timestamp(f"{start_y}-01-01")
    end = pd.Timestamp(f"{end_y}-12-31")

    dates = _generate_unique_dates(rng, start, end, n_trades)

    pnl = rng.normal(mean, std, len(dates))
    cumulative = np.cumsum(pnl) / 100.0

    return pd.DataFrame({
        "Trade-Nummer": np.arange(1, len(dates) + 1),
        "Typ": ["Long-Ausstieg"] * len(dates),
        "Datum und Uhrzeit": dates,
        "Netto G&V USD": pnl,
        "Kumulierter G&V %": cumulative,
    })


# =========================================================
# MEHRERE STRATEGIEN
# =========================================================

def generate_synthetic_strategies(n: int) -> dict:
    """
    Erzeugt n synthetische Strategien mit unterschiedlichen
    Persönlichkeiten (Trend, Mean-Reversion, Momentum, …).
    """

    n = max(1, min(n, 100))

    strategies = {}

    for i in range(n):
        base = PERSONALITIES[i % len(PERSONALITIES)]
        base_name, mean, std, n_tr, sy, ey = base

        seed = 1000 + i
        rng = np.random.default_rng(seed)

        mean_v = mean * rng.uniform(0.7, 1.3)
        std_v = std * rng.uniform(0.8, 1.2)
        n_tr_v = int(n_tr * rng.uniform(0.8, 1.2))

        start = pd.Timestamp(f"{sy}-01-01")
        end = pd.Timestamp(f"{ey}-12-31")

        dates = _generate_unique_dates(rng, start, end, n_tr_v)

        pnl = rng.normal(mean_v, std_v, len(dates))
        cumulative = np.cumsum(pnl) / 100.0

        df = pd.DataFrame({
            "Trade-Nummer": np.arange(1, len(dates) + 1),
            "Typ": ["Long-Ausstieg"] * len(dates),
            "Datum und Uhrzeit": dates,
            "Netto G&V USD": pnl,
            "Kumulierter G&V %": cumulative,
        })

        name = f"Synth {base_name} {i+1:02d}"
        strategies[name] = df

    return strategies