"""
analyzer.py
-----------
Analyzer-Seite des Sagers qAnalyzer.

Erlaubt das Hochladen einer Trading-Datei (CSV/Excel),
lädt die Trades, berechnet alle Kennzahlen und zeigt sie an.

Zusätzlich: Button für synthetische Beispieldaten (keine echten Strategien).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import numpy as np

from core.data_loader import load_trades, load_trading_data
from core.analyzer_engine import analyze_trades
from core.synthetic_data import generate_single_strategy


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

    col_upload, col_sample = st.columns([3, 1])

    with col_upload:
        uploaded_file = st.file_uploader(
            "CSV- oder Excel-Datei auswählen",
            type=["csv", "xlsx", "xls"],
        )

    with col_sample:
        st.write("")
        st.write("")
        if st.button("🎲  Beispiel", use_container_width=True):
            st.session_state["use_synthetic"] = True

    # -----------------------------------------------------
    # QUELLE BESTIMMEN
    # -----------------------------------------------------

    if uploaded_file is not None:
        st.session_state["use_synthetic"] = False
        source = uploaded_file
        is_synthetic = False
    elif st.session_state.get("use_synthetic"):
        source = None
        is_synthetic = True
        st.info("📊 Synthetische Beispielstrategie geladen (keine echten Daten).")
    else:
        st.info("Noch keine Trading-Datei geladen.")
        return

    # -----------------------------------------------------
    # DATEN LADEN
    # -----------------------------------------------------

    try:
        if is_synthetic:
            trades = generate_single_strategy(seed=7)
        else:
            trades = _load_uploaded(source)
    except Exception as exc:
        st.error(f"Fehler beim Laden der Datei: {exc}")
        return

    if trades is None or trades.empty:
        st.warning("Die Datei enthält keine Trades.")
        return

    if is_synthetic:
        st.success(f"Datei geladen: Beispieldaten ({len(trades)} Trades)")
    else:
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

    tab_equity, tab_dd, tab_monthly, tab_dist, tab_trades = st.tabs(
        ["Equity Curve", "Drawdown", "Monthly", "Distribution", "Trades"]
    )

    with tab_equity:
        _show_equity_chart(trades)

    with tab_dd:
        _show_drawdown_chart(trades)

    with tab_monthly:
        _show_monthly_heatmap(trades)

    with tab_dist:
        _show_trade_distribution(trades)

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
# DRAWDOWN CHART
# =========================================================

def _show_drawdown_chart(trades: pd.DataFrame):
    """
    Zeichnet die Drawdown-Kurve (Rückgang vom bisherigen Höchststand).
    """

    st.subheader("Drawdown")

    if "Kumulierter G&V %" not in trades.columns:
        st.info("Keine Equity-Daten gefunden.")
        return

    from core.metrics import drawdown_series

    dd = drawdown_series(trades)

    if "Datum und Uhrzeit" in trades.columns:
        chart_data = dd.copy()
        chart_data.index = trades["Datum und Uhrzeit"]
    else:
        chart_data = dd

    chart_data.name = "Drawdown %"
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


# =========================================================
# MONTHLY HEATMAP
# =========================================================

def _show_monthly_heatmap(trades: pd.DataFrame):
    """
    Zeigt die Monatsrenditen als farbige Heatmap.
    Grün = positiv, Rot = negativ.
    """

    st.subheader("Monthly Returns")

    from core.metrics import monthly_returns

    pivot = monthly_returns(trades)

    if pivot is None or pivot.empty:
        st.info("Keine Monatsdaten gefunden.")
        return

    text = pivot.map(
        lambda v: f"{v:+.2f}" if pd.notna(v) else ""
    )

    max_abs = float(pivot.abs().max().max())

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index.astype(str),
            text=text.values,
            texttemplate="%{text}",
            textfont={"size": 11},
            colorscale=[
                [0.0, "#8B0000"],
                [0.5, "#1a1a1a"],
                [1.0, "#0F8B3C"],
            ],
            zmid=0,
            zmin=-max_abs,
            zmax=max_abs,
            showscale=True,
            hoverongaps=False,
            colorbar=dict(
                title="%",
                ticksuffix="%",
            ),
        )
    )

    fig.update_layout(
        height=420,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(side="top"),
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# TRADE DISTRIBUTION (Histogramm)
# =========================================================

def _show_trade_distribution(trades: pd.DataFrame):
    """
    Histogramm der P&L-Werte pro Trade.
    Farbe: rot für Verluste, grün für Gewinne.
    """

    st.subheader("Trade Distribution")

    if "Netto G&V USD" not in trades.columns:
        st.info("Keine P&L-Daten gefunden.")
        return

    pnl = trades["Netto G&V USD"]

    counts, bin_edges = np.histogram(pnl, bins=40)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    colors = [
        "#EF4444" if center < 0 else "#22C55E"
        for center in bin_centers
    ]

    fig = go.Figure(
        data=go.Bar(
            x=bin_centers,
            y=counts,
            marker_color=colors,
            marker_line_width=0,
            hovertemplate="P&L: %{x:,.0f} USD<br>Anzahl: %{y}<extra></extra>",
        )
    )

    fig.update_layout(
        height=420,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(title="P&L (USD)", gridcolor="#333"),
        yaxis=dict(title="Anzahl Trades", gridcolor="#333"),
        bargap=0.02,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Bester Trade", f"${pnl.max():,.2f}")
    with col2:
        st.metric("Schlechtester Trade", f"${pnl.min():,.2f}")
    with col3:
        st.metric("Median", f"${pnl.median():,.2f}")
    with col4:
        st.metric("Std-Abweichung", f"${pnl.std():,.2f}")