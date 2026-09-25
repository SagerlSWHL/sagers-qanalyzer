"""
trades.py
---------
Trades-Seite des Sagers qAnalyzer.

Zeigt alle Trades (Einzelstrategie oder Portfolio) mit Filtern:
  - Strategie (bei Portfolio)
  - Jahr
  - Ergebnis (Gewinner / Verlierer)
  - Richtung (Long / Short, falls vorhanden)

Plus CSV-Export.
"""

import pandas as pd
import streamlit as st

from core.state import get_strategies, get_trades


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def _collect_trades() -> pd.DataFrame:
    """
    Sammelt alle Trades aus Shared State.

    - Wenn Portfolio geladen: alle Strategien zusammen mit 'Strategie'-Spalte
    - Sonst wenn Einzelstrategie geladen: nur diese
    - Sonst: leeres DataFrame
    """

    strategies = get_strategies()

    if strategies:
        frames = []
        for name, df in strategies.items():
            if df is None or df.empty:
                continue
            copy = df.copy()
            copy["Strategie"] = name
            frames.append(copy)

        if frames:
            return pd.concat(frames, ignore_index=True)

    # Fallback: Einzelstrategie
    trades = get_trades()
    if trades is not None and not trades.empty:
        return trades.copy()

    return pd.DataFrame()


def _format_currency(value: float) -> str:
    return f"${value:,.2f}"


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_trades():
    """Zeigt die Trades-Seite."""

    st.title("Trades")
    st.write("Alle Trades im Detail – filterbar und exportierbar.")
    st.divider()

    df = _collect_trades()

    if df.empty:
        st.info(
            "⚠️ **Keine Trades geladen.** "
            "Lade im **Analyzer** eine Einzelstrategie "
            "oder im **Portfolio** mehrere Strategien."
        )
        return

    # -----------------------------------------------------
    # FILTER-BEREICH
    # -----------------------------------------------------

    st.subheader("Filter")

    col1, col2, col3, col4 = st.columns(4)

    # Strategie (nur wenn Portfolio)
    with col1:
        if "Strategie" in df.columns:
            strategy_options = ["Alle"] + sorted(df["Strategie"].unique().tolist())
            selected_strategy = st.selectbox("Strategie", strategy_options)
        else:
            selected_strategy = "Alle"
            st.write("")

    # Jahr
    with col2:
        if "Datum und Uhrzeit" in df.columns:
            df["_Jahr"] = pd.to_datetime(
                df["Datum und Uhrzeit"], errors="coerce"
            ).dt.year
            years = sorted(df["_Jahr"].dropna().unique().tolist())
            year_options = ["Alle"] + [str(int(y)) for y in years]
            selected_year = st.selectbox("Jahr", year_options)
        else:
            selected_year = "Alle"
            st.write("")

    # Ergebnis
    with col3:
        result_options = ["Alle", "Nur Gewinner", "Nur Verlierer"]
        selected_result = st.selectbox("Ergebnis", result_options)

    # Richtung (nur wenn Long/Short vorhanden)
    with col4:
        if "Typ" in df.columns:
            direction_options = ["Alle", "Long", "Short"]
            selected_dir = st.selectbox("Richtung", direction_options)
        else:
            selected_dir = "Alle"
            st.write("")

    # -----------------------------------------------------
    # FILTER ANWENDEN
    # -----------------------------------------------------

    filtered = df.copy()

    if selected_strategy != "Alle" and "Strategie" in filtered.columns:
        filtered = filtered[filtered["Strategie"] == selected_strategy]

    if selected_year != "Alle" and "_Jahr" in filtered.columns:
        filtered = filtered[filtered["_Jahr"] == int(selected_year)]

    if "Netto G&V USD" in filtered.columns:
        if selected_result == "Nur Gewinner":
            filtered = filtered[filtered["Netto G&V USD"] > 0]
        elif selected_result == "Nur Verlierer":
            filtered = filtered[filtered["Netto G&V USD"] < 0]

    if selected_dir != "Alle" and "Typ" in filtered.columns:
        filtered = filtered[
            filtered["Typ"].astype(str).str.contains(selected_dir, na=False)
        ]

    st.divider()

    # -----------------------------------------------------
    # KPI-KARTEN
    # -----------------------------------------------------

    st.subheader("Übersicht (gefiltert)")

    total = len(filtered)
    net = float(filtered["Netto G&V USD"].sum()) if total else 0.0
    winners = int((filtered["Netto G&V USD"] > 0).sum()) if total else 0
    win_rate = (winners / total * 100) if total else 0.0
    avg_pnl = (net / total) if total else 0.0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Trades", total)

    with col2:
        st.metric("Net Profit", _format_currency(net))

    with col3:
        st.metric("Win Rate", f"{win_rate:.2f} %")

    with col4:
        st.metric("Ø P&L / Trade", _format_currency(avg_pnl))

    st.divider()

    # -----------------------------------------------------
    # TABELLE
    # -----------------------------------------------------

    st.subheader("Trade-Liste")

    # Interne Spalte ausblenden
    display_df = filtered.drop(columns=["_Jahr"], errors="ignore")

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        height=500,
    )

    # -----------------------------------------------------
    # CSV-EXPORT
    # -----------------------------------------------------

    csv = display_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥  Als CSV herunterladen",
        data=csv,
        file_name="trades_export.csv",
        mime="text/csv",
        width="stretch",
    )

    st.caption(
        f"{total} Trades in der aktuellen Auswahl. "
        "Der Export enthält nur die gefilterten Daten."
    )