"""
portfolio.py
------------
Portfolio-Seite des Sagers qAnalyzer.

Erlaubt das Hochladen mehrerer Strategie-Dateien ODER das Erzeugen
synthetischer Demo-Strategien (1 bis 100).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.analyzer_engine import analyze_trades
from core.data_loader import load_trades, load_trading_data
from core.portfolio_engine import (
    asset_correlation_matrix,
    build_equity_matrix,
    combine_equity,
    combine_equity_weighted,
    correlation_matrix,
    custom_asset_correlation,
    normalize_symbol,
)
from core.synthetic_data import generate_synthetic_strategies
from core.state import get_strategies, set_strategies

# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def _is_quantitativo_excel(uploaded_file) -> bool:
    """
    Prüft, ob eine Excel-Datei ein Quantitativo-Export ist.
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
    return filename.rsplit(".", 1)[0]

def _reset_portfolio_selection(all_names):
    """
    Callback für den 'Alle zeigen'-Button.
    Wird von Streamlit VOR dem Neu-Rendern ausgeführt – erlaubt das
    sichere Setzen von session_state vor dem Multiselect-Widget.
    """
    st.session_state["portfolio_selected"] = list(all_names)

def _select_all_strategies(names):
    """
    Callback: wählt alle Strategien aus – setzt sowohl die Auswahl-Liste
    als auch alle Checkbox-States.
    """
    st.session_state["portfolio_selected"] = list(names)
    for n in names:
        st.session_state[f"chk_{n}"] = True


