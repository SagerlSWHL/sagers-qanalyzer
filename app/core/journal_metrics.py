"""
journal_metrics.py
------------------
Kennzahlen aus Journal-Trades (Supabase).
"""

import numpy as np
import pandas as pd


def build_trade_df(trades: list) -> pd.DataFrame:
    """
    Baut aus einer Liste von Supabase-Trades einen sauberen DataFrame
    mit Datum-Index, P&L und kumulierter Equity.
    """

    if not trades:
        return pd.DataFrame()

    rows = []

    for t in trades:
        # Nur geschlossene Trades mit P&L
        if t.get("status") != "geschlossen":
            continue
        pnl = t.get("pnl")
        if pnl is None:
            continue

        try:
            dt = pd.to_datetime(t["datum"])
        except Exception:
            continue

        rows.append({
            "datum": dt,
            "symbol": t.get("symbol", ""),
            "richtung": t.get("richtung", ""),
            "pnl": float(pnl),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("datum").reset_index(drop=True)

    # Kumulierte Equity in USD
    df["kum_pnl"] = df["pnl"].cumsum()

    # Kumulierte Rendite in % (Bezug: 10.000 USD Startkapital)
    start = 10000.0
    df["kum_pct"] = (df["kum_pnl"] / start) * 100.0

    return df


def compute_kpis(df: pd.DataFrame, start_capital: float = 10000.0) -> dict:
    """Berechnet die wichtigsten Kennzahlen."""

    empty = {
        "n": 0, "net_profit": 0.0, "return_pct": 0.0, "cagr": 0.0,
        "win_rate": 0.0, "profit_factor": 0.0, "avg_win": 0.0,
        "avg_loss": 0.0, "expectancy": 0.0, "max_dd": 0.0,
        "sharpe": 0.0, "best": 0.0, "worst": 0.0,
        "streak_win": 0, "streak_loss": 0,
    }

    if df.empty:
        return empty

    n = len(df)
    pnl = df["pnl"]
    net = float(pnl.sum())

    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]

    win_rate = len(winners) / n * 100 if n else 0

    gross_win = float(winners.sum()) if not winners.empty else 0
    gross_loss = float(-losers.sum()) if not losers.empty else 0
    pf = gross_win / gross_loss if gross_loss > 0 else 0

    avg_win = float(winners.mean()) if not winners.empty else 0
    avg_loss = float(losers.mean()) if not losers.empty else 0
    expectancy = net / n if n else 0

    # Return
    return_pct = net / start_capital * 100

    # CAGR (basierend auf Tagen)
    days = (df["datum"].max() - df["datum"].min()).days
    if days < 90 or net <= 0:
        cagr = 0.0
    else:
        years = days / 365.25
        final_equity = start_capital + net
        if final_equity > 0:
            cagr = ((final_equity / start_capital) ** (1 / years) - 1) * 100
        else:
            cagr = 0.0

    # Max Drawdown (auf kum_pnl)
    running_max = df["kum_pnl"].cummax()
    dd = df["kum_pnl"] - running_max
    max_dd = float(dd.min())

    # Sharpe (per Trade)
    if pnl.std() > 0:
        sharpe = float(pnl.mean() / pnl.std() * np.sqrt(252))
    else:
        sharpe = 0.0

    # Streaks
    signs = (pnl > 0).astype(int).tolist()
    longest_win = 0
    longest_loss = 0
    cur_w = 0
    cur_l = 0
    for s in signs:
        if s:
            cur_w += 1
            cur_l = 0
            longest_win = max(longest_win, cur_w)
        else:
            cur_l += 1
            cur_w = 0
            longest_loss = max(longest_loss, cur_l)

    return {
        "n": n,
        "net_profit": net,
        "return_pct": return_pct,
        "cagr": cagr,
        "win_rate": win_rate,
        "profit_factor": pf,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "best": float(pnl.max()),
        "worst": float(pnl.min()),
        "streak_win": longest_win,
        "streak_loss": longest_loss,
    }


def monthly_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Jahre x Monate Raster aus kum_pnl-Differenzen."""

    if df.empty:
        return pd.DataFrame()

    s = df.set_index("datum")["kum_pnl"]
    monthly_end = s.resample("ME").last()
    monthly_diff = monthly_end.diff()
    monthly_diff.iloc[0] = monthly_end.iloc[0]

    result = pd.DataFrame({
        "Year": monthly_diff.index.year,
        "Month": monthly_diff.index.month,
        "Return": monthly_diff.values,
    })

    pivot = result.pivot(index="Year", columns="Month", values="Return")
    month_names = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    pivot.columns = [month_names[m - 1] for m in pivot.columns]

    return pivot
