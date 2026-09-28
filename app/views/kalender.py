"""
kalender.py
-----------
Kalender-Seite mit Trades + Journal.

Monatsansicht wie Microsoft Teams. Pro Tag Karten mit Trades.
Klick auf Karte → Details + Bearbeiten.
"""

import calendar
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import streamlit as st

from core.auth import get_current_user
from core.supabase_client import get_authenticated_client


# =========================================================
# SESSION-KEYS
# =========================================================

KEY_CAL_YEAR = "cal_year"
KEY_CAL_MONTH = "cal_month"
KEY_SELECTED_TRADE = "cal_selected_trade"
KEY_NEW_TRADE = "cal_new_trade"


# =========================================================
# DATEN LADEN
# =========================================================

def _load_trades_for_month(year: int, month: int) -> list:
    """Lädt alle Trades eines Monats für den eingeloggten User."""

    client = get_authenticated_client()

    # Monatsgrenzen
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)

    try:
        response = (
            client.table("trades")
            .select("*")
            .gte("datum", first.isoformat())
            .lte("datum", last.isoformat())
            .order("datum")
            .execute()
        )
        return response.data or []
    except Exception as exc:
        st.error(f"Fehler beim Laden: {exc}")
        return []


# =========================================================
# NAVIGATION
# =========================================================

def _render_navigation():
    """Zeigt Monatsnavigation + Neue-Trade-Button."""

    today = date.today()
    year = st.session_state.get(KEY_CAL_YEAR, today.year)
    month = st.session_state.get(KEY_CAL_MONTH, today.month)

    col_prev, col_title, col_today, col_next, col_new = st.columns([0.5, 3, 1, 0.5, 1.4])

    with col_prev:
        if st.button("◀", width="stretch", key="cal_prev"):
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
            st.session_state[KEY_CAL_YEAR] = year
            st.session_state[KEY_CAL_MONTH] = month
            st.rerun()

    with col_title:
        month_name = datetime(year, month, 1).strftime("%B %Y")
        st.markdown(
            f"### 📅  {month_name}",
            help=f"Monatsübersicht · {year}",
        )

    with col_today:
        if st.button("Heute", width="stretch", key="cal_today"):
            st.session_state[KEY_CAL_YEAR] = today.year
            st.session_state[KEY_CAL_MONTH] = today.month
            st.rerun()

    with col_next:
        if st.button("▶", width="stretch", key="cal_next"):
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
            st.session_state[KEY_CAL_YEAR] = year
            st.session_state[KEY_CAL_MONTH] = month
            st.rerun()

    with col_new:
        if st.button(
            "➕  Neuer Trade",
            type="primary",
            width="stretch",
            key="cal_new_trade_btn",
        ):
            st.session_state[KEY_NEW_TRADE] = True
            st.session_state[KEY_SELECTED_TRADE] = None
            st.rerun()

    return year, month


# =========================================================
# KALENDER-GRID
# =========================================================

def _trade_color(trade: dict) -> str:
    """Farbe für eine Trade-Karte."""

    status = trade.get("status", "geplant")
    pnl = trade.get("pnl")

    if status == "verworfen":
        return "#555"       # grau
    if status == "geplant":
        return "#8b8b8b"    # neutral
    if pnl is not None:
        if pnl > 0:
            return "#22C55E"  # grün
        if pnl < 0:
            return "#EF4444"  # rot
    return "#8b8b8b"


