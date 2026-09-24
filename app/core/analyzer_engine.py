"""
analyzer_engine.py
------------------
Kombiniert alle Einzelkennzahlen aus metrics.py zu einem
kompakten Ergebnis-Dictionary für eine Strategie.

Eingabe: Trade-Level-DataFrame (siehe load_trades)
Ausgabe: dict mit allen relevanten Kennzahlen
"""

import pandas as pd

from core import metrics


# =========================================================
# HAUPTFUNKTION
# =========================================================

def analyze_trades(df: pd.DataFrame) -> dict:
    """
    Berechnet alle Kennzahlen aus einem Trade-Level-DataFrame.

    Parameter
    ---------
    df : pd.DataFrame
        Ausgabe von load_trades() – ein Trade pro Zeile.

    Rückgabe
    --------
    dict mit folgenden Schlüsseln:

        net_profit          Summe P&L in USD
        gross_profit        Summe aller Gewinner
        gross_loss          Summe aller Verlierer
        total_trades        Anzahl Trades
        winning_trades      Anzahl Gewinner
        losing_trades       Anzahl Verlierer
        breakeven_trades    Anzahl Breakeven-Trades
        win_rate            Gewinnquote in %
        profit_factor       Bruttogewinn / Bruttoverlust
        avg_win             durchschnittlicher Gewinn
        avg_loss            durchschnittlicher Verlust
        expectancy          Erwartungswert pro Trade
        max_drawdown        maximaler Drawdown in %
    """

    if df is None or df.empty:
        return _empty_result()

    return {
        "net_profit": metrics.net_profit(df),
        "gross_profit": metrics.gross_profit(df),
        "gross_loss": metrics.gross_loss(df),
        "total_trades": metrics.total_trades(df),
        "winning_trades": metrics.winning_trades(df),
        "losing_trades": metrics.losing_trades(df),
        "breakeven_trades": metrics.breakeven_trades(df),
        "win_rate": metrics.win_rate(df),
        "profit_factor": metrics.profit_factor(df),
        "avg_win": metrics.avg_win(df),
        "avg_loss": metrics.avg_loss(df),
        "expectancy": metrics.expectancy(df),
        "max_drawdown": metrics.max_drawdown(df),
    }


# =========================================================
# HILFSFUNKTION: LEERES ERGEBNIS
# =========================================================

def _empty_result() -> dict:
    """
    Gibt ein Ergebnis-Dictionary mit Null-Werten zurück.
    Nützlich, wenn noch keine Daten geladen wurden.
    """
    return {
        "net_profit": 0.0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "breakeven_trades": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "expectancy": 0.0,
        "max_drawdown": 0.0,
    }