def _deselect_all_strategies(names):
    """
    Callback: wählt alle Strategien ab.
    """
    st.session_state["portfolio_selected"] = []
    for n in names:
        st.session_state[f"chk_{n}"] = False


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
    # QUELLEN-AUSWAHL
    # -----------------------------------------------------

    st.subheader("Import Strategies")

    col_upload, col_demo = st.columns([3, 2])

    with col_upload:
        uploaded_files = st.file_uploader(
            "Excel- oder CSV-Dateien auswählen (mehrere möglich)",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
        )

    with col_demo:
        st.write("")
        st.caption("Keine eigenen Dateien? Demo-Strategien erzeugen:")

        n_demo = st.selectbox(
            "Anzahl Strategien",
            options=[1, 5, 10, 20, 50, 100],
            index=2,  # Default: 10
        )

        if st.button("🎲  Demo-Strategien laden", width="stretch"):
            st.session_state["use_synthetic_portfolio"] = True
            st.session_state["n_synthetic"] = n_demo

    # -----------------------------------------------------
    # STRATEGIEN ZUSAMMENSTELLEN
    # -----------------------------------------------------

    strategies = {}

    # Priorität 1: Frische Uploads
    if uploaded_files:
        st.session_state["use_synthetic_portfolio"] = False

        for file in uploaded_files:
            try:
                trades = _load_uploaded(file)
                if trades is not None and not trades.empty:
                    strategies[_strategy_name(file.name)] = trades
            except Exception as exc:
                st.warning(f"Konnte '{file.name}' nicht laden: {exc}")

        if strategies:
            set_strategies(strategies)

    # Priorität 2: Demo-Strategien frisch laden
    elif st.session_state.get("use_synthetic_portfolio"):
        n = st.session_state.get("n_synthetic", 10)
        strategies = generate_synthetic_strategies(n)
        st.info(
            f"🎲 {n} synthetische Demo-Strategien geladen "
            "(keine echten Daten)."
        )
        set_strategies(strategies)

    # Priorität 3: Aus Shared State (beim Zurückkommen auf die Seite)
    else:
        strategies = get_strategies()
        if strategies:
            st.success(
                f"✅ {len(strategies)} Strategie(n) aus vorheriger Sitzung geladen. "
                "Lade neue Dateien hoch, um sie zu ersetzen."
            )

    if not strategies:
        st.info("Noch keine Strategien geladen.")
        return

    # -----------------------------------------------------
    # STRATEGIE-FILTER
    # -----------------------------------------------------

    all_names = list(strategies.keys())

    # Auto-Select: alle vorauswählen, wenn neue Strategien geladen wurden
    state_key = "portfolio_loaded_set"
    current_set = tuple(all_names)

    if st.session_state.get(state_key) != current_set:
        st.session_state["portfolio_selected"] = all_names
        st.session_state[state_key] = current_set
        # Checkbox-States initialisieren
        for n in all_names:
            st.session_state[f"chk_{n}"] = True

        st.subheader("Strategie-Auswahl")

    # Sortiert nach Net Profit (für spätere Verwendung)
    profit_sorted = sorted(
        all_names,
        key=lambda n: -float(strategies[n]["Netto G&V USD"].sum()),
    )

    # -----------------------------------------------------
    # MANUELLE AUSWAHL (aufklappbar)
    # -----------------------------------------------------

    with st.expander("🔧 Strategien auswählen", expanded=True):

        col_sel_all, col_sel_none = st.columns(2)

        with col_sel_all:
            st.button(
                "Alles anwählen",
                width="stretch",
                on_click=_select_all_strategies,
                args=(all_names,),
            )

        with col_sel_none:
            st.button(
                "Alles abwählen",
                width="stretch",
                on_click=_deselect_all_strategies,
                args=(all_names,),
            )

        # Checkboxen in 4 Spalten
        n_cols = 4
        cols = st.columns(n_cols)
        selection = list(st.session_state.get("portfolio_selected", []))

        for i, name in enumerate(profit_sorted):
            with cols[i % n_cols]:
                new_val = st.checkbox(
                    name,
                    key=f"chk_{name}",
                )

                if new_val and name not in selection:
                    selection.append(name)
                elif not new_val and name in selection:
                    selection.remove(name)

        st.session_state["portfolio_selected"] = selection

    selection = st.session_state.get("portfolio_selected", [])

    if not selection:
        st.warning("Mindestens eine Strategie muss sichtbar sein.")
        st.stop()

    # Filter anwenden
    strategies = {k: v for k, v in strategies.items() if k in selection}

    st.success(
        f"{len(strategies)} von {len(all_names)} Strategie(n) sichtbar: "
        + ", ".join(list(strategies.keys())[:5])
        + ("…" if len(strategies) > 5 else "")
    )


    # In Shared State speichern (für Correlation-Seite)
    set_strategies(strategies)

    # -----------------------------------------------------
    # PORTFOLIO-KENNZAHLEN
    # -----------------------------------------------------

    combined = combine_equity(strategies)

    total_net = sum(
        float(df["Netto G&V USD"].sum())
        for df in strategies.values()
        if "Netto G&V USD" in df.columns
    )

    total_trades = sum(len(df) for df in strategies.values())

    if not combined.empty:
        portfolio_return = float(combined.iloc[-1])
    else:
        portfolio_return = 0.0

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
            "Net Profit": round(result["net_profit"], 2),
            "Win Rate %": round(result["win_rate"], 2),
            "Profit Factor": round(result["profit_factor"], 3),
            "Max DD %": round(result["max_drawdown"], 2),
            "Expectancy": round(result["expectancy"], 2),
        })

    comparison = pd.DataFrame(rows)
    comparison = comparison.sort_values("Net Profit", ascending=False)

    st.dataframe(comparison, width="stretch", hide_index=True)

    st.divider()

    # -----------------------------------------------------
    # ANSICHT-WECHSEL (Dropdown statt Tabs)
    # -----------------------------------------------------

    view = st.radio(
        "Ansicht",
        options=[
            "📊 Portfolio (kombiniert)",
            "📈 Einzelne Strategien",
            "⚖️ Gewichtung",
            "📉 Rollierende Performance",
        ],
        index=0,
        horizontal=True,
        key="portfolio_view_selector",
        label_visibility="collapsed",
    )

    st.divider()

    if view == "📊 Portfolio (kombiniert)":
        _show_combined_equity(combined)

    elif view == "📈 Einzelne Strategien":
        _show_individual_equity(strategies)

    elif view == "⚖️ Gewichtung":
        _show_weighted_equity(strategies)

    elif view == "📉 Rollierende Performance":
        _show_rolling_performance(strategies)


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

    st.plotly_chart(fig, width="stretch")


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
            y=-0.4,
            xanchor="center",
            x=0.5,
            font=dict(size=9),
        ),
    )

    st.plotly_chart(fig, width="stretch")


# =========================================================
# KORRELATIONS-HEATMAP
# =========================================================