def _render_trade_card(trade: dict, compact: bool = True):
    """Zeigt eine kompakte Trade-Karte."""

    color = _trade_color(trade)

    symbol = trade.get("symbol", "?")
    richtung = trade.get("richtung", "")
    pnl = trade.get("pnl")
    status = trade.get("status", "geplant")

    if compact:
        # Mini-Karte mit Symbol + Richtung
        icon = "▲" if richtung == "Long" else ("▼" if richtung == "Short" else "•")

        pnl_text = ""
        if pnl is not None:
            sign = "+" if pnl >= 0 else ""
            pnl_text = f"{sign}{pnl:,.0f}"

        st.markdown(
            f"""
            <div style="
                background: {color}20;
                border-left: 3px solid {color};
                padding: 4px 6px;
                margin: 2px 0;
                border-radius: 4px;
                font-size: 11px;
                color: #ddd;
            ">
                <strong>{icon} {symbol}</strong>
                {f'<span style="float:right; color:{color};">{pnl_text}</span>' if pnl_text else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Klick-Button zum Auswählen
        if st.button(
            "Öffnen",
            key=f"open_trade_{trade['id']}",
            width="stretch",
        ):
            st.session_state[KEY_SELECTED_TRADE] = trade["id"]
            st.session_state[KEY_NEW_TRADE] = False
            st.rerun()


def _render_month_grid(year: int, month: int, trades: list):
    """Rendert das Kalender-Grid."""

    # Wochenstart Montag
    calendar.setfirstweekday(calendar.MONDAY)

    # Kopfzeile
    wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    cols = st.columns(7)
    for i, tag in enumerate(wochentage):
        cols[i].markdown(
            f"<div style='text-align:center; color:#888; font-size:12px; padding:4px 0;'>{tag}</div>",
            unsafe_allow_html=True,
        )

    # Wochen
    wochen = calendar.monthcalendar(year, month)

    # Trades nach Tag gruppieren
    trades_by_day = {}
    for t in trades:
        d = t.get("datum")
        if d:
            trades_by_day.setdefault(d, []).append(t)

    today = date.today()

    for woche in wochen:
        cols = st.columns(7)

        for i, tag in enumerate(woche):
            with cols[i]:

                if tag == 0:
                    # Leerer Tag
                    st.markdown(
                        "<div style='height:120px;'></div>",
                        unsafe_allow_html=True,
                    )
                    continue

                datum = date(year, month, tag)
                datum_str = datum.isoformat()
                ist_heute = datum == today
                trades_am_tag = trades_by_day.get(datum_str, [])

                # Tag-Karte
                with st.container(border=True):

                    # Kopfzeile mit Tag-Nummer
                    heute_marker = "🔥" if ist_heute else ""
                    st.markdown(
                        f"<div style='font-size:11px; color:{'#f59e0b' if ist_heute else '#888'}; "
                        f"font-weight:600; margin-bottom:4px;'>"
                        f"{tag} {heute_marker}</div>",
                        unsafe_allow_html=True,
                    )

                    # Trades
                    if trades_am_tag:
                        for t in trades_am_tag[:3]:
                            _render_trade_card(t)

                        if len(trades_am_tag) > 3:
                            st.caption(f"+ {len(trades_am_tag) - 3} weitere")

                    # Plus-Button
                    if st.button(
                        "＋",
                        key=f"add_trade_{datum_str}",
                        width="stretch",
                        help=f"Trade am {datum.strftime('%d.%m.%Y')} planen",
                    ):
                        st.session_state[KEY_NEW_TRADE] = True
                        st.session_state["new_trade_datum"] = datum_str
                        st.session_state[KEY_SELECTED_TRADE] = None
                        st.rerun()


# =========================================================
# FORMULAR: NEUER TRADE / BEARBEITEN
# =========================================================

def _trade_form(existing: Optional[dict] = None, default_datum: Optional[str] = None):
    """Formular zum Anlegen oder Bearbeiten eines Trades."""

    is_new = existing is None
    prefix = "new" if is_new else existing["id"]

    st.markdown(f"### {'➕  Neuer Trade' if is_new else '✏️  Trade bearbeiten'}")

    # ---------- Basisdaten ----------
    col1, col2, col3 = st.columns(3)

    with col1:
        datum = st.date_input(
            "Datum",
            value=(
                pd.to_datetime(existing["datum"]).date()
                if existing and existing.get("datum")
                else pd.to_datetime(default_datum or date.today()).date()
            ),
            key=f"tf_datum_{prefix}",
        )

    with col2:
        symbol = st.text_input(
            "Symbol",
            value=existing.get("symbol", "") if existing else "",
            placeholder="z.B. QQQ",
            key=f"tf_symbol_{prefix}",
        )

    with col3:
        richtung = st.selectbox(
            "Richtung",
            options=["Long", "Short"],
            index=(
                ["Long", "Short"].index(existing.get("richtung", "Long"))
                if existing and existing.get("richtung") in ["Long", "Short"]
                else 0
            ),
            key=f"tf_richtung_{prefix}",
        )

    # ---------- Planung ----------
    st.markdown("**Planung**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        entry = st.number_input(
            "Geplanter Entry",
            value=float(existing.get("geplanter_entry") or 0) if existing else 0.0,
            step=0.01,
            format="%.4f",
            key=f"tf_entry_{prefix}",
        )

    with col2:
        exit_p = st.number_input(
            "Geplanter Exit",
            value=float(existing.get("geplanter_exit") or 0) if existing else 0.0,
            step=0.01,
            format="%.4f",
            key=f"tf_exit_{prefix}",
        )

    with col3:
        stop = st.number_input(
            "Stop-Loss",
            value=float(existing.get("stop_loss") or 0) if existing else 0.0,
            step=0.01,
            format="%.4f",
            key=f"tf_stop_{prefix}",
        )

    with col4:
        tp = st.number_input(
            "Take-Profit",
            value=float(existing.get("take_profit") or 0) if existing else 0.0,
            step=0.01,
            format="%.4f",
            key=f"tf_tp_{prefix}",
        )

    # ---------- Ausführung ----------
    st.markdown("**Ausführung** *(nach dem Trade ausfüllen)*")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tats_entry = st.number_input(
            "Tats. Entry",
            value=float(existing.get("tatsaechlicher_entry") or 0) if existing else 0.0,
            step=0.01,
            format="%.4f",
            key=f"tf_tentry_{prefix}",
        )

    with col2:
        tats_exit = st.number_input(
            "Tats. Exit",
            value=float(existing.get("tatsaechlicher_exit") or 0) if existing else 0.0,
            step=0.01,
            format="%.4f",
            key=f"tf_texit_{prefix}",
        )

    with col3:
        position = st.number_input(
            "Positionsgröße",
            value=float(existing.get("positionsgroesse") or 0) if existing else 0.0,
            step=1.0,
            key=f"tf_pos_{prefix}",
        )

    with col4:
        pnl = st.number_input(
            "P&L (USD)",
            value=float(existing.get("pnl") or 0) if existing else 0.0,
            step=10.0,
            key=f"tf_pnl_{prefix}",
        )

    # ---------- Status ----------
    status_options = ["geplant", "offen", "geschlossen", "verworfen"]
    status = st.selectbox(
        "Status",
        options=status_options,
        index=(
            status_options.index(existing.get("status", "geplant"))
            if existing and existing.get("status") in status_options
            else 0
        ),
        key=f"tf_status_{prefix}",
    )

    # ---------- Notizen / Emotion / Tags ----------
    notizen = st.text_area(
        "Notizen",
        value=existing.get("notizen", "") if existing else "",
        height=80,
        placeholder="Setup, Gedanken, Regelbruch …",
        key=f"tf_notizen_{prefix}",
    )

    col1, col2 = st.columns(2)
    with col1:
        emotion = st.text_input(
            "Emotion",
            value=existing.get("emotion", "") if existing else "",
            placeholder="ruhig / FOMO / nervös",
            key=f"tf_emotion_{prefix}",
        )

    with col2:
        tags_raw = ", ".join(existing.get("tags", [])) if existing else ""
        tags = st.text_input(
            "Tags (Komma-getrennt)",
            value=tags_raw,
            placeholder="setup-a, regelbruch",
            key=f"tf_tags_{prefix}",
        )

    # ---------- Buttons ----------
    st.divider()

    col_save, col_cancel = st.columns([1, 1])

    with col_save:
        if st.button(
            "💾  Speichern",
            type="primary",
            width="stretch",
            key=f"tf_save_{prefix}",
        ):
            if not symbol.strip():
                st.error("Symbol ist erforderlich.")
            else:
                data = {
                    "datum": datum.isoformat(),
                    "symbol": symbol.strip().upper(),
                    "richtung": richtung,
                    "geplanter_entry": entry or None,
                    "geplanter_exit": exit_p or None,
                    "stop_loss": stop or None,
                    "take_profit": tp or None,
                    "tatsaechlicher_entry": tats_entry or None,
                    "tatsaechlicher_exit": tats_exit or None,
                    "positionsgroesse": position or None,
                    "pnl": pnl or None,
                    "status": status,
                    "notizen": notizen.strip(),
                    "emotion": emotion.strip(),
                    "tags": [t.strip() for t in tags.split(",") if t.strip()],
                }

                try:
                    client = get_authenticated_client()
                    user = get_current_user()

                    if is_new:
                        data["user_id"] = user["id"]
                        client.table("trades").insert(data).execute()
                    else:
                        client.table("trades").update(data).eq(
                            "id", existing["id"]
                        ).execute()

                    st.session_state[KEY_NEW_TRADE] = False
                    st.session_state[KEY_SELECTED_TRADE] = None
                    st.success("Gespeichert!")
                    st.rerun()

                except Exception as exc:
                    st.error(f"Fehler beim Speichern: {exc}")

    with col_cancel:
        if st.button(
            "Abbrechen",
            width="stretch",
            key=f"tf_cancel_{prefix}",
        ):
            st.session_state[KEY_NEW_TRADE] = False
            st.session_state[KEY_SELECTED_TRADE] = None
            st.rerun()


# =========================================================
# TRADE-DETAILS
# =========================================================

def _trade_detail(trade: dict):
    """Zeigt Details eines Trades mit Bearbeiten- und Löschen-Option."""

    st.markdown(f"### 📊  {trade.get('symbol', '?')} · {trade.get('datum', '')}")

    col1, col2 = st.columns([3, 1])

    with col1:
        richtung = trade.get("richtung", "—")
        status = trade.get("status", "—")
        st.caption(f"**{richtung}** · Status: **{status}**")

    with col2:
        if st.button("✏️  Bearbeiten", width="stretch", key=f"edit_{trade['id']}"):
            st.session_state["edit_trade"] = trade["id"]
            st.session_state[KEY_SELECTED_TRADE] = None
            st.rerun()

    # Kennzahlen
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        entry = trade.get("tatsaechlicher_entry") or trade.get("geplanter_entry")
        st.metric("Entry", f"{entry:.2f}" if entry else "—")

    with c2:
        exit_p = trade.get("tatsaechlicher_exit") or trade.get("geplanter_exit")
        st.metric("Exit", f"{exit_p:.2f}" if exit_p else "—")

    with c3:
        stop = trade.get("stop_loss")
        st.metric("Stop", f"{stop:.2f}" if stop else "—")

    with c4:
        pnl = trade.get("pnl")
        if pnl is not None:
            st.metric("P&L", f"${pnl:,.2f}")
        else:
            st.metric("P&L", "—")

    # Notizen
    if trade.get("notizen"):
        st.markdown("**Notizen**")
        st.write(trade["notizen"])

    # Emotion + Tags
    if trade.get("emotion") or trade.get("tags"):
        st.caption(
            f"Emotion: {trade.get('emotion', '—')} · "
            f"Tags: {', '.join(trade.get('tags', [])) or '—'}"
        )

    # Löschen
    with st.expander("🗑️  Löschen"):
        st.warning("Dieser Vorgang kann nicht rückgängig gemacht werden.")
        if st.button("Endgültig löschen", type="primary", key=f"del_{trade['id']}"):
            try:
                client = get_authenticated_client()
                client.table("trades").delete().eq("id", trade["id"]).execute()
                st.session_state[KEY_SELECTED_TRADE] = None
                st.success("Gelöscht.")
                st.rerun()
            except Exception as exc:
                st.error(f"Fehler: {exc}")

    if st.button("Schließen", key=f"close_{trade['id']}"):
        st.session_state[KEY_SELECTED_TRADE] = None
        st.rerun()


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_kalender():
    """Zeigt die Kalender-Seite."""

    st.title("Kalender")
    st.write("Plane und dokumentiere deine Trades.")
    st.divider()

    # ---------- Formular-Anzeige priorisiert ----------

    # 1) Neue-Trade-Formular
    if st.session_state.get(KEY_NEW_TRADE, False):
        default_datum = st.session_state.get("new_trade_datum")
        _trade_form(existing=None, default_datum=default_datum)
        return

    # 2) Bearbeiten-Formular
    if "edit_trade" in st.session_state and st.session_state["edit_trade"]:
        # Trade laden
        try:
            client = get_authenticated_client()
            r = client.table("trades").select("*").eq(
                "id", st.session_state["edit_trade"]
            ).execute()

            if r.data:
                _trade_form(existing=r.data[0])
                return
        except Exception:
            st.session_state.pop("edit_trade", None)

    # 3) Detail-Anzeige
    if st.session_state.get(KEY_SELECTED_TRADE):
        try:
            client = get_authenticated_client()
            r = client.table("trades").select("*").eq(
                "id", st.session_state[KEY_SELECTED_TRADE]
            ).execute()

            if r.data:
                _trade_detail(r.data[0])
                return
        except Exception:
            st.session_state.pop(KEY_SELECTED_TRADE, None)

    # ---------- Monatsnavigation ----------
    year, month = _render_navigation()

    st.divider()

    # ---------- Trades laden ----------
    trades = _load_trades_for_month(year, month)

    # ---------- Statistik-Zeile ----------
    if trades:
        n_total = len(trades)
        n_closed = sum(1 for t in trades if t.get("status") == "geschlossen")
        pnl_total = sum(t.get("pnl") or 0 for t in trades)
        winners = sum(1 for t in trades if (t.get("pnl") or 0) > 0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Trades im Monat", n_total)
        c2.metric("Abgeschlossen", n_closed)
        c3.metric(
            "P&L",
            f"${pnl_total:,.0f}",
            delta=f"{winners} Gewinner" if winners else None,
        )
        c4.metric(
            "Win Rate",
            f"{winners / n_closed * 100:.0f} %" if n_closed else "—",
        )

        st.divider()

    # ---------- Kalender-Grid ----------
    _render_month_grid(year, month, trades)