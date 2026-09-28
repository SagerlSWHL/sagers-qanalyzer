"""
backtesting.py
--------------
Backtesting-Seite des Sagers qAnalyzer.

Nutzer wählt Strategie + Symbol + Zeitraum → Backtest läuft →
Kennzahlen + Charts.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.backtest_engine import buy_and_hold, run_backtest
from core.market_data import POPULAR_SYMBOLS, load_ohlc
from core.strategies import STRATEGIES


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def _format_currency(v: float) -> str:
    return f"${v:,.2f}"


def _format_pct(v: float) -> str:
    return f"{v:.2f} %"


def _compute_stats(result, df) -> dict:
    """Berechnet KPI-Kennzahlen aus dem Backtest-Ergebnis."""

    trades = result.trades
    equity = result.daily_equity
    returns = result.daily_returns

    n_trades = len(trades)
    end_equity = float(equity.iloc[-1])
    total_return = end_equity - 1.0

    # CAGR (über Kalendertage)
    days = (df.index[-1] - df.index[0]).days
    years = days / 365.25 if days > 0 else 1.0
    cagr = (end_equity ** (1 / years)) - 1 if years > 0 else 0.0

    # Max Drawdown (Daily MTM)
    rolling_max = equity.cummax()
    dd = (equity / rolling_max) - 1
    max_dd = float(dd.min())

    # Sharpe (annualisiert, rf=0)
    if returns.std() > 0:
        sharpe = float(returns.mean() / returns.std() * (252 ** 0.5))
    else:
        sharpe = 0.0

    # Win Rate
    win_rate = 0.0
    profit_factor = 0.0
    avg_win = 0.0
    avg_loss = 0.0
    avg_hold = 0.0

    if n_trades > 0:
        winners = trades[trades["rendite"] > 0]["rendite"]
        losers = trades[trades["rendite"] < 0]["rendite"]

        win_rate = len(winners) / n_trades
        avg_win = float(winners.mean()) if len(winners) else 0.0
        avg_loss = float(losers.mean()) if len(losers) else 0.0
        avg_hold = float(trades["haltetage"].mean())

        gross_win = winners.sum()
        gross_loss = -losers.sum()
        profit_factor = float(gross_win / gross_loss) if gross_loss > 0 else 0.0

    # Exposure
    exposure = float(result.signals.mean())

    return {
        "n_trades": n_trades,
        "end_equity": end_equity,
        "total_return": total_return,
        "cagr": cagr,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_hold": avg_hold,
        "exposure": exposure,
    }


def _render_equity_chart(result, bh_result):
    """Equity-Chart: Strategie vs. Buy & Hold."""

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=result.daily_equity.index,
        y=result.daily_equity.values,
        mode="lines",
        name="Strategie",
        line=dict(color="#60A5FA", width=2),
    ))

    fig.add_trace(go.Scatter(
        x=bh_result.daily_equity.index,
        y=bh_result.daily_equity.values,
        mode="lines",
        name="Buy & Hold",
        line=dict(color="#F59E0B", width=1.5, dash="dot"),
    ))

    fig.update_layout(
        height=420,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(title="Equity (Start = 1)", gridcolor="#333"),
        legend=dict(orientation="h", y=1.05, x=1, xanchor="right"),
    )

    st.plotly_chart(fig, width="stretch")


def _render_drawdown_chart(result):
    """Drawdown-Verlauf."""

    equity = result.daily_equity
    dd = (equity / equity.cummax()) - 1

    fig = go.Figure()

    fig.add_hline(y=0, line_dash="dash", line_color="#666")

    fig.add_trace(go.Scatter(
        x=dd.index,
        y=dd.values * 100,
        mode="lines",
        name="Drawdown",
        line=dict(color="#EF4444", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(239, 68, 68, 0.15)",
    ))

    fig.update_layout(
        height=320,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(title="Drawdown %", gridcolor="#333"),
    )

    st.plotly_chart(fig, width="stretch")


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_backtesting():
    """Zeigt die Backtesting-Seite."""

    st.title("Backtesting")
    st.write("Teste Handelsstrategien auf historischen Marktdaten.")
    st.divider()

    # -----------------------------------------------------
    # KONFIGURATION
    # -----------------------------------------------------

    st.subheader("Konfiguration")

    col1, col2 = st.columns(2)

    with col1:
        strategy_name = st.selectbox(
            "Strategie",
            options=list(STRATEGIES.keys()),
            index=0,
        )
        strategy_spec = STRATEGIES[strategy_name]
        st.caption(strategy_spec["description"])

    with col2:
        # Symbol-Auswahl (gruppiert)
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

    col3, col4 = st.columns(2)

    with col3:
        start_date = st.date_input(
            "Startdatum",
            value=pd.Timestamp("2000-01-01").date(),
            min_value=pd.Timestamp("1990-01-01").date(),
        )

    with col4:
        cost_side = st.number_input(
            "Kosten je Seite (%)",
            min_value=0.0,
            max_value=1.0,
            value=0.02,
            step=0.01,
            format="%.3f",
        )

    # -----------------------------------------------------
    # BACKTEST STARTEN
    # -----------------------------------------------------

    if st.button("🚀  Backtest starten", type="primary", width="stretch"):

        with st.spinner(f"Lade Daten für {symbol}…"):
            try:
                df = load_ohlc(symbol, start=str(start_date))
            except Exception as exc:
                st.error(f"Fehler beim Laden: {exc}")
                return

        if df.empty:
            st.error("Keine Daten für dieses Symbol / Zeitraum.")
            return

        with st.spinner("Berechne Strategie…"):
            try:
                target = strategy_spec["fn"](df)
                result = run_backtest(df, target, cost_side=cost_side / 100)
                bh_result = buy_and_hold(df, cost_side=cost_side / 100)
            except Exception as exc:
                st.error(f"Fehler beim Backtest: {exc}")
                return

        # Für spätere Nutzung im State speichern
        st.session_state["bt_result"] = result
        st.session_state["bt_bh_result"] = bh_result
        st.session_state["bt_df"] = df
        st.session_state["bt_symbol"] = symbol
        st.session_state["bt_strategy"] = strategy_name

    # -----------------------------------------------------
    # ERGEBNIS ANZEIGEN (falls vorhanden)
    # -----------------------------------------------------

    if "bt_result" not in st.session_state:
        st.info(
            "Wähle eine Strategie und klicke **Backtest starten**. "
            "Der Backtest rechnet auf Tagesbasis von 2000 bis heute."
        )
        return

    result = st.session_state["bt_result"]
    bh_result = st.session_state["bt_bh_result"]
    df = st.session_state["bt_df"]
    symbol = st.session_state["bt_symbol"]
    strategy_name = st.session_state["bt_strategy"]

    st.divider()
    st.subheader(f"Ergebnis · {strategy_name} auf {symbol}")

    stats = _compute_stats(result, df)
    bh_stats = _compute_stats(bh_result, df)

    # -----------------------------------------------------
    # KPI-ZEILE 1
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "CAGR",
            _format_pct(stats["cagr"] * 100),
            delta=_format_pct((stats["cagr"] - bh_stats["cagr"]) * 100),
        )

    with col2:
        st.metric(
            "Max Drawdown",
            _format_pct(stats["max_dd"] * 100),
            delta=_format_pct((stats["max_dd"] - bh_stats["max_dd"]) * 100),
            delta_color="inverse",
        )

    with col3:
        st.metric(
            "Sharpe (annualisiert)",
            f"{stats['sharpe']:.2f}",
            delta=f"{stats['sharpe'] - bh_stats['sharpe']:+.2f}",
        )

    with col4:
        st.metric(
            "Endequity",
            f"{stats['end_equity']:.2f}×",
            delta=f"{(stats['end_equity'] - bh_stats['end_equity']):.2f}× vs. B&H",
        )

    # -----------------------------------------------------
    # KPI-ZEILE 2
    # -----------------------------------------------------

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric("Trades", stats["n_trades"])

    with col6:
        st.metric("Win Rate", _format_pct(stats["win_rate"] * 100))

    with col7:
        st.metric("Profit Factor", f"{stats['profit_factor']:.2f}")

    with col8:
        st.metric("Exposure", _format_pct(stats["exposure"] * 100))

    # -----------------------------------------------------
    # KPI-ZEILE 3
    # -----------------------------------------------------

    col9, col10, col11, col12 = st.columns(4)

    with col9:
        st.metric("Ø Gewinn", _format_pct(stats["avg_win"] * 100))

    with col10:
        st.metric("Ø Verlust", _format_pct(stats["avg_loss"] * 100))

    with col11:
        st.metric("Ø Haltedauer", f"{stats['avg_hold']:.1f} Tage")

    with col12:
        # Kaufen und Halten als Vergleich
        st.metric("B&H Endequity", f"{bh_stats['end_equity']:.2f}×")

    st.divider()

    # -----------------------------------------------------
    # TABS
    # -----------------------------------------------------

    tab_eq, tab_dd, tab_trades = st.tabs(
        ["Equity", "Drawdown", "Trades"]
    )

    with tab_eq:
        _render_equity_chart(result, bh_result)

    with tab_dd:
        _render_drawdown_chart(result)

    with tab_trades:
        if result.trades.empty:
            st.info("Keine Trades.")
        else:
            display = result.trades.copy()
            display["rendite"] = (display["rendite"] * 100).round(2)
            display["mae"] = (display["mae"] * 100).round(2)
            display["mfe"] = (display["mfe"] * 100).round(2)
            display.columns = [
                "Einstieg", "Ausstieg", "Kurs Ein", "Kurs Aus",
                "Rendite %", "Haltedauer", "MAE %", "MFE %",
            ]
            st.dataframe(
                display,
                width="stretch",
                hide_index=True,
                height=500,
            )