"""
news.py
-------
News-Seite des Sagers qAnalyzer.

Wirtschaftskalender mit Zeitzonen- und Zeitraum-Auswahl.
"""

from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from core.news_calendar import load_calendar


# =========================================================
# ZEITZONEN
# =========================================================

TIMEZONES = {
    "UTC": "UTC",
    "🇩🇪  Berlin (CET)": "Europe/Berlin",
    "🇬🇧  London (GMT)": "Europe/London",
    "🇺🇸  New York (EST)": "America/New_York",
    "🇯🇵  Tokyo (JST)": "Asia/Tokyo",
    "🇦🇺  Sydney (AEST)": "Australia/Sydney",
}


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_news():
    """Zeigt die News-Seite."""

    st.title("News")
    st.write("Wirtschaftskalender – wichtige Termine und Zahlen.")
    st.divider()

    # -----------------------------------------------------
    # FILTER-ZEILE 1 – Impact + Region
    # -----------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        impact = st.selectbox(
            "Impact",
            options=["high", "medium"],
            format_func=lambda x: {"high": "🔴 High", "medium": "🟡 Medium"}[x],
        )

    with col2:
        region = st.selectbox(
            "Region",
            options=[
                "US,EU,GB,DE,JP,CH,CA,AU,NZ",
                "US",
                "EU,GB,DE,CH",
                "JP,AU,NZ,CA",
            ],
            format_func=lambda x: {
                "US,EU,GB,DE,JP,CH,CA,AU,NZ": "🌍 Alle",
                "US": "🇺🇸 USA",
                "EU,GB,DE,CH": "🇪🇺 Europa",
                "JP,AU,NZ,CA": "🌏 Asien & andere",
            }[x],
        )

        col_a, col_b = st.columns(2)

    with col_a:
        only_indicators = st.toggle(
            "📊  Nur Daten-Releases",
            value=True,
            help="Blendet Reden und Termine aus – nur echte Wirtschaftsdaten.",
        )

    with col_b:
        only_top = st.toggle(
            "🎯  Nur Top-Events (FF-Niveau)",
            value=True,
            help="Zeigt nur die wichtigsten Events: Zinsen, NFP, CPI, GDP, PMI …",
        )

    # -----------------------------------------------------
    # FILTER-ZEILE 2 – Zeitzone + Zeitraum
    # -----------------------------------------------------

    col3, col4 = st.columns(2)

    with col3:
        tz_label = st.selectbox(
            "Zeitzone",
            options=list(TIMEZONES.keys()),
            index=1,  # Berlin vorausgewählt
        )
        tz_name = TIMEZONES[tz_label]

    with col4:
        timeframe = st.selectbox(
            "Zeitraum",
            options=[
                "Heute",
                "Heute + Morgen",
                "Nächste 3 Tage",
                "Nächste 7 Tage",
                "Alle (Standard-Feed)",
            ],
            index=3,  # 7 Tage vorausgewählt
        )

    # -----------------------------------------------------
    # DATEN LADEN
    # -----------------------------------------------------

    with st.spinner("Lade Kalender…"):
        try:
            df = load_calendar(
                importance=impact,
                countries=region,
                only_top=only_top,
            )
        except Exception as exc:
            st.error(f"Fehler beim Laden: {exc}")
            return

    if df.empty:
        st.info("Keine Events gefunden.")
        return

    # -----------------------------------------------------
    # NUR DATEN-RELEASES
    # -----------------------------------------------------

    if only_indicators and "_type" in df.columns:
        df = df[df["_type"] == "indicator"].reset_index(drop=True)

        if df.empty:
            st.info(
                "Keine Daten-Releases gefunden. "
                "Schalte den Filter unten aus, um Reden und Termine zu sehen."
            )
            return

    # -----------------------------------------------------
    # ZEITZONE ANWENDEN
    # -----------------------------------------------------

    tz = ZoneInfo(tz_name)

    # _dt_utc ist tz-aware UTC → in gewünschte Zone konvertieren
    df["_dt_local"] = df["_dt_utc"].dt.tz_convert(tz)

    df["Datum"] = df["_dt_local"].dt.strftime("%d.%m.%Y")
    df["Zeit"] = df["_dt_local"].dt.strftime("%H:%M")

    # -----------------------------------------------------
    # ZEITRAUM FILTERN
    # -----------------------------------------------------

    heute = pd.Timestamp.now(tz=tz).normalize()

    if timeframe == "Heute":
        cutoff = heute + pd.Timedelta(days=1)
    elif timeframe == "Heute + Morgen":
        cutoff = heute + pd.Timedelta(days=2)
    elif timeframe == "Nächste 3 Tage":
        cutoff = heute + pd.Timedelta(days=3)
    elif timeframe == "Nächste 7 Tage":
        cutoff = heute + pd.Timedelta(days=7)
    else:
        cutoff = None

    if cutoff is not None:
        df = df[
            (df["_dt_local"] >= heute)
            & (df["_dt_local"] < cutoff)
        ].reset_index(drop=True)

    if df.empty:
        st.info(
            "Keine Events im gewählten Zeitraum. "
            "Erweitere den Zeitraum oder ändere die Filter."
        )
        return

    # -----------------------------------------------------
    # KPI-ZEILE
    # -----------------------------------------------------

    total = len(df)
    heute_str = heute.strftime("%d.%m.%Y")
    heute_count = int((df["Datum"] == heute_str).sum())

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Events", total)
    with col2:
        st.metric("Heute", heute_count)
    with col3:
        st.metric("Zeitraum", f"{df['Datum'].iloc[0]} – {df['Datum'].iloc[-1]}")

    st.divider()

    # -----------------------------------------------------
    # TABELLE (gruppiert nach Tag)
    # -----------------------------------------------------

    st.subheader("Kalender")

    for datum, group in df.groupby("Datum", sort=False):
        st.markdown(f"### 📅  {datum}")

        display = group[["Zeit", "Währung", "Impact", "Event",
                         "Actual", "Forecast", "Previous"]].copy()
        display = display.rename(columns={"Zeit": f"Zeit ({tz_label.split()[0]})"})

        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    # -----------------------------------------------------
    # HINWEIS
    # -----------------------------------------------------

    st.caption(
        f"Daten: MetaTrader-5-Kalender (biquote). "
        f"Alle Zeiten in **{tz_label}**."
    )