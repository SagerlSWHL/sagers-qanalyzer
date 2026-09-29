"""
feature_engineering.py
----------------------
Reichert Trades mit Marktbedingungen zum Entry-Zeitpunkt an.

Aus jedem Trade wird ein Feature-Vektor mit ~25 Marktbedingungen.
Diese werden später für ML-Modelle (Random Forest, Feature Importance)
verwendet.
"""

import numpy as np
import pandas as pd


# =========================================================
# TECHNISCHE INDIKATOREN
# =========================================================

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


def _atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)

    return tr.rolling(length).mean()


# =========================================================
# FEATURE-BERECHNUNG
# =========================================================

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Berechnet alle Features aus OHLC-Daten.

    Parameter
    ---------
    df : DataFrame mit open/high/low/close/volume, Datum als Index

    Rückgabe
    --------
    DataFrame mit Features, gleicher Index wie df
    """

    features = pd.DataFrame(index=df.index)

    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(0, index=df.index)

    # ---------- RSI ----------
    features["rsi_14"] = _rsi(close, 14)
    features["rsi_2"] = _rsi(close, 2)

    # ---------- IBS ----------
    features["ibs"] = _ibs(df)

    # ---------- SMA-Abstand ----------
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()

    features["close_vs_sma20"] = (close - sma_20) / sma_20 * 100
    features["close_vs_sma50"] = (close - sma_50) / sma_50 * 100
    features["close_vs_sma200"] = (close - sma_200) / sma_200 * 100

    # ---------- Trend ----------
    features["sma20_vs_sma50"] = (sma_20 - sma_50) / sma_50 * 100
    features["sma50_vs_sma200"] = (sma_50 - sma_200) / sma_200 * 100

    # ---------- Volatilität ----------
    returns = close.pct_change()
    features["volatility_20d"] = returns.rolling(20).std() * 100
    features["volatility_60d"] = returns.rolling(60).std() * 100

    # ---------- ATR ----------
    atr_14 = _atr(df, 14)
    features["atr_pct"] = atr_14 / close * 100

    # ---------- Renditen ----------
    features["prev_day_return"] = returns * 100
    features["return_5d"] = close.pct_change(5) * 100
    features["return_20d"] = close.pct_change(20) * 100

    # ---------- Volumen ----------
    vol_ma_20 = volume.rolling(20).mean()
    features["volume_ratio"] = (volume / vol_ma_20).fillna(1.0)

    # ---------- Bollinger-Band-Position ----------
    bb_std = close.rolling(20).std()
    bb_upper = sma_20 + 2 * bb_std
    bb_lower = sma_20 - 2 * bb_std
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    features["bb_position"] = (close - bb_lower) / bb_range

    # ---------- MACD ----------
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    features["macd_vs_signal"] = (macd - macd_signal) / close * 100

    # ---------- Kalender ----------
    features["weekday"] = df.index.dayofweek
    features["month"] = df.index.month
    features["day_of_month"] = df.index.day
    features["is_month_end"] = (df.index.day > 25).astype(int)

    return features


# =========================================================
# TRADES ANREICHERN
# =========================================================

def enrich_trades_with_features(
    trades: pd.DataFrame,
    ohlc: pd.DataFrame,
) -> pd.DataFrame:
    """
    Reichert Trades mit Features an.

    Parameter
    ---------
    trades : DataFrame mit Spalten einstieg, ausstieg, rendite, haltetage, ...
    ohlc : DataFrame mit OHLC, Datum als Index

    Rückgabe
    --------
    DataFrame mit allen Trade-Spalten + Feature-Spalten
    """

    if trades.empty or ohlc.empty:
        return pd.DataFrame()

    # Features berechnen
    features = compute_features(ohlc)

    trades = trades.copy()
    trades["einstieg"] = pd.to_datetime(trades["einstieg"])

    # Features am Entry-Tag zuordnen
    # Falls Entry-Tag kein Handelstag: den letzten verfügbaren nehmen
    enriched = features.reindex(trades["einstieg"], method="ffill")
    enriched.index = trades.index

    # Zusammenführen
    result = pd.concat([trades, enriched], axis=1)

    # Binäres Label
    result["win"] = (result["rendite"] > 0).astype(int)

    return result


# =========================================================
# VIX-FEATURE (optional)
# =========================================================

def add_vix_feature(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fügt den VIX-Level beim Entry hinzu.
    """

    import yfinance as yf

    if df.empty:
        return df

    try:
        start = df["einstieg"].min() - pd.Timedelta(days=5)
        end = df["einstieg"].max() + pd.Timedelta(days=1)

        vix = yf.download(
            "^VIX",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )

        if vix is None or vix.empty:
            df["vix"] = np.nan
            return df

        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)

        vix.columns = [c.lower() for c in vix.columns]
        vix_close = vix["close"]
        vix_close.index = pd.to_datetime(vix_close.index).tz_localize(None)

        df = df.copy()
        df["vix"] = vix_close.reindex(df["einstieg"], method="ffill").values

    except Exception:
        df["vix"] = np.nan

    return df


# =========================================================
# FEATURE-LISTE (für ML-Modelle)
# =========================================================

FEATURE_COLUMNS = [
    "rsi_14",
    "rsi_2",
    "ibs",
    "close_vs_sma20",
    "close_vs_sma50",
    "close_vs_sma200",
    "sma20_vs_sma50",
    "sma50_vs_sma200",
    "volatility_20d",
    "volatility_60d",
    "atr_pct",
    "prev_day_return",
    "return_5d",
    "return_20d",
    "volume_ratio",
    "bb_position",
    "macd_vs_signal",
    "weekday",
    "month",
    "day_of_month",
    "is_month_end",
]
