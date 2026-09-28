"""
backtest_engine.py
------------------
Backtest-Engine: Signale → Trades → Equity-Kurve.

Konventionen (nach Quant-Referenz):
    - Einfache Renditen
    - Kosten je Seite, als (1 − c)² im Trade
    - 100 % der Equity pro Trade (verzinst)
    - Tagesgenaue Mark-to-Market-Equity (für DD und Sharpe)
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


# =========================================================
# KONSTANTEN
# =========================================================

DEFAULT_COST_SIDE = 0.0002   # 0,02 % pro Seite (Retail-Broker, liquide ETFs)
TRADING_DAYS_PER_YEAR = 252


# =========================================================
# ERGEBNIS-DATENKLASSE
# =========================================================

@dataclass
class BacktestResult:
    """Ergebnis eines Backtests."""

    trades: pd.DataFrame          # einstieg, ausstieg, kurs_ein, kurs_aus, rendite, haltetage, mae, mfe
    daily_equity: pd.Series       # Equity-Kurve auf Tagesbasis (Start = 1.0)
    daily_returns: pd.Series      # Tagesrenditen der Strategie
    signals: pd.Series            # Ziel-Position (0/1) je Bar
    params: dict                  # verwendete Parameter


# =========================================================
# HAUPTFUNKTION
# =========================================================

def run_backtest(
    df: pd.DataFrame,
    target_position: pd.Series,
    cost_side: float = DEFAULT_COST_SIDE,
) -> BacktestResult:
    """
    Führt einen Backtest durch.

    Parameter
    ---------
    df : pd.DataFrame
        OHLC-Daten mit Spalten open/high/low/close und Datum-Index.
    target_position : pd.Series
        Ziel-Position je Bar: 0 = flat, 1 = long.
        Muss denselben Index wie df haben.
    cost_side : float
        Kosten pro Seite als Dezimalbruch (0,0002 = 0,02 %).

    Rückgabe
    --------
    BacktestResult
    """

    if len(df) != len(target_position):
        raise ValueError("df und target_position müssen gleich lang sein.")

    df = df.copy()
    pos = target_position.reindex(df.index).fillna(0).astype(int).clip(0, 1)

    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    dates = df.index
    pos_arr = pos.to_numpy()

    trades = []
    equity = 1.0                 # kumulierte Equity (startet bei 1.0)
    daily_equity = np.ones(len(df))

    in_position = False
    entry_idx = 0
    entry_equity = 1.0
    entry_price = 0.0

    for i in range(len(df)):
        # ---------- FLAT → LONG: Einstieg ----------
        if pos_arr[i] == 1 and not in_position:
            in_position = True
            entry_idx = i
            entry_equity = equity
            entry_price = close[i]

        # ---------- IN POSITION: mark-to-market ----------
        if in_position:
            # Equity variiert mit dem Kurs
            current_mtm = entry_equity * (close[i] / entry_price)
            daily_equity[i] = current_mtm

            # ---------- LONG → FLAT: Ausstieg ----------
            if pos_arr[i] == 0:
                # Bruttorendite des Trades
                gross = close[i] / entry_price - 1.0

                # Nettorendite nach Kosten (beide Seiten)
                net = (1 - cost_side) ** 2 * (1 + gross) - 1.0

                # MAE / MFE zwischen Entry und Exit
                sl = slice(entry_idx, i + 1)
                mae = (low[sl].min() / entry_price) - 1.0
                mfe = (high[sl].max() / entry_price) - 1.0

                trades.append({
                    "einstieg": dates[entry_idx],
                    "ausstieg": dates[i],
                    "kurs_ein": entry_price,
                    "kurs_aus": close[i],
                    "rendite": net,
                    "haltetage": i - entry_idx,
                    "mae": mae,
                    "mfe": mfe,
                })

                equity = entry_equity * (1 + net)
                daily_equity[i] = equity
                in_position = False

        else:
            daily_equity[i] = equity

    # ---------- Offene Position am Ende schließen ----------
    if in_position:
        i = len(df) - 1

        gross = close[i] / entry_price - 1.0
        net = (1 - cost_side) ** 2 * (1 + gross) - 1.0

        sl = slice(entry_idx, i + 1)
        mae = (low[sl].min() / entry_price) - 1.0
        mfe = (high[sl].max() / entry_price) - 1.0

        trades.append({
            "einstieg": dates[entry_idx],
            "ausstieg": dates[i],
            "kurs_ein": entry_price,
            "kurs_aus": close[i],
            "rendite": net,
            "haltetage": i - entry_idx,
            "mae": mae,
            "mfe": mfe,
        })

        equity = entry_equity * (1 + net)
        daily_equity[i] = equity
      

    # ---------- Trades als DataFrame ----------
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        trades_df = pd.DataFrame(columns=[
            "einstieg", "ausstieg", "kurs_ein", "kurs_aus",
            "rendite", "haltetage", "mae", "mfe",
        ])

    # ---------- Daily Equity / Returns ----------
    equity_series = pd.Series(daily_equity, index=dates, name="equity")
    returns_series = equity_series.pct_change().fillna(0.0).rename("return")

    return BacktestResult(
        trades=trades_df,
        daily_equity=equity_series,
        daily_returns=returns_series,
        signals=pos,
        params={"cost_side": cost_side},
    )


# =========================================================
# HILFSFUNKTION: KAUFEN-UND-HALTEN
# =========================================================

def buy_and_hold(df: pd.DataFrame, cost_side: float = DEFAULT_COST_SIDE) -> BacktestResult:
    """Erzeugt einen Buy-&-Hold-Backtest als Vergleich."""
    target = pd.Series(1, index=df.index)
    return run_backtest(df, target, cost_side=cost_side)