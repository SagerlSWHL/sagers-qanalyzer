"""
performance.py
--------------
Performance-Seite: Charts und Kennzahlen aus deinen Journal-Trades.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.auth import get_current_user
from core.journal_metrics import build_trade_df, compute_kpis, monthly_returns
from core.supabase_client import get_authenticated_client


@st.cache_data(ttl=5, show_spinner=False)
def _load_closed_trades(user_id: str) -> list:
    client = get_authenticated_client()
    try:
        r = (
            client.table("trades")
            .select("*")
            .eq("status", "geschlossen")
            .order("datum")
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def _render_kpi_cards(k: dict):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net Profit", f"${k['net_profit']:,.2f}")
    c2.metric("Return", f"{k['return_pct']:.2f} %")
    c3.metric("CAGR", f"{k['cagr']:.2f} %")
    c4.metric("Max DD", f"${k['max_dd']:,.2f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Win Rate", f"{k['win_rate']:.1f} %")
    c6.metric(
        "Profit Factor",
        f"{k['profit_factor']:.2f}" if k["profit_factor"] > 0 else "—",
    )
    c7.metric("Expectancy", f"${k['expectancy']:,.2f}")
    c8.metric(
        "Sharpe (ann.)",
        f"{k['sharpe']:.2f}" if k["n"] >= 5 else "—",
    )

    c9, c10, c11, c12 = st.columns(4)
    c9.metric("Trades", k["n"])
    c10.metric("Bester Trade", f"${k['best']:,.2f}")
    c11.metric("Schlechtester", f"${k['worst']:,.2f}")
    c12.metric("Serien", f"{k['streak_win']}W / {k['streak_loss']}L")


def _render_equity(df: pd.DataFrame, symbol: str = "SPY"):
    from core.journal_metrics import benchmark_curve

    fig = go.Figure()

    # Strategie-Equity
    fig.add_trace(go.Scatter(
        x=df["datum"], y=df["kum_pnl"],
        mode="lines", name="Journal",
        line=dict(color="#60A5FA", width=2),
    ))

    # Benchmark (Buy & Hold)
    bh = benchmark_curve(df, symbol)
    if not bh.empty:
        fig.add_trace(go.Scatter(
            x=bh.index, y=bh.values,
            mode="lines", name=f"Buy & Hold ({symbol})",
            line=dict(color="#F59E0B", width=1.5, dash="dot"),
        ))

    fig.update_layout(
        height=360, margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(title="P&L (USD)", gridcolor="#333"),
        legend=dict(orientation="h", y=1.05, x=1, xanchor="right"),
    )
    st.plotly_chart(fig, width="stretch")


def _render_drawdown(df: pd.DataFrame):
    running_max = df["kum_pnl"].cummax()
    dd = df["kum_pnl"] - running_max

    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="#666")
    fig.add_trace(go.Scatter(
        x=df["datum"], y=dd,
        mode="lines", name="Drawdown",
        line=dict(color="#EF4444", width=1.5),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.15)",
    ))
    fig.update_layout(
        height=300, margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(title="Drawdown (USD)", gridcolor="#333"),
    )
    st.plotly_chart(fig, width="stretch")


def _render_monthly(pivot: pd.DataFrame):
    if pivot.empty:
        st.info("Keine Monatsdaten.")
        return

    text = pivot.map(lambda v: f"{v:+,.0f}" if pd.notna(v) else "")
    max_abs = float(pivot.abs().max().max()) or 1.0

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index.astype(str),
        text=text.values, texttemplate="%{text}",
        textfont={"size": 11},
        colorscale=[
            [0.0, "#8B0000"], [0.5, "#1a1a1a"], [1.0, "#0F8B3C"],
        ],
        zmid=0, zmin=-max_abs, zmax=max_abs,
        showscale=True, hoverongaps=False,
        colorbar=dict(title="USD"),
    ))
    fig.update_layout(
        height=40 * len(pivot) + 180,
        margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(side="top"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch")


def _render_distribution(df: pd.DataFrame):
    pnl = df["pnl"]
    counts, edges = pd.np.histogram(pnl, bins=30) if hasattr(pd, "np") else (None, None)
    # Fallback ohne numpy-Import:
    import numpy as np
    counts, edges = np.histogram(pnl, bins=30)
    centers = (edges[:-1] + edges[1:]) / 2
    colors = ["#EF4444" if c < 0 else "#22C55E" for c in centers]

    fig = go.Figure(data=go.Bar(
        x=centers, y=counts, marker_color=colors,
        hovertemplate="P&L: %{x:,.0f}<br>Anzahl: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=320, margin=dict(l=60, r=20, t=20, b=40),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#e6e6e6"),
        xaxis=dict(title="P&L (USD)", gridcolor="#333"),
        yaxis=dict(title="Anzahl", gridcolor="#333"),
        bargap=0.02, showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")


def show_performance():
    st.title("Performance")
    st.write("Deine echten Trades – Kennzahlen und Charts.")
    st.divider()

    user = get_current_user()
    if not user:
        st.warning("Bitte einloggen.")
        return

    trades = _load_closed_trades(user["id"])
    df = build_trade_df(trades)

    if df.empty:
        st.info(
            "📊 **Noch keine geschlossenen Trades.**\n\n"
            "Trage im **Kalender** bei deinen Trades den Status auf "
            "**geschlossen** und einen P&L-Wert ein. Dann erscheinen "
            "sie hier als Equity-Kurve, Drawdown und Monats-Heatmap."
        )
        return

    # KPIs
    k = compute_kpis(df)
    _render_kpi_cards(k)

    st.divider()

    # Tabs
    tab_eq, tab_dd, tab_month, tab_dist, tab_list = st.tabs(
        ["Equity", "Drawdown", "Monthly", "Verteilung", "Trades"]
    )

    with tab_eq:
        # Symbol-Auswahl für Benchmark
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.caption("Vergleich mit Buy & Hold")
        with col_b:
            benchmark_symbol = st.selectbox(
                "Benchmark",
                options=["SPY", "QQQ", "TLT", "GLD", "BTC-USD", "^GDAXI"],
                index=0,
                label_visibility="collapsed",
                key="perf_benchmark_select",
            )

        _render_equity(df, benchmark_symbol)

        # Benchmark-Vergleich-KPI
        from core.journal_metrics import benchmark_curve
        bh = benchmark_curve(df, benchmark_symbol)
        if not bh.empty:
            bh_return = float(bh.iloc[-1])
            journal_return = float(df["kum_pnl"].iloc[-1])
            diff = journal_return - bh_return

            col1, col2, col3 = st.columns(3)
            col1.metric(
                "Journal P&L",
                f"${journal_return:,.2f}",
            )
            col2.metric(
                f"Buy & Hold {benchmark_symbol}",
                f"${bh_return:,.2f}",
            )
            col3.metric(
                "Differenz",
                f"${diff:+,.2f}",
                delta="Outperformance" if diff > 0 else "Underperformance",
                delta_color="normal" if diff > 0 else "inverse",
            )

    with tab_dd:
        _render_drawdown(df)

    with tab_month:
        _render_monthly(monthly_returns(df))

    with tab_dist:
        _render_distribution(df)

    with tab_list:
        display = df.copy()
        display["datum"] = display["datum"].dt.strftime("%d.%m.%Y")

        # Zahlen hübscher formatieren
        display["pnl"] = display["pnl"].apply(lambda v: f"${v:+,.2f}")
        display["kum_pnl"] = display["kum_pnl"].apply(lambda v: f"${v:,.2f}")
        display["kum_pct"] = display["kum_pct"].apply(lambda v: f"{v:+.2f} %")

        display.columns = [
            "Datum", "Symbol", "Richtung",
            "P&L", "Kumuliert USD", "Kumuliert %",
        ]

        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            height=500,
        )

        # CSV-Export
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥  Als CSV herunterladen",
            data=csv,
            file_name="journal_trades.csv",
            mime="text/csv",
            width="stretch",
        )
