"""
correlation.py
--------------
Eigene Seite für Korrelations-Analysen.

Drei Modi:
  1. Return-Korrelation (Strategien – braucht geladene Strategien)
  2. Asset-Korrelation  (Strategien – braucht geladene Strategien)
  3. Symbol-Vergleich   (manuell – funktioniert standalone)
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.portfolio_engine import (
    asset_correlation_matrix,
    correlation_matrix,
    custom_asset_correlation,
    normalize_symbol,
)
from core.state import get_strategies


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_correlation():
    """
    Zeigt die Correlation-Seite mit drei Modi.
    """

    st.title("Correlation")
    st.write(
        "Analysiere Korrelationen zwischen Strategien oder "
        "zwischen beliebigen Markt-Symbolen."
    )
    st.divider()

    # -----------------------------------------------------
    # MODUS-WAHL
    # -----------------------------------------------------

    mode = st.radio(
        "Korrelations-Art:",
        options=[
            "📈 Return-Korrelation (Strategien)",
            "💹 Asset-Korrelation (Strategien)",
            "🌍 Symbol-Vergleich (manuell)",
        ],
        index=2,  # Symbol-Vergleich vorausgewählt (funktioniert immer)
        horizontal=True,
        key="corr_page_mode",
    )

    st.divider()

    # -----------------------------------------------------
    # WEITERLEITUNG
    # -----------------------------------------------------

    if mode.startswith("📈"):
        _show_return_correlation()
    elif mode.startswith("💹"):
        _show_asset_correlation()
    else:
        _show_custom_symbols_correlation()

    # -----------------------------------------------------
    # ERKLÄRUNG
    # -----------------------------------------------------

    st.divider()
    _show_explanation()


# =========================================================
# MODUS 1 – RETURN-KORRELATION
# =========================================================

def _show_return_correlation():
    """Return-Korrelation der geladenen Strategien."""

    st.subheader("Return-Korrelation")

    strategies = get_strategies()

    if not strategies:
        st.info(
            "⚠️ **Keine Strategien geladen.** "
            "Lade im **Portfolio**-Bereich Strategien hoch, "
            "um die Return-Korrelation zu sehen."
        )
        return

    st.write(
        "Wie ähnlich laufen die Strategien zueinander? "
        "Vergleicht die **Monatsänderung der Renditen**."
    )

    freq_labels = {
        "Täglich": "D",
        "Wöchentlich": "W",
        "Monatlich (empfohlen)": "ME",
    }

    selected_freq = st.radio(
        "Zeitbasis:",
        list(freq_labels.keys()),
        index=2,
        horizontal=True,
        key="return_freq_radio",
    )

    freq = freq_labels[selected_freq]

    corr = correlation_matrix(strategies, freq=freq)

    if corr.empty:
        st.info("Mindestens 2 Strategien nötig.")
        return

    _render_heatmap(corr)

    st.caption(f"Return-Korrelation auf {selected_freq.lower()}er Basis.")


# =========================================================
# MODUS 2 – ASSET-KORRELATION
# =========================================================

def _show_asset_correlation():
    """Asset-Korrelation der geladenen Strategien (via yfinance)."""

    st.subheader("Asset-Korrelation")

    strategies = get_strategies()

    if not strategies:
        st.info(
            "⚠️ **Keine Strategien geladen.** "
            "Lade im **Portfolio**-Bereich Strategien mit echten "
            "Ticker-Namen hoch (z. B. QQQ, SPY, TLT)."
        )
        return

    # Demo-Strategien erkennen
    real_tickers = any(
        not name.startswith("Synth ") for name in strategies.keys()
    )

    if not real_tickers:
        st.info(
            "ℹ️ **Asset-Korrelation nur mit echten Ticker-Namen möglich** "
            "(z. B. QQQ, SPY, TLT in den Dateinamen). "
            "Bei Demo-Strategien steht nur die Return-Korrelation zur Verfügung."
        )
        return

    st.write(
        "Wie ähnlich laufen die **Preise der gehandelten Assets**? "
        "Vergleicht die täglichen Kursänderungen."
    )

    with st.spinner("Lade Preisdaten von Yahoo Finance…"):
        corr = asset_correlation_matrix(strategies, period="2y")

    if corr.empty:
        st.warning(
            "Konnte keine Asset-Preise laden. "
            "Prüfe die Symbole in den Dateinamen und die Internetverbindung."
        )
        return

    _render_heatmap(corr)

    st.caption(
        "Asset-Korrelation basierend auf täglichen Kursänderungen "
        "(letzte 2 Jahre, Quelle: Yahoo Finance)."
    )


# =========================================================
# MODUS 3 – SYMBOL-VERGLEICH (manuell)
# =========================================================

def _show_custom_symbols_correlation():
    """Korrelation frei wählbarer Symbole (funktioniert ohne Strategien)."""

    st.subheader("Symbol-Vergleich")

    st.write(
        "Füge beliebige Symbole hinzu (Forex, Aktien, Indizes, Krypto). "
        "Zum Beispiel: **EURUSD**, **EURCHF**, **USDCHF**, **AAPL**, **BTC-USD**."
    )

    # State initialisieren
    if "custom_symbols" not in st.session_state:
        st.session_state["custom_symbols"] = ["EURUSD=X", "USDCHF=X"]

    # -----------------------------------------------------
    # SYMBOL HINZUFÜGEN
    # -----------------------------------------------------

    col_in, col_btn = st.columns([4, 1])

    with col_in:
        new_sym = st.text_input(
            "Symbol hinzufügen",
            placeholder="z. B. EURUSD, AAPL, BTC-USD",
            key="custom_symbol_input",
            label_visibility="collapsed",
        )

    with col_btn:
        if st.button("➕  Hinzufügen", width="stretch"):
            normalized = normalize_symbol(new_sym)
            if normalized and normalized not in st.session_state["custom_symbols"]:
                st.session_state["custom_symbols"].append(normalized)
                st.rerun()

    # -----------------------------------------------------
    # AKTUELLE SYMBOLE
    # -----------------------------------------------------

    current = st.session_state["custom_symbols"]

    if not current:
        st.info("Noch keine Symbole ausgewählt. Füge oben welche hinzu.")
        return

    st.caption(f"📌 Aktuelle Symbole ({len(current)}):")

    cols = st.columns(min(6, len(current)))
    to_remove = None

    for i, sym in enumerate(current):
        with cols[i % len(cols)]:
            label = sym.replace("=X", "")
            if st.button(f"❌ {label}", key=f"del_{sym}", width="stretch"):
                to_remove = sym

    if to_remove:
        st.session_state["custom_symbols"].remove(to_remove)
        st.rerun()

    # -----------------------------------------------------
    # PERIODE
    # -----------------------------------------------------

    period_label = st.radio(
        "Zeitraum:",
        options=["1 Jahr", "2 Jahre", "5 Jahre", "Max"],
        index=1,
        horizontal=True,
        key="custom_period_radio",
    )

    period_map = {"1 Jahr": "1y", "2 Jahre": "2y", "5 Jahre": "5y", "Max": "max"}
    period = period_map[period_label]

    # -----------------------------------------------------
    # BERECHNEN
    # -----------------------------------------------------

    if len(current) < 2:
        st.warning("Mindestens 2 Symbole hinzufügen, um zu vergleichen.")
        return

    with st.spinner("Lade Kursdaten von Yahoo Finance…"):
        corr = custom_asset_correlation(current, period=period)

    if corr.empty:
        st.error(
            "Konnte keine Daten laden. Prüfe die Symbole – evtl. "
            "existiert eines bei Yahoo Finance nicht."
        )
        return

    _render_heatmap(corr, strip_suffix=True)

    st.caption(
        f"Berechnet auf Tagesbasis, Zeitraum: {period_label}. "
        "Forex-Paare werden automatisch im Yahoo-Format geladen."
    )


# =========================================================
# HEATMAP-RENDERER
# =========================================================

def _render_heatmap(corr: pd.DataFrame, strip_suffix: bool = False):
    """Zeichnet die Heatmap einer Korrelations-Matrix."""

    display = corr.copy()

    if strip_suffix:
        display.index = [str(i).replace("=X", "") for i in display.index]
        display.columns = [str(c).replace("=X", "") for c in display.columns]

    text = display.map(lambda v: f"{v:.2f}")

    fig = go.Figure(
        data=go.Heatmap(
            z=display.values,
            x=display.columns,
            y=display.index,
            text=text.values,
            texttemplate="%{text}",
            textfont={"size": 11},
            colorscale=[
                [0.0, "#8B0000"],
                [0.5, "#1a1a1a"],
                [1.0, "#0F8B3C"],
            ],
            zmid=0,
            zmin=-1,
            zmax=1,
            showscale=True,
            colorbar=dict(title="ρ"),
        )
    )

    height = max(420, 30 * len(display) + 200)

    fig.update_layout(
        height=height,
        margin=dict(l=110, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig, width="stretch")


# =========================================================
# ERKLÄRUNG
# =========================================================

def _show_explanation():
    """Erklärt, was Korrelation aussagt – und was nicht."""

    with st.expander("ℹ️  Was die Korrelation aussagt – und was nicht"):
        st.markdown(
            """
**Was die Korrelation misst**

Sie zeigt, wie stark sich zwei Werte zeitlich im Gleichschritt bewegen.

| Wert | Bedeutung |
|------|-----------|
| **+1,0** | Perfekt im Gleichschritt |
| **+0,5** | Stark ähnlich |
| **0,0** | Unabhängig |
| **-0,5** | Gegenläufig |
| **-1,0** | Perfekt gegensätzlich |

**Die drei Modi**

- **Return-Korrelation** – Vergleich der Strategie-Renditen
- **Asset-Korrelation** – Vergleich der Marktpreise der gehandelten Assets
- **Symbol-Vergleich** – freie Auswahl beliebiger Symbole (Forex, Aktien, Krypto)

**Was sie NICHT aussagt**

- ❌ **Nichts über Rendite**
- ❌ **Nichts über Risiko**
- ❌ **Nichts über Kausalität**

**Praxis-Tipp**

Niedrige Korrelation (< 0,3) → gute Diversifikation.
Hohe Korrelation (> 0,7) → du hast effektiv **eine** Position mit mehrfachem Risiko.
            """
        )