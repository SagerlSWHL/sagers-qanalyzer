"""
ml_analysis.py
--------------
Machine Learning Analyse-Seite.

Trainiert ein Random-Forest-Modell auf Backtest-Trades und zeigt:
  - Modell-Qualität (AUC, Accuracy)
  - Feature Importance
  - Clustering
  - Filter-Vorschläge
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.backtest_engine import run_backtest
from core.feature_engineering import (
    FEATURE_COLUMNS,
    enrich_trades_with_features,
)
from core.market_data import POPULAR_SYMBOLS, load_ohlc
from core.ml_engine import (
    cluster_trades,
    permutation_test,
    suggest_filters,
    train_random_forest,
)
from core.strategies import STRATEGIES


# =========================================================
# KPI-KARTEN
# =========================================================

def _render_metrics(metrics: dict):
    """Zeigt Modell-Metriken mit Farb-Bewertung."""

    auc = metrics.get("auc", 0)
    acc = metrics.get("accuracy", 0)
    baseline = metrics.get("baseline_win_rate", 0)
    n_train = metrics.get("n_train", 0)
    n_test = metrics.get("n_test", 0)

    # Bewertung der AUC
    if auc < 0.55:
        auc_status = "schwach"
        auc_color = "#EF4444"
    elif auc < 0.60:
        auc_status = "grenzwertig"
        auc_color = "#F59E0B"
    else:
        auc_status = "brauchbar"
        auc_color = "#22C55E"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "AUC",
            f"{auc:.3f}",
            help="0,5 = Zufall · 1,0 = perfekt",
        )
        st.markdown(
            f"<div style='color:{auc_color}; font-size:12px; margin-top:-14px;'>"
            f"→ {auc_status}</div>",
            unsafe_allow_html=True,
        )

    with col2:
        st.metric("Accuracy", f"{acc:.1%}")

    with col3:
        st.metric("Baseline Win Rate", f"{baseline:.1%}")

    with col4:
        st.metric("Train / Test", f"{n_train} / {n_test}")

    # Ehrlicher Hinweis bei schwacher AUC
    if auc < 0.55:
        st.info(
            "ℹ️ **Das Modell findet kein Muster in dieser Strategie.** "
            "Das bedeutet: Weder RSI, noch VIX, noch Wochentag helfen dabei, "
            "Gewinner von Verlierern zu unterscheiden. "
            "Das ist bei sehr einfachen Strategien wie IBS normal – "
            "die Regel ist schon so schlank, dass kein versteckter Filter existiert."
        )


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

def _render_feature_importance(importance: pd.DataFrame):
    """Zeigt Feature-Wichtigkeit als horizontales Balken-Diagramm."""

    st.subheader("Feature Importance")

    if importance.empty:
        st.info("Keine Daten.")
        return

    # Top 15
    top = importance.head(15).copy()
    top = top.sort_values("importance", ascending=True)

    fig = go.Figure(go.Bar(
        x=top["importance"],
        y=top["feature"],
        orientation="h",
        marker=dict(
            color=top["importance"],
            colorscale=[[0, "#1e3a5f"], [1, "#60A5FA"]],
            showscale=False,
        ),
        hovertemplate="%{y}<br>Wichtigkeit: %{x:.4f}<extra></extra>",
    ))

    fig.update_layout(
        height=max(300, 25 * len(top)),
        margin=dict(l=140, r=20, t=10, b=20),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6", size=11),
        xaxis=dict(
            title="Relativer Beitrag",
            gridcolor="#333",
        ),
        yaxis=dict(gridcolor="#333"),
    )

    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Zeigt, welche Features das Modell am stärksten nutzt. "
        "**Achtung:** Hohe Wichtigkeit bedeutet nicht automatisch ein echtes "
        "Signal – bei 21 Features ist die niedrige Importance "
        "(alle ~0,05) selbst ein Hinweis auf fehlende Struktur."
    )


# =========================================================
# CLUSTERING
# =========================================================

def _render_clustering(summary: pd.DataFrame):
    """Zeigt Cluster-Zusammenfassung als Tabelle + Chart."""

    st.subheader("Trade-Cluster")

    if summary.empty:
        st.info("Keine Cluster.")
        return

    # Farbige Tabelle
    display = summary.copy()
    display.columns = [
        "Cluster",
        "Trades",
        "Win Rate %",
        "Ø Rendite %",
        "Summe %",
        "Ø Haltedauer",
    ]

    st.dataframe(display, width="stretch", hide_index=True)

    # Bar-Chart: Win Rate pro Cluster
    fig = go.Figure(go.Bar(
        x=[f"Cluster {int(c)}" for c in summary["cluster"]],
        y=summary["win_rate"],
        marker=dict(
            color=summary["win_rate"],
            colorscale=[[0, "#EF4444"], [1, "#22C55E"]],
            showscale=False,
        ),
        text=[f"{v:.1f} %" for v in summary["win_rate"]],
        textposition="outside",
        hovertemplate="Cluster %{x}<br>Win Rate: %{y:.1f} %<extra></extra>",
    ))

    fig.update_layout(
        height=280,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        yaxis=dict(
            title="Win Rate %",
            gridcolor="#333",
            range=[0, 100],
        ),
        xaxis=dict(gridcolor="#333"),
        showlegend=False,
    )

    st.plotly_chart(fig, width="stretch")


# =========================================================
# FILTER-VORSCHLÄGE
# =========================================================

def _render_filters(filters: pd.DataFrame):
    """Zeigt Filter-Vorschläge mit Warnung."""

    st.subheader("Filter-Vorschläge")

    if filters.empty:
        st.info("Keine Filter gefunden, die die Win Rate signifikant verbessern.")
        return

    st.warning(
        "⚠️ **Vorsicht vor Overfitting.** Diese Filter wurden aus **denselben Daten** "
        "abgeleitet, auf denen sie getestet wurden. Sie wirken in der Historie – "
        "aber **nicht unbedingt in der Zukunft**. "
        "Für einen sauberen Test: Filter in neuen Backtests validieren."
    )

    display = filters.copy()
    display.columns = [
        "Feature",
        "Richtung",
        "Schwelle",
        "Betroffene Trades",
        "Behalten",
        "WR vorher %",
        "WR nachher %",
        "Verbesserung %",
    ]

    st.dataframe(display, width="stretch", hide_index=True)

    # Beispiel-Interpretation für den Top-Filter
    top = filters.iloc[0]
    direction_word = "unter" if top["direction"] == "below" else "über"

    st.markdown(
        f"""
        **Top-Vorschlag interpretiert:**

        > Ignoriere alle Trades mit `{top['feature']}` **{direction_word}** `{top['threshold']}`.
        > Damit würden **{int(top['n_affected'])}** Trades wegfallen.
        > Win Rate: **{top['win_rate_before']:.1f} %** → **{top['win_rate_after']:.1f} %**.
        """
    )


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_ml_analysis():
    """Zeigt die ML-Analyse-Seite."""

    st.title("ML-Analyse")
    st.write(
        "Findet Muster in Trades mit Machine Learning – "
        "und zeigt ehrlich, ob sie echt oder Zufall sind."
    )
    st.divider()

    # -----------------------------------------------------
    # KONFIGURATION
    # -----------------------------------------------------

    st.subheader("Konfiguration")

    col1, col2 = st.columns(2)

    with col1:
        category_map = {}
        for name, spec in STRATEGIES.items():
            cat = spec.get("category", "Sonstige")
            category_map.setdefault(cat, []).append(name)

        category = st.selectbox(
            "Kategorie",
            options=list(category_map.keys()),
        )

        strategy_name = st.selectbox(
            "Strategie",
            options=category_map[category],
        )

        strategy_spec = STRATEGIES[strategy_name]

    with col2:
        all_symbols = []
        symbol_labels = []
        for group, items in POPULAR_SYMBOLS.items():
            for sym, label in items:
                all_symbols.append(sym)
                symbol_labels.append(f"{sym} — {label}")

        default_sym = strategy_spec.get("default_symbol", "QQQ")
        default_idx = all_symbols.index(default_sym) if default_sym in all_symbols else 0

        symbol_idx = st.selectbox(
            "Symbol",
            options=range(len(all_symbols)),
            format_func=lambda i: symbol_labels[i],
            index=default_idx,
        )
        symbol = all_symbols[symbol_idx]

        start_date = st.date_input(
            "Startdatum",
            value=pd.Timestamp("2000-01-01").date(),
        )

    n_clusters = st.slider(
        "Anzahl Cluster",
        min_value=2,
        max_value=6,
        value=3,
        help="Wie viele Trade-Muster soll das Modell erkennen?",
    )

    # -----------------------------------------------------
    # TRAINING
    # -----------------------------------------------------

    if st.button("🤖  Modell trainieren", type="primary", width="stretch"):

        # Daten laden
        with st.spinner(f"Lade Daten für {symbol}…"):
            try:
                df = load_ohlc(symbol, start=str(start_date))
            except Exception as exc:
                st.error(f"Fehler beim Laden: {exc}")
                return

        if df.empty:
            st.error("Keine Daten.")
            return

        # Backtest
        with st.spinner("Backtest läuft…"):
            target = strategy_spec["fn"](df)
            result = run_backtest(df, target)

        if result.trades.empty:
            st.warning("Keine Trades im Backtest.")
            return

        # Features
        with st.spinner("Berechne Features…"):
            enriched = enrich_trades_with_features(result.trades, df)

        if enriched.empty:
            st.error("Features konnten nicht berechnet werden.")
            return

        # ML Training
        with st.spinner("Trainiere Modell…"):
            ml_result = train_random_forest(enriched, FEATURE_COLUMNS)

        if "error" in ml_result:
            st.error(ml_result["error"])
            return

        # Clustering
        with st.spinner("Clustere Trades…"):
            cluster_result = cluster_trades(
                enriched, FEATURE_COLUMNS, n_clusters=n_clusters
            )

        # Filter
        with st.spinner("Suche Filter…"):
            filters = suggest_filters(enriched, FEATURE_COLUMNS)

        # Permutations-Test
        with st.spinner("Permutations-Test läuft (~30-60 Sek)…"):
            perm_result = permutation_test(
                enriched, FEATURE_COLUMNS, n_permutations=50
            )

        # In Session speichern
        st.session_state["ml_result"] = ml_result
        st.session_state["ml_cluster"] = cluster_result
        st.session_state["ml_filters"] = filters
        st.session_state["ml_perm"] = perm_result
        st.session_state["ml_strategy"] = strategy_name
        st.session_state["ml_symbol"] = symbol
        st.session_state["ml_n_trades"] = len(enriched)

    # -----------------------------------------------------
    # ERGEBNIS ANZEIGEN
    # -----------------------------------------------------

    if "ml_result" not in st.session_state:
        st.info(
            "Wähle eine Strategie und klicke **Modell trainieren**. "
            "Die Berechnung dauert ~5–10 Sekunden."
        )
        return

    ml = st.session_state["ml_result"]
    cluster = st.session_state["ml_cluster"]
    filters = st.session_state["ml_filters"]

    st.divider()
    st.subheader(
        f"Ergebnis · {st.session_state['ml_strategy']} "
        f"auf {st.session_state['ml_symbol']} "
        f"· {st.session_state['ml_n_trades']} Trades"
    )

    # Metriken
    _render_metrics(ml["metrics"])

    st.divider()

    # Tabs
    tab_imp, tab_cluster, tab_filters, tab_pred, tab_perm = st.tabs(
        ["📊 Features", "🎯 Cluster", "🔍 Filter",
         "🔮 Predictions", "🧪 Permutation"]
    )

    with tab_imp:
        _render_feature_importance(ml["feature_importance"])

    with tab_cluster:
        if "error" in cluster:
            st.error(cluster["error"])
        else:
            _render_clustering(cluster["summary"])

    with tab_filters:
        _render_filters(filters)

    with tab_pred:
        pred = ml["predictions"].copy()

        st.write(
            "Modell-Vorhersage für die **Test-Daten** (hintere 30 %). "
            "Ein Trade gilt als 'gut' (1), wenn das Modell eine "
            "Gewinnwahrscheinlichkeit > 50 % sieht."
        )

        # Sortiert nach Wahrscheinlichkeit
        pred = pred.sort_values("probability", ascending=False)

        display = pd.DataFrame({
            "Einstieg": pred["einstieg"].dt.strftime("%d.%m.%Y"),
            "Rendite %": (pred["rendite"] * 100).round(2),
            "Echt": pred["actual"].map({1: "Gewinn", 0: "Verlust"}),
            "Vorhersage": pred["prediction"].map({1: "Gewinn", 0: "Verlust"}),
            "Wahrscheinlichkeit": (pred["probability"] * 100).round(1),
        })

        st.dataframe(display, width="stretch", hide_index=True, height=400)

        # Trefferquote
        correct = (pred["prediction"] == pred["actual"]).sum()
        total = len(pred)
        st.caption(
            f"Korrekte Vorhersagen: **{correct} / {total}** "
            f"({correct / total * 100:.1f} %)"
        )

    with tab_perm:
        perm = st.session_state.get("ml_perm")
        if not perm:
            st.info("Kein Permutations-Test verfügbar.")
        else:
            _render_permutation(perm)


# =========================================================
# PERMUTATIONS-TEST ANZEIGE
# =========================================================

def _render_permutation(perm: dict):
    """Zeigt den Permutations-Test."""

    st.subheader("Permutations-Test")

    if "error" in perm:
        st.error(perm["error"])
        return

    st.write(
        "**Was wird geprüft?** Wir haben die echten Trade-Labels (Gewinn/Verlust) "
        "zufällig gemischt und das Modell neu trainiert. Wenn die echte AUC "
        "nicht besser ist als die Zufalls-AUCs, hat das Modell kein echtes Signal gefunden."
    )

    # ---------- KPI-Karten ----------
    real = perm["real_auc"]
    p = perm["p_value"]
    med = perm["percentiles"]["50"]
    q95 = perm["percentiles"]["95"]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Echte AUC", f"{real:.3f}")
    with c2:
        st.metric("Zufalls-Median", f"{med:.3f}")
    with c3:
        st.metric("Zufalls-95 %", f"{q95:.3f}")
    with c4:
        st.metric("p-Wert", f"{p:.4f}")

    # ---------- Bewertung ----------
    if p < 0.01:
        st.success(f"✅ **{perm['verdict']}**")
    elif p < 0.05:
        st.success(f"✅ **{perm['verdict']}**")
    elif p < 0.10:
        st.warning(f"⚠️ **{perm['verdict']}**")
    else:
        st.error(f"❌ **{perm['verdict']}**")
        st.info(
            "💡 **Was das bedeutet:** Das Modell findet **kein** Muster, das "
            "Gewinner von Verlierern vorhersagt. Die Filter-Vorschläge aus dem "
            "anderen Tab sind mit hoher Wahrscheinlichkeit **Overfitting**."
        )

    # ---------- Verteilungs-Chart ----------
    st.markdown("**Verteilung der Zufalls-AUCs**")

    fig = go.Figure()

    # Histogramm der Permutationen
    fig.add_trace(go.Histogram(
        x=perm["perm_aucs"],
        nbinsx=25,
        name="Zufalls-AUCs",
        marker_color="#8B5CF6",
        opacity=0.7,
    ))

    # Rote Linie: echte AUC
    fig.add_vline(
        x=real,
        line_color="#EF4444",
        line_width=3,
        line_dash="dash",
        annotation_text=f"Echt: {real:.3f}",
        annotation_position="top",
    )

    # Grüne Linie: 95%-Quantil
    fig.add_vline(
        x=q95,
        line_color="#22C55E",
        line_width=2,
        line_dash="dot",
        annotation_text=f"95 %: {q95:.3f}",
        annotation_position="top right",
    )

    fig.update_layout(
        height=340,
        margin=dict(l=60, r=20, t=40, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(
            title="AUC",
            gridcolor="#333",
        ),
        yaxis=dict(
            title="Anzahl Permutationen",
            gridcolor="#333",
        ),
        showlegend=False,
        bargap=0.05,
    )

    st.plotly_chart(fig, width="stretch")

    st.caption(
        f"**So liest du den Test:** Die rote Linie (echte AUC = {real:.3f}) zeigt "
        f"wo unsere Strategie liegt. Die violetten Balken sind die Zufallsläufe. "
        f"Wenn die rote Linie **rechts** von den violetten Balken liegt → echtes Signal. "
        f"Wenn sie **mitten drin** oder links liegt → Zufall (wie hier)."
    )