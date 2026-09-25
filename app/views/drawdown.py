"""
drawdown.py
-----------
Drawdown-Seite des Sagers qAnalyzer.

Zeigt:
  - Drawdown-Verlauf (Chart)
  - Kennzahlen: Max DD, Ø DD, Aktuell, Anzahl Phasen
  - Dauer-Kennzahlen: Ø Dauer, längste Phase, längste Unterwasser
  - Vergleich Einzelstrategie ↔ Portfolio
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.metrics import (
    drawdown_duration_stats,
    drawdown_series,
    drawdown_stats,
)
from core.portfolio_engine import combine_equity
from core.state import get_strategies, get_trades


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_drawdown():
    """Zeigt die Drawdown-Seite."""

    st.title("Drawdown")
    st.write(
        "Analysiere die Drawdown-Phasen deiner Strategien – "
        "wie tief und wie lange sie unter Wasser waren."
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
            key="dd_mode_radio",
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
    # KENNZAHLEN BERECHNEN
    # -----------------------------------------------------

    stats = drawdown_stats(df)
    durations = drawdown_duration_stats(df)

    unit = "Tage" if mode.startswith("📊") else "Trades"

    # -----------------------------------------------------
    # KENNZAHLEN ZEILE 1 – TIEFE
    # -----------------------------------------------------

    st.subheader(f"Drawdown-Kennzahlen · {title}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Max Drawdown", f"{stats['max_drawdown']:.2f} %")

    with col2:
        st.metric("Ø Drawdown", f"{stats['avg_drawdown']:.2f} %")

    with col3:
        st.metric("Aktuell", f"{stats['current_drawdown']:.2f} %")

    with col4:
        st.metric("Anzahl Phasen", durations["n_phases"])

    # -----------------------------------------------------
    # KENNZAHLEN ZEILE 2 – DAUER
    # -----------------------------------------------------

    st.caption("**Dauer der Drawdown-Phasen**")

    col5, col6, col7 = st.columns(3)

    with col5:
        st.metric(
            "Ø Dauer (Peak → Trough)",
            f"{durations['avg_duration']:.0f} {unit}",
            help="Durchschnittliche Zeit vom Hochpunkt bis zum Tiefpunkt einer Verlustphase.",
        )

    with col6:
        st.metric(
            "Längste Phase (Peak → Trough)",
            f"{durations['max_duration']} {unit}",
            help="Die längste Zeit vom Hochpunkt bis zum Tiefpunkt.",
        )

    with col7:
        st.metric(
            "Längste Unterwasser (Peak → Recovery)",
            f"{stats['longest_underwater']} {unit}",
            help="Die längste Zeit vom Hochpunkt bis zum neuen Allzeit-Hoch.",
        )

    st.divider()

    # -----------------------------------------------------
    # CHART
    # -----------------------------------------------------

    st.subheader("Drawdown-Verlauf")

    dd = drawdown_series(df)

    if "Datum und Uhrzeit" in df.columns:
        x = pd.to_datetime(df["Datum und Uhrzeit"])
    else:
        x = list(range(len(dd)))

    fig = go.Figure()

    fig.add_hline(y=0, line_dash="dash", line_color="#666")

    fig.add_trace(
        go.Scatter(
            x=x,
            y=dd.values,
            mode="lines",
            name="Drawdown",
            line=dict(color="#EF4444", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.15)",
        )
    )

    trough_idx = dd.idxmin()
    x_trough = x.iloc[trough_idx] if hasattr(x, "iloc") else x[trough_idx]
    fig.add_trace(
        go.Scatter(
            x=[x_trough],
            y=[dd.min()],
            mode="markers",
            name="Max DD",
            marker=dict(color="#F59E0B", size=12, symbol="x"),
        )
    )

    fig.update_layout(
        height=420,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(title="Drawdown %", gridcolor="#333"),
        legend=dict(orientation="h", y=1.05, x=1, xanchor="right"),
    )

    st.plotly_chart(fig, width="stretch")

    # -----------------------------------------------------
    # ERKLÄRUNG
    # -----------------------------------------------------

    with st.expander("ℹ️  Was die Kennzahlen bedeuten"):
        st.markdown(
            """
**Max Drawdown** – Der tiefste Rückgang vom bisherigen Höchststand.
Zeigt das schlimmste Szenario der Strategie.

**Ø Drawdown** – Durchschnitt aller negativen Rückgänge.

**Aktuell** – Wie weit bist du gerade unter deinem Höchststand?
(0 % = neues Hoch, negativ = unter Wasser)

**Anzahl Phasen** – Wie oft es überhaupt zu einem Rückgang kam.

**Drei verschiedene Dauer-Kennzahlen:**

| Kennzahl | Was gemessen wird | Typisch |
|----------|-------------------|---------|
| **Ø Dauer (Peak → Trough)** | Zeit vom Hoch bis zum tiefsten Punkt | kurz (Wochen) |
| **Längste Phase (Peak → Trough)** | Längste Zeit bis zum tiefsten Punkt | mittel |
| **Längste Unterwasser (Peak → Recovery)** | Zeit bis zum neuen Allzeit-Hoch | lang (Monate/Jahre) |

**Warum der Unterschied wichtig ist:**

Eine Strategie kann schnell am Tiefpunkt sein (z. B. 50 Tage),
aber lange brauchen, um wieder aufs alte Hoch zu kommen (z. B. 500 Tage).
Beide Zahlen sind nützlich – sie messen unterschiedliche Dinge.
            """
        )