"""
statistics.py
-------------
Statistics-Seite des Sagers qAnalyzer.

Zeigt alle Kennzahlen ausführlich in Kategorien.
  - Portfolio-Modus: Vergleichstabelle aller Strategien
  - Einzelstrategie-Modus: Kennzahlen in Kategorien
"""

import pandas as pd
import streamlit as st

from core.analyzer_engine import analyze_trades
from core.metrics import cagr, drawdown_stats, sharpe_ratio, sortino_ratio
from core.portfolio_engine import combine_equity
from core.state import get_strategies, get_trades


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_statistics():
    """Zeigt die Statistics-Seite."""

    st.title("Statistics")
    st.write("Alle Kennzahlen ausführlich – einzeln oder im Vergleich.")

    trades = get_trades()
    strategies = get_strategies()

    has_single = trades is not None and not trades.empty
    has_portfolio = bool(strategies)

    if not has_single and not has_portfolio:
        st.info(
            "⚠️ **Keine Daten geladen.** "
            "Lade im **Analyzer** eine Einzelstrategie "
            "oder im **Portfolio** mehrere Strategien."
        )
        return

    # -----------------------------------------------------
    # MODUS-WAHL
    # -----------------------------------------------------

    if has_single and has_portfolio:
        mode = st.radio(
            "Ansicht:",
            options=["📊 Portfolio-Vergleich", "📄 Einzelstrategie"],
            index=0,
            horizontal=True,
            key="stats_mode_radio",
        )
    elif has_single:
        mode = "📄 Einzelstrategie"
    else:
        mode = "📊 Portfolio-Vergleich"

    st.divider()

    # -----------------------------------------------------
    # WEITERLEITUNG
    # -----------------------------------------------------

    if mode.startswith("📊"):
        _show_portfolio_stats(strategies)
    else:
        _show_single_stats(trades)


# =========================================================
# PORTFOLIO-VERGLEICH
# =========================================================

def _show_portfolio_stats(strategies: dict):
    """Tabelle mit allen Kennzahlen pro Strategie."""

    st.subheader("Strategie-Vergleich")

    rows = []

    for name, df in strategies.items():
        if df is None or df.empty:
            continue

        r = analyze_trades(df)
        dd_stats = drawdown_stats(df)

        rows.append({
            "Strategie": name,
            "Trades": r["total_trades"],
            "Win Rate %": round(r["win_rate"], 2),
            "Net Profit": round(r["net_profit"], 2),
            "CAGR %": round(r["cagr"], 2),
            "Profit Factor": round(r["profit_factor"], 3),
            "Sharpe": round(r["sharpe_ratio"], 3),
            "Sortino": round(r["sortino_ratio"], 3),
            "Expectancy": round(r["expectancy"], 2),
            "Max DD %": round(r["max_drawdown"], 2),
        })

    if not rows:
        st.info("Keine Strategien mit Daten gefunden.")
        return

    summary = pd.DataFrame(rows)

    # Sortierung nach Net Profit
    summary = summary.sort_values("Net Profit", ascending=False).reset_index(drop=True)

    st.dataframe(
        summary,
        width="stretch",
        hide_index=True,
        height=min(600, 40 * len(summary) + 40),
    )

    # -----------------------------------------------------
    # PORTFOLIO-GESAMT
    # -----------------------------------------------------

    st.divider()
    st.subheader("Portfolio-Gesamt")

    total_trades = int(summary["Trades"].sum())
    total_net = float(summary["Net Profit"].sum())
    avg_wr = float(summary["Win Rate %"].mean())
    avg_pf = float(summary["Profit Factor"].mean())

    combined = combine_equity(strategies)

    if not combined.empty:
        portfolio_df = pd.DataFrame({
            "Kumulierter G&V %": combined.values,
            "Datum und Uhrzeit": combined.index,
        })
        portfolio_return = float(combined.iloc[-1])
        portfolio_dd = float((combined - combined.cummax()).min())
        portfolio_cagr = cagr(portfolio_df)
        portfolio_sharpe = sharpe_ratio(portfolio_df)
        portfolio_sortino = sortino_ratio(portfolio_df)
    else:
        portfolio_return = 0.0
        portfolio_dd = 0.0
        portfolio_cagr = 0.0
        portfolio_sharpe = 0.0
        portfolio_sortino = 0.0

        # -----------------------------------------------------
    # KPI-ZEILE 1 – RENDITE & RISIKO
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Trades gesamt", total_trades)
    with col2:
        st.metric("Net Profit gesamt", f"${total_net:,.2f}")
    with col3:
        st.metric("Portfolio Return", f"{portfolio_return:.2f} %")
    with col4:
        st.metric("Portfolio Max DD", f"{portfolio_dd:.2f} %")

    # -----------------------------------------------------
    # KPI-ZEILE 2 – PERFORMANCE-KENNZAHLEN
    # -----------------------------------------------------

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric("Portfolio CAGR", f"{portfolio_cagr:.2f} %")
    with col6:
        st.metric("Portfolio Sharpe", f"{portfolio_sharpe:.3f}")
    with col7:
        st.metric("Portfolio Sortino", f"{portfolio_sortino:.3f}")
    with col8:
        ratio = abs(portfolio_return / portfolio_dd) if portfolio_dd != 0 else 0
        st.metric("Return / DD", f"{ratio:.2f}")

    # -----------------------------------------------------
    # KPI-ZEILE 3 – DURCHSCHNITTE
    # -----------------------------------------------------

    col9, col10, col11 = st.columns(3)

    with col9:
        st.metric("Ø Win Rate", f"{avg_wr:.2f} %")
    with col10:
        st.metric("Ø Profit Factor", f"{avg_pf:.3f}")
    with col11:
        st.metric("Strategien", len(summary))


