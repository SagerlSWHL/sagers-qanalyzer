"""
portfolio.py
------------
Portfolio-Seite des Sagers qAnalyzer.

Erlaubt das Hochladen mehrerer Strategie-Dateien und zeigt
eine kombinierte Portfolio-Ansicht.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.analyzer_engine import analyze_trades
from core.data_loader import load_trades, load_trading_data
from core.portfolio_engine import build_equity_matrix, combine_equity


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def _is_quantitativo_excel(uploaded_file) -> bool:
    """
    Prüft, ob eine Excel-Datei ein Quantitativo-Export ist
    (Sheet 'Handelsgeschäfte' vorhanden).
    """
    if not uploaded_file.name.lower().endswith((".xlsx", ".xls")):
        return False
    try:
        xls = pd.ExcelFile(uploaded_file)
        return "Handelsgeschäfte" in xls.sheet_names
    except Exception:
        return False


def _load_uploaded(uploaded_file):
    """
    Lädt eine hochgeladene Datei – Quantitativo-Excel oder generisch.
    """
    if _is_quantitativo_excel(uploaded_file):
        return load_trades(uploaded_file)
    return load_trading_data(uploaded_file)


def _strategy_name(filename: str) -> str:
    """
    Kürzt einen Dateinamen zu einem lesbaren Strategie-Namen.
    """
    name = filename.rsplit(".", 1)[0]
    return name


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_portfolio():
    """
    Zeigt die Portfolio-Seite.
    """

    st.title("Portfolio")
    st.write("Combine multiple strategies into one portfolio.")
    st.divider()

    # -----------------------------------------------------
    # DATEI-IMPORT (mehrere Dateien)
    # -----------------------------------------------------

    st.subheader("Import Strategies")

    uploaded_files = st.file_uploader(
        "Excel- oder CSV-Dateien auswählen (mehrere möglich)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("Noch keine Strategien geladen.")
        return

    # -----------------------------------------------------
    # STRATEGIEN LADEN
    # -----------------------------------------------------

    strategies = {}

    for file in uploaded_files:
        try:
            trades = _load_uploaded(file)
            if trades is not None and not trades.empty:
                strategies[_strategy_name(file.name)] = trades
        except Exception as exc:
            st.warning(f"Konnte '{file.name}' nicht laden: {exc}")

    if not strategies:
        st.error("Keine gültigen Strategien gefunden.")
        return

    st.success(f"{len(strategies)} Strategie(n) geladen: "
               + ", ".join(strategies.keys()))

    # -----------------------------------------------------
    # PORTFOLIO-KENNZAHLEN
    # -----------------------------------------------------

    combined = combine_equity(strategies)

    # Gesamtnetto
    total_net = sum(
        float(df["Netto G&V USD"].sum())
        for df in strategies.values()
        if "Netto G&V USD" in df.columns
    )

    total_trades = sum(len(df) for df in strategies.values())

    if not combined.empty:
        portfolio_return = float(combined.iloc[-1])
        portfolio_dd = float((combined - combined.cummax()).min())
    else:
        portfolio_return = 0.0
        portfolio_dd = 0.0

    st.subheader("Portfolio Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Strategien", len(strategies))
    with col2:
        st.metric("Trades gesamt", total_trades)
    with col3:
        st.metric("Net Profit gesamt", f"${total_net:,.2f}")
    with col4:
        st.metric("Portfolio Return", f"{portfolio_return:.2f} %")

    st.divider()

    # -----------------------------------------------------
    # STRATEGIE-VERGLEICH (Tabelle)
    # -----------------------------------------------------

    st.subheader("Strategie Comparison")

    rows = []

    for name, df in strategies.items():
        result = analyze_trades(df)
        rows.append({
            "Strategie": name,
            "Trades": result["total_trades"],
            "Net Profit": result["net_profit"],
            "Win Rate %": round(result["win_rate"], 2),
            "Profit Factor": round(result["profit_factor"], 3),
            "Max DD %": round(result["max_drawdown"], 2),
            "Expectancy": round(result["expectancy"], 2),
        })

    comparison = pd.DataFrame(rows)
    comparison = comparison.sort_values("Net Profit", ascending=False)

    st.dataframe(comparison, use_container_width=True, hide_index=True)

    st.divider()

    # -----------------------------------------------------
    # EQUITY CURVES
    # -----------------------------------------------------

    tab_combined, tab_individual = st.tabs(
        ["Portfolio (kombiniert)", "Einzelne Strategien"]
    )

    with tab_combined:
        _show_combined_equity(combined)

    with tab_individual:
        _show_individual_equity(strategies)


# =========================================================
# KOMBINIERTE EQUITY CURVE
# =========================================================

def _show_combined_equity(combined: pd.Series):
    """
    Zeigt die kombinierte Portfolio-Equity-Curve.
    """

    st.subheader("Combined Equity")

    if combined.empty:
        st.info("Keine Portfolio-Daten verfügbar.")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=combined.index,
            y=combined.values,
            mode="lines",
            name="Portfolio",
            line=dict(color="#60A5FA", width=2),
        )
    )

    fig.update_layout(
        height=420,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(title="Return %", gridcolor="#333"),
    )

    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# EINZELNE EQUITY CURVES
# =========================================================

def _show_individual_equity(strategies: dict):
    """
    Zeigt alle Strategie-Equity-Curves überlagert.
    """

    st.subheader("Individual Equity Curves")

    matrix = build_equity_matrix(strategies)

    if matrix.empty:
        st.info("Keine Daten verfügbar.")
        return

    fig = go.Figure()

    for col in matrix.columns:
        fig.add_trace(
            go.Scatter(
                x=matrix.index,
                y=matrix[col],
                mode="lines",
                name=col,
                line=dict(width=1.5),
            )
        )

    fig.update_layout(
        height=420,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(title="Return %", gridcolor="#333"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)