"""
analyzer.py
-----------
Analyzer-Seite des Sagers qAnalyzer.

Erlaubt das Hochladen einer Trading-Datei (CSV/Excel),
lädt die Trades, berechnet alle Kennzahlen und zeigt sie an.
"""

import pandas as pd
import streamlit as st

from core.data_loader import load_trades, load_trading_data
from core.analyzer_engine import analyze_trades


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def _is_quantitativo_excel(uploaded_file) -> bool:
    """
    Prüft, ob die hochgeladene Excel-Datei ein Quantitativo-Export ist
    (erkennbar am Sheet 'Handelsgeschäfte').
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
    Lädt die hochgeladene Datei passend zum Format.
    Gibt einen Trade-Level-DataFrame zurück.
    """
    if _is_quantitativo_excel(uploaded_file):
        return load_trades(uploaded_file)

    # Fallback: generische CSV/Excel
    return load_trading_data(uploaded_file)


def _format_currency(value: float) -> str:
    return f"${value:,.2f}"


def _format_percent(value: float) -> str:
    return f"{value:.2f} %"


def _format_number(value: float) -> str:
    return f"{value:,.2f}"


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_analyzer():
    """
    Zeigt den Analyzer des Sagers qAnalyzer.
    """

    st.title("Analyzer")
    st.write("Analyze individual trading strategies and trading results.")
    st.divider()

    # -----------------------------------------------------
    # DATEI IMPORT
    # -----------------------------------------------------

    st.subheader("Import Trading Data")

    uploaded_file = st.file_uploader(
        "CSV- oder Excel-Datei auswählen",
        type=["csv", "xlsx", "xls"]
    )

    if uploaded_file is None:
        st.info("Noch keine Trading-Datei geladen.")
        return

    # -----------------------------------------------------
    # DATEI LADEN
    # -----------------------------------------------------

    try:
        trades = _load_uploaded(uploaded_file)
    except Exception as exc:
        st.error(f"Fehler beim Laden der Datei: {exc}")
        return

    if trades is None or trades.empty:
        st.warning("Die Datei enthält keine Trades.")
        return

    st.success(f"Datei geladen: {uploaded_file.name}  ({len(trades)} Trades)")

    # -----------------------------------------------------
    # ANALYSE
    # -----------------------------------------------------

    result = analyze_trades(trades)

    # -----------------------------------------------------
    # KPI-KARTEN (Zeile 1)
    # -----------------------------------------------------

    st.subheader("Performance")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Net Profit", _format_currency(result["net_profit"]))

    with col2:
        st.metric("Win Rate", _format_percent(result["win_rate"]))

    with col3:
        st.metric("Profit Factor", _format_number(result["profit_factor"]))

    with col4:
        st.metric("Max Drawdown", _format_percent(result["max_drawdown"]))

    # -----------------------------------------------------
    # KPI-KARTEN (Zeile 2)
    # -----------------------------------------------------

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric("Trades", result["total_trades"])

    with col6:
        st.metric("Avg Win", _format_currency(result["avg_win"]))

    with col7:
        st.metric("Avg Loss", _format_currency(result["avg_loss"]))

    with col8:
        st.metric("Expectancy", _format_currency(result["expectancy"]))

    st.divider()

    # -----------------------------------------------------
    # TABS
    # -----------------------------------------------------

    tab_chart, tab_trades = st.tabs(["Equity Curve", "Trades"])

    with tab_chart:
        _show_equity_chart(trades)

    with tab_trades:
        _show_trades_table(trades)


# =========================================================
# EQUITY CHART
# =========================================================

def _show_equity_chart(trades: pd.DataFrame):
    """
    Zeichnet die Equity-Kurve aus 'Kumulierter G&V %'.
    """

    st.subheader("Equity Curve")

    if "Kumulierter G&V %" not in trades.columns:
        st.info(
            "Keine Equity-Daten gefunden. "
            "Diese Ansicht funktioniert aktuell für Quantitativo-Exporte."
        )
        return

    if "Datum und Uhrzeit" in trades.columns:
        chart_data = trades[["Datum und Uhrzeit", "Kumulierter G&V %"]].copy()
        chart_data = chart_data.set_index("Datum und Uhrzeit")
    else:
        chart_data = trades[["Kumulierter G&V %"]].copy()

    st.line_chart(chart_data)


# =========================================================
# TRADES TABELLE
# =========================================================

def _show_trades_table(trades: pd.DataFrame):
    """
    Zeigt die Trades als Tabelle.
    """

    st.subheader("Trades")

    st.dataframe(
        trades,
        use_container_width=True,
        hide_index=True,
    )