# =========================================================
# EINZELSTRATEGIE-KENNZAHLEN
# =========================================================

def _show_single_stats(trades: pd.DataFrame):
    """Zeigt alle Kennzahlen einer Einzelstrategie in Kategorien."""

    r = analyze_trades(trades)
    dd_stats = drawdown_stats(trades)

    # -----------------------------------------------------
    # PERFORMANCE
    # -----------------------------------------------------

    st.subheader("Performance")

    perf = pd.DataFrame([
        {"Kennzahl": "Net Profit", "Wert": f"${r['net_profit']:,.2f}"},
        {"Kennzahl": "CAGR", "Wert": f"{r['cagr']:.2f} %"},
        {"Kennzahl": "Bruttogewinn", "Wert": f"${r['gross_profit']:,.2f}"},
        {"Kennzahl": "Bruttoverlust", "Wert": f"${r['gross_loss']:,.2f}"},
        {"Kennzahl": "Erwartung pro Trade", "Wert": f"${r['expectancy']:,.2f}"},
    ])

    st.dataframe(perf, width="stretch", hide_index=True)

    # -----------------------------------------------------
    # TRADES
    # -----------------------------------------------------

    st.subheader("Trades")

    trades_stats = pd.DataFrame([
        {"Kennzahl": "Trades gesamt", "Wert": r["total_trades"]},
        {"Kennzahl": "Gewinner", "Wert": r["winning_trades"]},
        {"Kennzahl": "Verlierer", "Wert": r["losing_trades"]},
        {"Kennzahl": "Breakeven", "Wert": r["breakeven_trades"]},
        {"Kennzahl": "Win Rate", "Wert": f"{r['win_rate']:.2f} %"},
        {"Kennzahl": "Profit Factor", "Wert": f"{r['profit_factor']:.3f}"},
    ])

    st.dataframe(trades_stats, width="stretch", hide_index=True)

    # -----------------------------------------------------
    # TRADE-DURCHSCHNITTE
    # -----------------------------------------------------

    st.subheader("Durchschnitte pro Trade")

    avg = pd.DataFrame([
        {"Kennzahl": "Ø Gewinn (Winner)", "Wert": f"${r['avg_win']:,.2f}"},
        {"Kennzahl": "Ø Verlust (Loser)", "Wert": f"${r['avg_loss']:,.2f}"},
        {
            "Kennzahl": "Gewinn / Verlust-Verhältnis",
            "Wert": (
                f"{(r['avg_win'] / r['avg_loss']):.3f}"
                if r["avg_loss"] > 0
                else "–"
            ),
        },
    ])

    st.dataframe(avg, width="stretch", hide_index=True)

    # -----------------------------------------------------
    # RISIKO
    # -----------------------------------------------------

    st.subheader("Risiko")

    risk = pd.DataFrame([
        {"Kennzahl": "Max Drawdown", "Wert": f"{dd_stats['max_drawdown']:.2f} %"},
        {"Kennzahl": "Ø Drawdown", "Wert": f"{dd_stats['avg_drawdown']:.2f} %"},
        {"Kennzahl": "Aktuell", "Wert": f"{dd_stats['current_drawdown']:.2f} %"},
        {"Kennzahl": "Sharpe Ratio", "Wert": f"{r['sharpe_ratio']:.3f}"},
        {"Kennzahl": "Sortino Ratio", "Wert": f"{r['sortino_ratio']:.3f}"},
    ])

    st.dataframe(risk, width="stretch", hide_index=True)