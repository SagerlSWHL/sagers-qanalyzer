"""
overview.py
-----------
Overview-Seite – persönliches Cockpit des eingeloggten Users.

Zeigt:
  - Heute fällige Trades
  - Wochenübersicht
  - Persönliche KPIs
"""

import calendar as cal
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from core.auth import get_current_user
from core.strategies_db import WEEKDAY_LABELS
from core.supabase_client import get_authenticated_client


# =========================================================
# DATEN LADEN
# =========================================================

def _load_trades_range(start: date, end: date) -> list:
    """Lädt alle Trades im Zeitraum."""

    client = get_authenticated_client()
    try:
        r = (
            client.table("trades")
            .select("*")
            .gte("datum", start.isoformat())
            .lte("datum", end.isoformat())
            .order("datum")
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def _load_all_trades() -> list:
    """Lädt alle Trades des Users (für KPIs)."""

    client = get_authenticated_client()
    try:
        r = (
            client.table("trades")
            .select("*")
            .order("datum", desc=True)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


# =========================================================
# KPI-BERECHNUNG
# =========================================================

def _compute_kpis(trades: list) -> dict:
    """Berechnet Portfolio-KPIs aus den Trades."""

    closed = [t for t in trades if t.get("status") == "geschlossen"]
    pnls = [t.get("pnl") or 0 for t in closed if t.get("pnl") is not None]

    n_total = len(trades)
    n_closed = len(closed)
    n_planned = len([t for t in trades if t.get("status") == "geplant"])
    n_open = len([t for t in trades if t.get("status") == "offen"])
    n_discarded = len([t for t in trades if t.get("status") == "verworfen"])

    net_pnl = sum(pnls)
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]

    win_rate = (len(winners) / n_closed * 100) if n_closed else 0
    gross_win = sum(winners)
    gross_loss = abs(sum(losers))
    profit_factor = (gross_win / gross_loss) if gross_loss else 0

    avg_win = (sum(winners) / len(winners)) if winners else 0
    avg_loss = (sum(losers) / len(losers)) if losers else 0
    expectancy = net_pnl / n_closed if n_closed else 0

    return {
        "n_total": n_total,
        "n_closed": n_closed,
        "n_planned": n_planned,
        "n_open": n_open,
        "n_discarded": n_discarded,
        "net_pnl": net_pnl,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
    }


# =========================================================
# RENDER
# =========================================================

def _render_welcome(user: dict):
    """Willkommens-Header."""

    email = user.get("email", "User")
    name = email.split("@")[0]

    st.markdown(
        f"""
        <div style="
            padding: 12px 0 6px 0;
        ">
            <span style="font-size: 13px; color: #888;">
                Willkommen zurück,
            </span>
            <h1 style="
                margin: 4px 0 0 0;
                font-size: 38px;
            ">
                {name}
            </h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_today(trades_today: list):
    """Heute fällige Trades."""

    st.markdown("### 📅  Heute")

    if not trades_today:
        st.info("Keine Trades für heute geplant.")
        return

    for t in trades_today:
        status = t.get("status", "geplant")
        symbol = t.get("symbol", "?")
        richtung = t.get("richtung", "")
        note = t.get("validation_note", "")

        icon = {
            "geplant": "🟡",
            "offen": "🔵",
            "geschlossen": "✅",
            "verworfen": "⚫",
        }.get(status, "•")

        richtung_icon = "▲" if richtung == "Long" else ("▼" if richtung == "Short" else "")

        cols = st.columns([1, 3, 2, 2])

        with cols[0]:
            st.markdown(f"### {icon}")
        with cols[1]:
            st.markdown(f"**{richtung_icon} {symbol}**")
            if t.get("notizen"):
                st.caption(t["notizen"][:80])
        with cols[2]:
            st.caption(f"Status: **{status}**")
        with cols[3]:
            if note:
                st.caption(note)


def _render_week(trades_week: list, today: date):
    """Wochenübersicht."""

    st.markdown("### 📊  Diese Woche")

    # Nach Wochentag gruppieren
    by_day = {}
    for t in trades_week:
        try:
            d = pd.to_datetime(t["datum"]).date()
            by_day.setdefault(d, []).append(t)
        except Exception:
            continue

    if not by_day:
        st.info("Keine Trades diese Woche.")
        return

    # 7 Tage anzeigen
    for i in range(7):
        d = today - timedelta(days=today.weekday()) + timedelta(days=i)
        is_today = d == today
        day_trades = by_day.get(d, [])

        marker = "🔥" if is_today else ""

        with st.expander(
            f"{WEEKDAY_LABELS[d.weekday()]}, {d.strftime('%d.%m.')} "
            f"{marker}  ·  {len(day_trades)} Trade(s)",
            expanded=is_today,
        ):
            if not day_trades:
                st.caption("—")
                continue

            for t in day_trades:
                status = t.get("status", "geplant")
                symbol = t.get("symbol", "?")
                richtung = t.get("richtung", "")
                pnl = t.get("pnl")
                note = t.get("validation_note", "")

                richtung_icon = "▲" if richtung == "Long" else ("▼" if richtung == "Short" else "")

                pnl_text = ""
                if pnl is not None:
                    pnl_text = f" · **{pnl:+,.2f} USD**"

                st.markdown(
                    f"**{richtung_icon} {symbol}** "
                    f"· {status}{pnl_text}"
                )
                if note:
                    st.caption(note)


def _render_kpis(kpis: dict):
    """KPI-Karten."""

    st.markdown("### 📈  Meine Zahlen")

    # Zeile 1: Netto-Zahlen
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Net Profit",
            f"${kpis['net_pnl']:,.2f}",
        )

    with c2:
        st.metric(
            "Win Rate",
            f"{kpis['win_rate']:.1f} %",
        )

    with c3:
        st.metric(
            "Profit Factor",
            f"{kpis['profit_factor']:.2f}",
        )

    with c4:
        st.metric(
            "Ø P&L pro Trade",
            f"${kpis['expectancy']:,.2f}",
        )

    # Zeile 2: Trades
    c5, c6, c7, c8 = st.columns(4)

    with c5:
        st.metric("Trades gesamt", kpis["n_total"])

    with c6:
        st.metric("Geplant", kpis["n_planned"])

    with c7:
        st.metric("Offen", kpis["n_open"])

    with c8:
        st.metric("Geschlossen", kpis["n_closed"])

    # Zeile 3: Durchschnitte
    c9, c10, c11, c12 = st.columns(4)

    with c9:
        st.metric("Ø Gewinn", f"${kpis['avg_win']:,.2f}")

    with c10:
        st.metric("Ø Verlust", f"${kpis['avg_loss']:,.2f}")

    with c11:
        st.metric("Verworfen", kpis["n_discarded"])

    with c12:
        ratio = kpis["avg_win"] / abs(kpis["avg_loss"]) if kpis["avg_loss"] else 0
        st.metric("Payoff", f"{ratio:.2f}")


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_overview():
    """Zeigt die Overview-Seite (login-abhängig)."""

    user = get_current_user()

    if not user:
        st.warning("Bitte einloggen.")
        return

    _render_welcome(user)

    st.divider()

    # ---------- Trades laden ----------

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    trades_today = _load_trades_range(today, today)
    trades_week = _load_trades_range(week_start, week_end)
    all_trades = _load_all_trades()

    # ---------- Heute ----------
    _render_today(trades_today)

    st.divider()

    # ---------- Woche ----------
    _render_week(trades_week, today)

    st.divider()

    # ---------- KPIs ----------
    kpis = _compute_kpis(all_trades)
    _render_kpis(kpis)

    # ---------- Hinweis bei leer ----------
    if kpis["n_total"] == 0:
        st.divider()
        st.info(
            "💡 **Noch keine Trades.** Lege im **Kalender** deinen ersten Trade an "
            "oder hinterlege im Bereich **Strategien** Zeitregeln für "
            "automatisch generierte Trades."
        )