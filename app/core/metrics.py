"""
metrics.py
----------
Einzelne Kennzahlen für Trading-Analysen.

Jede Funktion ist "pure": sie bekommt einen DataFrame (oder eine Serie)
und gibt einen einzelnen Wert zurück. Keine Seiteneffekte.

Alle Funktionen erwarten als Eingabe den Trade-Level-DataFrame
(also den Output von load_trades()), mit den Spalten:
    - 'Netto G&V USD'   → P&L pro Trade in USD
    - 'Kumulierter G&V %' → kumulierter Return (Equity-Kurve in %)
"""

import numpy as np
import pandas as pd


# =========================================================
# KONSTANTEN (Spaltennamen)
# =========================================================

COL_PNL = "Netto G&V USD"
COL_EQUITY = "Kumulierter G&V %"


# =========================================================
# GEWINN / VERLUST BASIS
# =========================================================

def net_profit(df: pd.DataFrame) -> float:
    """Summe aller P&L (Netto-Gewinn in USD)."""
    return float(df[COL_PNL].sum())


def gross_profit(df: pd.DataFrame) -> float:
    """Summe aller positiven P&L."""
    return float(df.loc[df[COL_PNL] > 0, COL_PNL].sum())


def gross_loss(df: pd.DataFrame) -> float:
    """Summe aller negativen P&L (als positiver Betrag)."""
    return float(-df.loc[df[COL_PNL] < 0, COL_PNL].sum())


# =========================================================
# TRADE-ANZAHLEN
# =========================================================

def total_trades(df: pd.DataFrame) -> int:
    """Anzahl aller Trades."""
    return int(len(df))


def winning_trades(df: pd.DataFrame) -> int:
    """Anzahl Gewinner."""
    return int((df[COL_PNL] > 0).sum())


def losing_trades(df: pd.DataFrame) -> int:
    """Anzahl Verlierer."""
    return int((df[COL_PNL] < 0).sum())


def breakeven_trades(df: pd.DataFrame) -> int:
    """Anzahl Trades mit P&L == 0."""
    return int((df[COL_PNL] == 0).sum())


# =========================================================
# RATEN & VERHÄLTNISSE
# =========================================================

def win_rate(df: pd.DataFrame) -> float:
    """Anteil Gewinner an allen Trades (in %)."""
    total = total_trades(df)
    if total == 0:
        return 0.0
    return 100.0 * winning_trades(df) / total


def profit_factor(df: pd.DataFrame) -> float:
    """
    Bruttogewinn / Bruttoverlust.
    > 1 bedeutet profitabel, < 1 unprofitabel.
    """
    gl = gross_loss(df)
    if gl == 0:
        return float("inf") if gross_profit(df) > 0 else 0.0
    return gross_profit(df) / gl


def avg_win(df: pd.DataFrame) -> float:
    """Durchschnittlicher Gewinn pro Gewinner-Trade."""
    winners = df.loc[df[COL_PNL] > 0, COL_PNL]
    if winners.empty:
        return 0.0
    return float(winners.mean())


def avg_loss(df: pd.DataFrame) -> float:
    """Durchschnittlicher Verlust pro Verlierer-Trade (als positiver Betrag)."""
    losers = df.loc[df[COL_PNL] < 0, COL_PNL]
    if losers.empty:
        return 0.0
    return float(-losers.mean())


def expectancy(df: pd.DataFrame) -> float:
    """
    Erwartungswert pro Trade:
    (WinRate * AvgWin) - (LossRate * AvgLoss)
    """
    total = total_trades(df)
    if total == 0:
        return 0.0

    wr = winning_trades(df) / total
    lr = losing_trades(df) / total
    return (wr * avg_win(df)) - (lr * avg_loss(df))


# =========================================================
# DRAWDOWN
# =========================================================

