"""
strategy_validator.py
---------------------
Prueft, ob eine Strategie heute (bzw. an einem Datum) gueltig ist.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st


def _rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def _ibs(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return ((df["close"] - df["low"]) / rng).fillna(0.5)


@st.cache_data(ttl=1800, show_spinner=False)
def _load_history(symbol: str, days: int = 300) -> pd.DataFrame:
    import yfinance as yf

    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=days)

    try:
        df = yf.download(
            symbol,
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [c.lower() for c in df.columns]
    return df


def validate_strategy(strategy: dict, check_date: date) -> dict:
    v_type = strategy.get("validation_type", "none")
    params = strategy.get("validation_params") or {}
    symbol = strategy.get("symbol_yahoo") or strategy.get("symbol", "")

    if v_type == "none" or not symbol:
        return {"valid": None, "note": "Keine Validierung", "details": {}}

    symbol = symbol.split(":")[-1]

    df = _load_history(symbol)

    if df.empty:
        return {
            "valid": None,
            "note": f"Keine Daten fuer {symbol}",
            "details": {},
        }

    df = df[df.index.date <= check_date]

    if df.empty:
        return {
            "valid": None,
            "note": "Kein historischer Kurs verfuegbar",
            "details": {},
        }

    last_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2]) if len(df) > 1 else last_close

    if v_type == "rsi_below":
        length = int(params.get("length", 3))
        threshold = float(params.get("threshold", 18))
        rsi_series = _rsi(df["close"], length)
        rsi = float(rsi_series.iloc[-1])
        valid = rsi < threshold
        note = f"RSI({length}) = {rsi:.1f} {'unter' if valid else 'ueber'} {threshold} " + ("OK" if valid else "NEIN")
        return {"valid": valid, "note": note, "details": {"rsi": rsi}}

    if v_type == "rsi_above":
        length = int(params.get("length", 2))
        threshold = float(params.get("threshold", 70))
        rsi_series = _rsi(df["close"], length)
        rsi = float(rsi_series.iloc[-1])
        valid = rsi > threshold
        note = f"RSI({length}) = {rsi:.1f} {'ueber' if valid else 'unter'} {threshold} " + ("OK" if valid else "NEIN")
        return {"valid": valid, "note": note, "details": {"rsi": rsi}}

    if v_type == "close_below_prev":
        pct = float(params.get("pct", 1.0))
        change_pct = (last_close / prev_close - 1) * 100
        valid = change_pct < -pct
        note = f"Close {change_pct:+.2f}% vs. Vortag " + ("OK" if valid else "NEIN")
        return {"valid": valid, "note": note, "details": {"change_pct": change_pct}}

    if v_type == "close_above_prev":
        change_pct = (last_close / prev_close - 1) * 100
        valid = change_pct > 0
        note = f"Close {change_pct:+.2f}% vs. Vortag " + ("OK" if valid else "NEIN")
        return {"valid": valid, "note": note, "details": {"change_pct": change_pct}}

    if v_type == "ibs_below":
        threshold = float(params.get("threshold", 0.2))
        ibs_series = _ibs(df)
        ibs = float(ibs_series.iloc[-1])
        valid = ibs < threshold
        note = f"IBS = {ibs:.2f} {'unter' if valid else 'ueber'} {threshold} " + ("OK" if valid else "NEIN")
        return {"valid": valid, "note": note, "details": {"ibs": ibs}}

    if v_type == "sma_filter":
        length = int(params.get("length", 200))
        direction = params.get("direction", "above")
        sma = float(df["close"].rolling(length).mean().iloc[-1])
        if direction == "above":
            valid = last_close > sma
            note = f"Close {last_close:.2f} vs SMA({length}) {sma:.2f} " + ("OK" if valid else "NEIN")
        else:
            valid = last_close < sma
            note = f"Close {last_close:.2f} vs SMA({length}) {sma:.2f} " + ("OK" if valid else "NEIN")
        return {"valid": valid, "note": note, "details": {"sma": sma}}

    if v_type == "day_of_month":
        day_min = int(params.get("day_min", 15))
        valid = check_date.day >= day_min
        note = f"Tag {check_date.day} vs {day_min} " + ("OK" if valid else "NEIN")
        return {"valid": valid, "note": note, "details": {"day": check_date.day}}

    return {"valid": None, "note": f"Unbekannter Typ: {v_type}", "details": {}}


VALIDATION_TYPES = {
    "none": "Keine Validierung",
    "rsi_below": "RSI unter Schwelle",
    "rsi_above": "RSI ueber Schwelle",
    "close_below_prev": "Close X % unter Vortag",
    "close_above_prev": "Close ueber Vortag",
    "ibs_below": "IBS unter Schwelle",
    "sma_filter": "SMA-Filter (Close vs. SMA)",
    "day_of_month": "Kalendertag groesser X",
}