def _show_correlation(strategies: dict):
    """
    Zeigt zwei Arten von Korrelation:
      - Return-Korrelation (basierend auf monatlichen Renditen)
      - Asset-Korrelation (basierend auf Preisen der gehandelten Assets)
    """

    st.subheader("Correlation Matrix")

    # -----------------------------------------------------
    # MODUS-WAHL
    # -----------------------------------------------------

    # Prüfen, ob echte Ticker vorhanden sind
    # (Demo-Strategien fangen mit "Synth " an → kein Asset-Modus)
    real_tickers = any(
        not name.startswith("Synth ") for name in strategies.keys()
    )

    mode = st.radio(
        "Korrelations-Art:",
        options=[
            "📈 Return-Korrelation (Strategien)",
            "💹 Asset-Korrelation (Strategien)",
            "🌍 Symbol-Vergleich (manuell)",
        ],
        index=0,
        horizontal=True,
        key="corr_mode_radio",
    )

    is_asset = mode.startswith("💹")
    is_custom = mode.startswith("🌍")

    # -----------------------------------------------------
    # SYMBOL-VERGLEICH (manuelle Auswahl)
    # -----------------------------------------------------

    if is_custom:
        _show_custom_symbols_correlation()
        return

    # -----------------------------------------------------
    # RETURN-KORRELATION
    # -----------------------------------------------------

    if not is_asset:

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
            key="corr_freq_radio",
        )

        freq = freq_labels[selected_freq]

        corr = correlation_matrix(strategies, freq=freq)
        title = "Return"

        if corr.empty:
            st.info("Mindestens 2 Strategien nötig.")
            return

    # -----------------------------------------------------
    # ASSET-KORRELATION
    # -----------------------------------------------------

    else:

        st.write(
            "Wie ähnlich laufen die **Preise der gehandelten Assets**? "
            "Vergleicht die täglichen Kursänderungen."
        )

        with st.spinner("Lade Preisdaten von Yahoo Finance…"):
            corr = asset_correlation_matrix(strategies, period="2y")

        title = "Asset"

        if corr.empty:
            st.warning(
                "Konnte keine Asset-Preise laden. "
                "Prüfe, ob die Symbole in den Dateinamen erkennbar sind "
                "(z. B. QQQ, SPY, TLT) und ob Internet verfügbar ist."
            )
            return

    # -----------------------------------------------------
    # HEATMAP ZEICHNEN
    # -----------------------------------------------------

    text = corr.map(lambda v: f"{v:.2f}")

    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.index,
            text=text.values,
            texttemplate="%{text}",
            textfont={"size": 10},
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

    fig.update_layout(
        height=600,
        margin=dict(l=120, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig, use_container_width=True)

    if not is_asset:
        st.caption(
            f"Return-Korrelation auf {selected_freq.lower()}er Basis."
        )
    else:
        st.caption(
            "Asset-Korrelation basierend auf täglichen Kursänderungen "
            "(letzte 2 Jahre, Quelle: Yahoo Finance)."
        )

    # -----------------------------------------------------
    # ERKLÄRUNG
    # -----------------------------------------------------

    with st.expander("ℹ️  Was die Korrelation aussagt – und was nicht"):
        st.markdown(
            """
**Return-Korrelation** (Strategien)

Vergleicht: Wie stark bewegen sich die **Renditen** zweier
Strategien zeitlich im Gleichschritt?

- **+1,0** = perfekt gleichläufig
- **0,0** = unabhängig
- **-1,0** = gegensätzlich

**Asset-Korrelation** (Märkte)

Vergleicht: Wie stark bewegen sich die **Preise** der gehandelten
Assets (z. B. QQQ vs. TLT) im Gleichschritt?

Zeigt, ob zwei Strategien auf **grundsätzlich verschiedenen Märkten**
agieren – auch wenn sie unterschiedliche Regeln haben.

**Was die Korrelation NICHT aussagt**

- ❌ **Nichts über Rendite** – eine Strategie kann +200 % machen und trotzdem unkorreliert sein
- ❌ **Nichts über Risiko** – Korrelation und Volatilität sind verschieden
- ❌ **Nichts über Kausalität** – nur weil zwei Strategien gleich laufen, beeinflusst die eine nicht die andere

**Praxis-Tipp**

Niedrige Korrelation (< 0,3) → gute Diversifikation.
Hohe Korrelation (> 0,7) → du hast effektiv **eine** Strategie mit mehrfachem Risiko.
            """
        )


# =========================================================
# GEWICHTETE EQUITY
# =========================================================

def _show_weighted_equity(strategies: dict):
    """
    Erlaubt das Einstellen der Gewichte pro Strategie.
    """

    st.subheader("Portfolio Weights")

    st.write("Passe die Gewichtung der Strategien an.")

    names = list(strategies.keys())
    n = len(names)

    default_w = round(100.0 / n, 2)

    weights_pct = {}

    # Bei vielen Strategien: nur die ersten 20 als Slider
    max_sliders = 20
    shown = names[:max_sliders]

    if n > max_sliders:
        st.caption(
            f"Nur die ersten {max_sliders} Strategien sind einstellbar. "
            "Die übrigen werden gleichmäßig verteilt."
        )

    for name in shown:
        weights_pct[name] = st.slider(
            name,
            min_value=0,
            max_value=100,
            value=int(default_w),
            step=5,
            key=f"weight_{name}",
        )

    # Restliche Strategien: gleichmäßig
    remaining = names[max_sliders:]
    for name in remaining:
        weights_pct[name] = default_w

    total = sum(weights_pct.values())

    if total == 0:
        st.warning("Bitte mindestens eine Strategie mit Gewicht > 0.")
        return

    weights = {k: v / total for k, v in weights_pct.items()}

    st.caption(f"Summe: {total:.0f}% → normalisiert auf 100%")

    combined = combine_equity_weighted(strategies, weights)

    if combined.empty:
        st.info("Keine Daten verfügbar.")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=combined.index,
            y=combined.values,
            mode="lines",
            name="Gewichtetes Portfolio",
            line=dict(color="#F59E0B", width=2),
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

    st.plotly_chart(fig, width="stretch")

    col1, col2, col3 = st.columns(3)

    final_return = float(combined.iloc[-1])
    dd = float((combined - combined.cummax()).min())

    with col1:
        st.metric("Return", f"{final_return:.2f} %")
    with col2:
        st.metric("Max Drawdown", f"{dd:.2f} %")
    with col3:
        ratio = abs(final_return / dd) if dd != 0 else 0
        st.metric("Return/DD", f"{ratio:.2f}")


# =========================================================
# ROLLIERENDE PERFORMANCE
# =========================================================

def _show_rolling_performance(strategies: dict):
    """
    Rollierende 3-Monats-Performance der kombinierten Equity.
    """

    st.subheader("Rolling Performance (3 Monate)")

    st.write(
        "Wie entwickelt sich die Portfolio-Rendite über die Zeit? "
        "Hilft, um Stabilität einzuschätzen."
    )

    combined = combine_equity(strategies)

    if combined.empty:
        st.info("Keine Daten verfügbar.")
        return

    combined = combined.copy()
    combined.index = pd.to_datetime(combined.index)

    rolling = combined.diff(periods=90)

    fig = go.Figure()

    fig.add_hline(y=0, line_dash="dash", line_color="#666")

    fig.add_trace(
        go.Scatter(
            x=rolling.index,
            y=rolling.values,
            mode="lines",
            name="3-Monats-Rendite",
            line=dict(color="#A78BFA", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(167, 139, 250, 0.15)",
        )
    )

    fig.update_layout(
        height=420,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(title="Rendite (3 Mon.) %", gridcolor="#333"),
    )

    st.plotly_chart(fig, width="stretch")



# =========================================================
# SYMBOL-VERGLEICH (manuell)
# =========================================================

def _show_custom_symbols_correlation():
    """
    Erlaubt dem Nutzer, beliebige Symbole hinzuzufügen und
    deren Korrelation zu sehen.
    """

    st.write(
        "Füge beliebige Symbole hinzu (Forex, Aktien, Indizes, Krypto). "
        "Zum Beispiel: **EURUSD**, **EURCHF**, **USDCHF**, **AAPL**, **BTC-USD**."
    )

    # -----------------------------------------------------
    # STATE
    # -----------------------------------------------------

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
        if st.button("➕  Hinzufügen", use_container_width=True):
            normalized = normalize_symbol(new_sym)
            if normalized and normalized not in st.session_state["custom_symbols"]:
                st.session_state["custom_symbols"].append(normalized)
                st.rerun()

    # -----------------------------------------------------
    # AKTUELLE SYMBOLE ANZEIGEN
    # -----------------------------------------------------

    current = st.session_state["custom_symbols"]

    if not current:
        st.info("Noch keine Symbole ausgewählt. Füge oben welche hinzu.")
        return

    st.caption(f"📌 Aktuelle Symbole ({len(current)}):")

    # Symbole als Chips mit Löschen-Button
    cols = st.columns(min(6, len(current)))
    to_remove = None

    for i, sym in enumerate(current):
        with cols[i % len(cols)]:
            label = sym.replace("=X", "")
            if st.button(f"❌ {label}", key=f"del_{sym}", use_container_width=True):
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
    # KORRELATION BERECHNEN
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

    # -----------------------------------------------------
    # HEATMAP
    # -----------------------------------------------------

    # Für die Anzeige die =X-Suffixe ausblenden
    display = corr.copy()
    display.index = [i.replace("=X", "") for i in display.index]
    display.columns = [c.replace("=X", "") for c in display.columns]

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

    fig.update_layout(
        height=max(400, 30 * len(display) + 200),
        margin=dict(l=100, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Berechnet auf Tagesbasis, Zeitraum: {period_label}. "
        "Forex-Paare werden automatisch im Yahoo-Format geladen."
    )