def max_drawdown(df: pd.DataFrame) -> float:
    """
    Maximaler Drawdown der Equity-Kurve in Prozentpunkten.

    Die Equity-Kurve ist 'Kumulierter G&V %'.
    Wir berechnen den größten Rückgang vom jeweils vorherigen Höchststand.
    """

    equity = df[COL_EQUITY]

    # Bisheriges Maximum (kumulativ)
    running_max = equity.cummax()

    # Drawdown = aktueller Wert minus bisheriges Maximum
    drawdown = equity - running_max

    return float(drawdown.min())



# =========================================================
# DRAWDOWN-SERIE (für Chart)
# =========================================================

def drawdown_series(df: pd.DataFrame) -> pd.Series:
    """
    Gibt die komplette Drawdown-Kurve in Prozentpunkten zurück.

    Für jeden Punkt der Equity-Kurve:
        drawdown = equity - bisheriges Maximum
    """

    equity = df[COL_EQUITY]
    running_max = equity.cummax()
    return equity - running_max



# =========================================================
# MONATSRENDITEN (für Heatmap)
# =========================================================

def monthly_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Berechnet die Monatsrendite in % pro Jahr/Monat.

    Vorgehen:
    1. Kumulierte Equity in eine Zeitreihe umwandeln
    2. Pro Monat: den letzten kumulierten Wert nehmen
    3. Differenz zum Vormonat = Monatsrendite

    Rückgabe: DataFrame mit Jahren als Zeilen, Monaten als Spalten,
    Werte = Rendite in %.
    """

    # Brauchen Datum und kumulierte Equity
    if "Datum und Uhrzeit" not in df.columns:
        return pd.DataFrame()

    series = df[["Datum und Uhrzeit", COL_EQUITY]].copy()
    series = series.set_index("Datum und Uhrzeit")
    series.index = pd.to_datetime(series.index)
    series = series.sort_index()

    # Kumulierter Wert am Ende jedes Monats
    monthly_end = series[COL_EQUITY].resample("ME").last()

    # Differenz zum Vormonat (Monatsänderung in Prozentpunkten)
    monthly_diff = monthly_end.diff()

    # Erster Monat: Wert selbst (Startwert war 0)
    monthly_diff.iloc[0] = monthly_end.iloc[0]

    # In ein Jahr × Monat Raster umformen
    result = pd.DataFrame({
        "Year": monthly_diff.index.year,
        "Month": monthly_diff.index.month,
        "Return": monthly_diff.values,
    })

    pivot = result.pivot(index="Year", columns="Month", values="Return")

    # Monate als Namen
    month_names = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    pivot.columns = [month_names[m - 1] for m in pivot.columns]

    return pivot



# =========================================================
# DRAWDOWN-STATISTIK (kompakt)
# =========================================================

def drawdown_stats(df: pd.DataFrame) -> dict:
    """
    Liefert die wichtigsten Drawdown-Kennzahlen einer Strategie.

    Rückgabe
    --------
    dict mit:
        max_drawdown         tiefster Rückgang in %
        avg_drawdown         durchschnittlicher Rückgang (nur negative)
        current_drawdown     aktueller Rückgang (letzter Wert)
        longest_underwater   längste Phase unter Wasser (in Trades)
        current_underwater   aktuelle Phase unter Wasser (in Trades)
        total_trades         Anzahl Trades
    """

    equity = df[COL_EQUITY]
    running_max = equity.cummax()
    dd = equity - running_max

    max_dd = float(dd.min())

    negatives = dd[dd < 0]
    avg_dd = float(negatives.mean()) if not negatives.empty else 0.0

    current_dd = float(dd.iloc[-1]) if len(dd) else 0.0

    # Längste und aktuelle „unter Wasser"-Phase
    underwater = (dd < 0).astype(int).tolist()

    longest = 0
    current_run = 0
    for v in underwater:
        if v:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 0

    # Aktuelle Phase (vom Ende rückwärts)
    current_run = 0
    for v in reversed(underwater):
        if v:
            current_run += 1
        else:
            break

    return {
        "max_drawdown": max_dd,
        "avg_drawdown": avg_dd,
        "current_drawdown": current_dd,
        "longest_underwater": int(longest),
        "current_underwater": int(current_run),
        "total_trades": len(df),
    }



# =========================================================
# DRAWDOWN-DAUER (Peak → Trough, wie Quantitativo/Excel)
# =========================================================

def drawdown_duration_stats(df: pd.DataFrame) -> dict:
    """
    Berechnet Drawdown-Dauern nach Excel-Logik (Peak → Trough).

    Eine Drawdown-Phase beginnt beim Peak (letztes Hoch) und endet
    beim Tiefpunkt (Trough), bevor ein neues Hoch erreicht wird.

    Rückgabe
    --------
    dict mit:
        n_phases       Anzahl Drawdown-Phasen
        avg_duration   durchschnittliche Dauer (Peak → Trough)
        max_duration   längste Dauer (Peak → Trough)
    """

    equity = df[COL_EQUITY].reset_index(drop=True)
    running_max = equity.cummax()
    dd = equity - running_max

    durations = []
    current_peak_idx = 0
    in_drawdown = False
    deepest_idx = 0
    deepest_val = 0.0

    for i in range(len(dd)):
        val = float(dd.iloc[i])

        if val < 0:
            if not in_drawdown:
                in_drawdown = True
                current_peak_idx = max(i - 1, 0)
                deepest_idx = i
                deepest_val = val
            elif val < deepest_val:
                deepest_val = val
                deepest_idx = i
        else:
            if in_drawdown:
                durations.append(deepest_idx - current_peak_idx)
                in_drawdown = False
                deepest_idx = 0
                deepest_val = 0.0

    # Offene Phase am Ende
    if in_drawdown:
        durations.append(deepest_idx - current_peak_idx)

    if not durations:
        return {"n_phases": 0, "avg_duration": 0, "max_duration": 0}

    return {
        "n_phases": len(durations),
        "avg_duration": sum(durations) / len(durations),
        "max_duration": max(durations),
    }



# =========================================================
# CAGR (Compound Annual Growth Rate)
# =========================================================

def cagr(df: pd.DataFrame) -> float:
    """
    Jährliche Wachstumsrate in %.

    Annahme: Startkapital = 100 % (entspricht Kumulierter G&V % Basis).
    """

    if "Datum und Uhrzeit" not in df.columns:
        return 0.0

    equity = df[COL_EQUITY]
    dates = pd.to_datetime(df["Datum und Uhrzeit"], errors="coerce").dropna()

    if dates.empty:
        return 0.0

    years = (dates.max() - dates.min()).days / 365.25

    if years <= 0:
        return 0.0

    start = 100.0
    end = 100.0 + float(equity.iloc[-1])

    if end <= 0:
        return -100.0

    return ((end / start) ** (1.0 / years) - 1.0) * 100.0


# =========================================================
# SHARPE RATIO (per Trade)
# =========================================================

def sharpe_ratio(df: pd.DataFrame) -> float:
    """
    Sharpe Ratio basierend auf Trade-zu-Trade-Änderungen.
    (Nicht annualisiert – relativ vergleichbar zwischen Strategien.)
    """

    returns = df[COL_EQUITY].diff().dropna()

    if returns.empty:
        return 0.0

    std = returns.std()

    if std == 0 or pd.isna(std):
        return 0.0

    return float(returns.mean() / std)


# =========================================================
# SORTINO RATIO (per Trade)
# =========================================================

def sortino_ratio(df: pd.DataFrame) -> float:
    """
    Sortino Ratio – wie Sharpe, aber nur mit der Downside-Volatilität.
    """

    returns = df[COL_EQUITY].diff().dropna()

    if returns.empty:
        return 0.0

    downside = returns[returns < 0]

    if downside.empty:
        return 0.0

    std = downside.std()

    if std == 0 or pd.isna(std):
        return 0.0

    return float(returns.mean() / std)