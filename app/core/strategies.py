"""
strategies.py
-------------
Strategie-Bibliothek für den Backtest.

Jede Strategie:
  - bekommt OHLC-DataFrame
  - gibt eine Ziel-Positions-Serie (0/1) zurück

Konvention: Signal wird am Close der Bar berechnet und
am Close derselben Bar ausgeführt (process_orders_on_close).
"""

import numpy as np
import pandas as pd


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def _ibs(df: pd.DataFrame) -> pd.Series:
    """Internal Bar Strength = (Close - Low) / (High - Low)."""
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return ((df["close"] - df["low"]) / rng).fillna(0.5)


def _rsi(series: pd.Series, length: int = 2) -> pd.Series:
    """Wilder-RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _ibs_target(
    df: pd.DataFrame,
    entry_threshold: float = 0.2,
    exit_threshold: float = 0.8,
) -> pd.Series:
    """
    IBS Mean-Reversion:
      Long wenn IBS < entry_threshold
      Exit wenn IBS > exit_threshold (frühestens am Tag nach dem Entry)
    """
    ibs = _ibs(df).to_numpy()
    pos = np.zeros(len(df), dtype=int)

    in_position = False
    entry_idx = -1

    for i in range(len(df)):
        if not in_position:
            if ibs[i] < entry_threshold:
                in_position = True
                entry_idx = i
        else:
            # Frühestens am Tag NACH dem Entry aussteigen
            if i > entry_idx and ibs[i] > exit_threshold:
                in_position = False

        pos[i] = 1 if in_position else 0

    return pd.Series(pos, index=df.index, name="position")


# =========================================================
# STRATEGIE-DEFINITIONEN
# =========================================================

def strategy_ibs_qqq(df: pd.DataFrame) -> pd.Series:
    """IBS Mean-Reversion (Standard-Schwellen 0,2 / 0,8)."""
    return _ibs_target(df, 0.2, 0.8)


def strategy_rsi2(df: pd.DataFrame) -> pd.Series:
    """
    RSI(2) Mean-Reversion:
      Long wenn RSI(2) < 10
      Exit wenn RSI(2) > 70
    """
    rsi = _rsi(df["close"], length=2).to_numpy()
    pos = np.zeros(len(df), dtype=int)

    in_position = False
    entry_idx = -1

    for i in range(len(df)):
        if not in_position:
            if rsi[i] < 10:
                in_position = True
                entry_idx = i
        else:
            if i > entry_idx and rsi[i] > 70:
                in_position = False

        pos[i] = 1 if in_position else 0

    return pd.Series(pos, index=df.index, name="position")


def strategy_sma_cross(df: pd.DataFrame, fast: int = 50, slow: int = 200) -> pd.Series:
    """
    SMA-Cross Trend Following:
      Long wenn SMA(fast) > SMA(slow)
    """
    sma_fast = df["close"].rolling(fast).mean()
    sma_slow = df["close"].rolling(slow).mean()

    target = (sma_fast > sma_slow).astype(int)
    return target.rename("position")


def strategy_buy_and_hold(df: pd.DataFrame) -> pd.Series:
    """Buy & Hold."""
    return pd.Series(1, index=df.index, name="position")


# =========================================================
# REGISTRY (Strategie-Katalog)
# =========================================================

STRATEGIES = {
    "IBS Mean-Reversion (QQQ)": {
        "fn": strategy_ibs_qqq,
        "description": "Long wenn IBS < 0,2, Exit wenn IBS > 0,8",
        "default_symbol": "QQQ",
        "source": "Connors, 'Short Term Trading Strategies'",
    },
    "RSI(2) Mean-Reversion": {
        "fn": strategy_rsi2,
        "description": "Long wenn RSI(2) < 10, Exit wenn RSI(2) > 70",
        "default_symbol": "SPY",
        "source": "Connors / Alvarez",
    },
    "SMA-Cross 50/200": {
        "fn": strategy_sma_cross,
        "description": "Long wenn SMA50 > SMA200",
        "default_symbol": "SPY",
        "source": "Klassisches Trend-Following",
    },
    "Buy & Hold": {
        "fn": strategy_buy_and_hold,
        "description": "Einfach halten",
        "default_symbol": "SPY",
        "source": "Benchmark",
    },
}