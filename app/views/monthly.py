"""
monthly.py
----------
Monthly-Seite des Sagers qAnalyzer.

Zeigt:
  - Heatmap: Jahre × Monate
  - Jahresübersicht: Summe, Anzahl positiver/negativer Monate
  - Bester & schlechtester Monat pro Jahr
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.metrics import monthly_returns
from core.portfolio_engine import combine_equity
from core.state import get_strategies, get_trades


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_monthly():
    """Zeigt die Monthly-Seite."""

    st.title("Monthly")
    st.write(
        "Monatsrenditen im Überblick – Jahr für Jahr, Monat für Monat."
    )
    st.divider()

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
            options=["📊 Portfolio (kombiniert)", "📄 Einzelstrategie"],
            index=0,
            horizontal=True,
            key="monthly_mode_radio",
        )
    elif has_single:
        mode = "📄 Einzelstrategie"
    else:
        mode = "📊 Portfolio (kombiniert)"

    # -----------------------------------------------------
    # DATEN AUFBEREITEN
    # -----------------------------------------------------

    if mode.startswith("📊"):
        combined = combine_equity(strategies)

        if combined.empty:
            st.warning("Portfolio-Daten konnten nicht kombiniert werden.")
            return

        df = pd.DataFrame({
            "Kumulierter G&V %": combined.values,
            "Datum und Uhrzeit": combined.index,
        })

        title = "Portfolio (kombiniert)"

    else:
        df = trades.copy()
        title = "Einzelstrategie"

    if "Kumulierter G&V %" not in df.columns:
        st.warning("Die geladenen Daten enthalten keine Equity-Kurve.")
        return

    # -----------------------------------------------------
    # MONATSRENDITEN BERECHNEN
    # -----------------------------------------------------

    pivot = monthly_returns(df)

    if pivot is None or pivot.empty:
        st.info("Keine Monatsdaten verfügbar.")
        return

    st.subheader(f"Monthly Heatmap · {title}")

    # -----------------------------------------------------
    # HEATMAP
    # -----------------------------------------------------

    _render_heatmap(pivot)

    st.divider()

    # -----------------------------------------------------
    # JAHRESÜBERSICHT
    # -----------------------------------------------------

    st.subheader("Jahresübersicht")

    _render_yearly_summary(pivot)

    st.divider()

    # -----------------------------------------------------
    # DETAILLIERTE TABELLE
    # -----------------------------------------------------

    with st.expander("📄  Rohdaten anzeigen"):
        st.dataframe(
            pivot.style.format("{:+.2f}", na_rep=""),
            width="stretch",
        )


# =========================================================
# HEATMAP RENDERN
# =========================================================

def _render_heatmap(pivot: pd.DataFrame):
    """Zeichnet die Jahre × Monate Heatmap."""

    text = pivot.map(lambda v: f"{v:+.2f}" if pd.notna(v) else "")

    max_abs = float(pivot.abs().max().max())
    if max_abs == 0:
        max_abs = 1.0

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
        height=40 * len(pivot) + 180,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(side="top"),
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig, width="stretch")


# =========================================================
# JAHRESÜBERSICHT
# =========================================================

def _render_yearly_summary(pivot: pd.DataFrame):
    """Baut die Jahresübersicht-Tabelle."""

    rows = []

    for year, row in pivot.iterrows():
        values = row.dropna()

        if values.empty:
            continue

        total = float(values.sum())
        pos_count = int((values > 0).sum())
        neg_count = int((values < 0).sum())
        best_month = values.idxmax()
        best_val = float(values.max())
        worst_month = values.idxmin()
        worst_val = float(values.min())

        rows.append({
            "Jahr": int(year),
            "Gesamt %": round(total, 2),
            "+ Monate": pos_count,
            "− Monate": neg_count,
            "Bester Monat": f"{best_month} ({best_val:+.2f}%)",
            "Schlechtester Monat": f"{worst_month} ({worst_val:+.2f}%)",
        })

    summary = pd.DataFrame(rows)

    if summary.empty:
        st.info("Keine Jahresdaten verfügbar.")
        return

    st.dataframe(
        summary,
        width="stretch",
        hide_index=True,
    )

    # Ein kleines Gesamtfazit
    total_return = summary["Gesamt %"].sum()
    best_year = summary.loc[summary["Gesamt %"].idxmax()]
    worst_year = summary.loc[summary["Gesamt %"].idxmin()]

    st.caption(
        f"**{len(summary)} Jahre** · "
        f"Gesamtrendite: **{total_return:+.2f} %** · "
        f"Bestes Jahr: **{int(best_year['Jahr'])} ({best_year['Gesamt %']:+.2f} %)** · "
        f"Schlechtestes Jahr: **{int(worst_year['Jahr'])} ({worst_year['Gesamt %']:+.2f} %)**"
    )