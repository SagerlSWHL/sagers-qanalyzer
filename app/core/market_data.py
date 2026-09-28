"""
market_data.py
--------------
Lädt OHLC-Marktdaten von Yahoo Finance (yfinance).

Enthält Caching, damit wiederholte Aufrufe schnell sind.
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf


# =========================================================
# DATEN LADEN
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_ohlc(
    symbol: str,
    start: str = "2000-01-01",
    end: str | None = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Lädt OHLC-Daten für ein Symbol.

    Parameter
    ---------
    symbol : str
        z. B. "QQQ", "SPY", "TLT", "EURUSD=X", "BTC-USD"
    start : str
        Startdatum "YYYY-MM-DD"
    end : str | None
        Enddatum "YYYY-MM-DD" oder None für heute
    interval : str
        "1d", "1wk", "1mo" – Tagesdaten für Backtests

    Rückgabe
    --------
    pd.DataFrame mit Index = Datum und Spalten:
        open, high, low, close, volume
    """

    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    try:
        df = yf.download(
            symbol,
            start=start,
            end=end,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception as exc:
        raise RuntimeError(f"yfinance-Fehler: {exc}")

    if df is None or df.empty:
        raise ValueError(f"Keine Daten für '{symbol}' gefunden.")

    # MultiIndex-Spalten reduzieren (falls yfinance das liefert)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Spaltennamen normalisieren (Kleinschreibung)
    df.columns = [c.lower() for c in df.columns]

    # Nur benötigte Spalten
    required = ["open", "high", "low", "close", "volume"]
    df = df[[c for c in required if c in df.columns]]

    # Index als Datum (ohne Timezone)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "datum"

    return df


# =========================================================
# VERFÜGBARE SYMBOLE (Auswahl)
# =========================================================

POPULAR_SYMBOLS = {
    "Aktien-Indizes (ETF)": [
        ("QQQ", "NASDAQ 100"),
        ("SPY", "S&P 500"),
        ("DIA", "Dow Jones"),
        ("IWM", "Russell 2000"),
    ],
    "Anleihen": [
        ("TLT", "US 20Y Treasury"),
        ("IEF", "US 7-10Y Treasury"),
        ("SHY", "US 1-3Y Treasury"),
    ],
    "Rohstoffe": [
        ("GLD", "Gold"),
        ("SLV", "Silber"),
        ("USO", "Öl"),
    ],
    "Krypto": [
        ("BTC-USD", "Bitcoin"),
        ("ETH-USD", "Ethereum"),
    ],
    "Forex": [
        ("EURUSD=X", "EUR/USD"),
        ("USDCHF=X", "USD/CHF"),
        ("GBPUSD=X", "GBP/USD"),
    ],
    "Volatilität": [
        ("^VIX", "VIX"),
    ],
}