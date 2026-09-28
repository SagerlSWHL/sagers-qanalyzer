"""
strategien.py
-------------
Strategie-Bibliothek mit Supabase + Live-Validierung.
"""

from datetime import date, time

import pandas as pd
import streamlit as st

from core.strategies_db import (
    WEEKDAY_LABELS,
    create_strategy,
    delete_strategy,
    ensure_seed_strategies,
    load_user_strategies,
    update_strategy,
)
from core.strategy_validator import VALIDATION_TYPES, validate_strategy
from core.strategies_store import load_excel_summary, save_uploaded_file


def _s(key, default=""):
    """Sicheres Lesen aus session_state (None-safe)."""
    val = st.session_state.get(key)
    return val if val is not None else default


def _format_time(val):
    if not val:
        return "-"
    if isinstance(val, str):
        return val[:5]
    if hasattr(val, "strftime"):
        return val.strftime("%H:%M")
    return str(val)


def _strategy_form(existing=None, is_new=True):
    prefix = "new" if is_new else existing["id"]

    st.text_input(
        "Name",
        value=existing.get("name", "") if existing else "",
        key=f"f_name_{prefix}",
    )

    col1, col2, col3 = st.columns(3)
    col1.text_input(
        "Symbol (Anzeige)",
        value=existing.get("symbol", "") if existing else "",
        placeholder="z.B. NASDAQ:QQQ",
        key=f"f_symbol_{prefix}",
    )
    col2.text_input(
        "Symbol (Yahoo)",
        value=existing.get("symbol_yahoo", "") if existing else "",
        placeholder="z.B. QQQ",
        key=f"f_symyahoo_{prefix}",
    )
    col3.text_input(
        "Zeitrahmen",
        value=existing.get("timeframe", "") if existing else "",
        placeholder="z.B. 1 Stunde",
        key=f"f_tf_{prefix}",
    )

    st.text_input(
        "Typ",
        value=existing.get("typ", "") if existing else "",
        placeholder="z.B. Mean Reversion",
        key=f"f_typ_{prefix}",
    )

    st.text_area(
        "Beschreibung",
        value=existing.get("beschreibung", "") if existing else "",
        height=80,
        key=f"f_desc_{prefix}",
    )

    regeln_text = "\n".join(existing.get("regeln", [])) if existing else ""
    st.text_area(
        "Regeln (eine pro Zeile)",
        value=regeln_text,
        height=100,
        key=f"f_rules_{prefix}",
    )

    st.markdown("**Zeitregeln**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        entry_wd = st.selectbox(
            "Entry Wochentag",
            options=list(range(7)),
            format_func=lambda i: WEEKDAY_LABELS[i],
            index=existing.get("entry_weekday", 0) if existing else 0,
            key=f"f_ewd_{prefix}",
        )
    with col2:
        entry_t = st.time_input(
            "Entry Uhrzeit",
            value=pd.to_datetime(existing["entry_time"]).time() if existing and existing.get("entry_time") else time(9, 0),
            key=f"f_et_{prefix}",
        )
    with col3:
        exit_wd = st.selectbox(
            "Exit Wochentag",
            options=list(range(7)),
            format_func=lambda i: WEEKDAY_LABELS[i],
            index=existing.get("exit_weekday", 1) if existing else 1,
            key=f"f_xwd_{prefix}",
        )
    with col4:
        exit_t = st.time_input(
            "Exit Uhrzeit",
            value=pd.to_datetime(existing["exit_time"]).time() if existing and existing.get("exit_time") else time(22, 0),
            key=f"f_xt_{prefix}",
        )

    st.markdown("**Validierung (Live-Check)**")

    v_options = list(VALIDATION_TYPES.keys())
    v_default = existing.get("validation_type", "none") if existing else "none"
    v_idx = v_options.index(v_default) if v_default in v_options else 0

    v_type = st.selectbox(
        "Regel-Typ",
        options=v_options,
        format_func=lambda k: VALIDATION_TYPES[k],
        index=v_idx,
        key=f"f_vtype_{prefix}",
    )

    v_params = dict(existing.get("validation_params") or {}) if existing else {}

    if v_type in ("rsi_below", "rsi_above"):
        c1, c2 = st.columns(2)
        v_params["length"] = c1.number_input(
            "RSI-Laenge", min_value=1, max_value=50,
            value=int(v_params.get("length", 3)),
            key=f"f_vlen_{prefix}",
        )
        v_params["threshold"] = c2.number_input(
            "Schwelle", min_value=0.0, max_value=100.0,
            value=float(v_params.get("threshold", 18)),
            key=f"f_vth_{prefix}",
        )
    elif v_type == "close_below_prev":
        v_params["pct"] = st.number_input(
            "Mindest-Rueckgang (%)", min_value=0.1, max_value=20.0,
            value=float(v_params.get("pct", 1.0)), step=0.1,
            key=f"f_vpct_{prefix}",
        )
    elif v_type == "ibs_below":
        v_params["threshold"] = st.number_input(
            "IBS-Schwelle", min_value=0.0, max_value=1.0,
            value=float(v_params.get("threshold", 0.2)), step=0.05,
            key=f"f_vibs_{prefix}",
        )
    elif v_type == "sma_filter":
        c1, c2 = st.columns(2)
        v_params["length"] = c1.number_input(
            "SMA-Laenge", min_value=5, max_value=500,
            value=int(v_params.get("length", 200)),
            key=f"f_vsma_{prefix}",
        )
        v_params["direction"] = c2.selectbox(
            "Richtung", options=["above", "below"],
            index=0 if v_params.get("direction", "above") == "above" else 1,
            key=f"f_vdir_{prefix}",
        )
    elif v_type == "day_of_month":
        v_params["day_min"] = st.number_input(
            "Kalendertag minimum", min_value=1, max_value=31,
            value=int(v_params.get("day_min", 15)),
            key=f"f_vday_{prefix}",
        )

    auto_gen = st.toggle(
        "Automatisch im Kalender anlegen",
        value=existing.get("auto_generate", False) if existing else True,
        key=f"f_autogen_{prefix}",
    )

    st.text_area(
        "Pinescript-Code (optional)",
        value=existing.get("pine_code", "") if existing else "",
        height=120,
        key=f"f_pine_{prefix}",
    )

    uploaded = st.file_uploader(
        "Excel/CSV Performance-Report (optional)",
        type=["xlsx", "xls", "csv"],
        key=f"f_file_{prefix}",
    )

    if existing and existing.get("excel_path"):
        st.caption(f"Verknuepft: `{existing['excel_path']}`")

    col_save, col_cancel = st.columns([1, 1])
    save_clicked = col_save.button(
        "Speichern", type="primary", width="stretch",
        key=f"f_save_{prefix}",
    )
    cancel_clicked = col_cancel.button(
        "Abbrechen", width="stretch",
        key=f"f_cancel_{prefix}",
    )

    if save_clicked:
        name = _s(f"f_name_{prefix}").strip()
        if not name:
            st.error("Name ist erforderlich.")
            return

        excel_path = existing.get("excel_path") if existing else None
        if uploaded is not None:
            excel_path = save_uploaded_file(uploaded)

        regeln_raw = _s(f"f_rules_{prefix}")

        data = {
            "name": name,
            "symbol": _s(f"f_symbol_{prefix}").strip(),
            "symbol_yahoo": _s(f"f_symyahoo_{prefix}").strip(),
            "timeframe": _s(f"f_tf_{prefix}").strip(),
            "typ": _s(f"f_typ_{prefix}").strip(),
            "beschreibung": _s(f"f_desc_{prefix}").strip(),
            "regeln": [r.strip() for r in regeln_raw.split("\n") if r.strip()],
            "pine_code": _s(f"f_pine_{prefix}").strip(),
            "excel_path": excel_path,
            "entry_weekday": entry_wd,
            "entry_time": entry_t.isoformat(),
            "exit_weekday": exit_wd,
            "exit_time": exit_t.isoformat(),
            "validation_type": v_type,
            "validation_params": v_params,
            "auto_generate": auto_gen,
        }

        if is_new:
            ok, msg, _ = create_strategy(data)
        else:
            ok, msg = update_strategy(existing["id"], data)

        if ok:
            if is_new:
                st.session_state["show_new_form"] = False
            else:
                st.session_state[f"editing_{existing['id']}"] = False
            st.rerun()
        else:
            st.error(msg)

    if cancel_clicked:
        if is_new:
            st.session_state["show_new_form"] = False
        else:
            st.session_state[f"editing_{existing['id']}"] = False
        st.rerun()


def _render_card(strategy):
    sid = strategy["id"]
    expanded_key = f"expanded_{sid}"
    editing_key = f"editing_{sid}"

    if st.session_state.get(editing_key, False):
        with st.container(border=True):
            st.markdown(f"### Bearbeiten: {strategy.get('name', '')}")
            _strategy_form(existing=strategy, is_new=False)
        return

    expanded = st.session_state.get(expanded_key, False)
    excel_stats = load_excel_summary(strategy.get("excel_path", ""))

    with st.container(border=True):
        col_left, col_time, col_status, col_cagr, col_gear = st.columns([3, 2, 1, 1.2, 0.6])

        with col_left:
            st.markdown(f"#### {strategy.get('name', 'Ohne Namen')}")
            meta = []
            if strategy.get("symbol"):
                meta.append(f"`{strategy['symbol']}`")
            if strategy.get("timeframe"):
                meta.append(strategy["timeframe"])
            if strategy.get("typ"):
                meta.append(strategy["typ"])
            if meta:
                st.caption("  -  ".join(meta))

        with col_time:
            ewd = strategy.get("entry_weekday")
            xtd = strategy.get("exit_weekday")
            et = _format_time(strategy.get("entry_time"))
            xt = _format_time(strategy.get("exit_time"))
            if ewd is not None and xtd is not None:
                st.caption(
                    f"Zeit: **{WEEKDAY_LABELS[ewd]}** {et} -> "
                    f"**{WEEKDAY_LABELS[xtd]}** {xt}"
                )

        with col_status:
            if strategy.get("auto_generate"):
                v = validate_strategy(strategy, date.today())
                valid = v.get("valid")
                if valid is True:
                    st.markdown("🟢")
                elif valid is False:
                    st.markdown("🔴")
                else:
                    st.markdown("⚪")

        with col_cagr:
            if excel_stats.get("cagr") is not None:
                st.metric("CAGR", f"{excel_stats['cagr']:.2f} %")

        with col_gear:
            with st.popover("⚙️"):
                if st.button("Bearbeiten", width="stretch", key=f"edit_{sid}"):
                    st.session_state[editing_key] = True
                    st.rerun()
                if st.button("Loeschen", width="stretch", key=f"del_{sid}"):
                    ok, msg = delete_strategy(sid)
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)

        toggle_label = "Details ausblenden" if expanded else "Details anzeigen"
        if st.button(toggle_label, key=f"toggle_{sid}", width="stretch"):
            st.session_state[expanded_key] = not expanded
            st.rerun()

        if expanded:
            st.divider()

            if strategy.get("beschreibung"):
                st.markdown("**Beschreibung**")
                st.write(strategy["beschreibung"])

            if strategy.get("regeln"):
                st.markdown("**Regeln**")
                for r in strategy["regeln"]:
                    st.markdown(f"- {r}")

            st.markdown("**Live-Validierung (heute)**")
            v = validate_strategy(strategy, date.today())
            valid = v.get("valid")
            note = v.get("note", "")
            if valid is True:
                st.success(f"OK - {note}")
            elif valid is False:
                st.error(f"Ungueltig - {note}")
            else:
                st.info(f"Keine Aussage - {note}")

            if excel_stats.get("nettogewinn") is not None:
                st.markdown("**Performance (aus Excel)**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Net Profit", f"${excel_stats['nettogewinn']:,.0f}")
                c2.metric("Return", f"{excel_stats.get('nettogewinn_pct') or 0:.1f} %")
                c3.metric("CAGR", f"{excel_stats.get('cagr') or 0:.2f} %")
                c4.metric("Max DD", f"{excel_stats.get('max_dd') or 0:.2f} %")
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Trades", f"{int(excel_stats.get('trades') or 0)}")
                c6.metric("Win Rate", f"{excel_stats.get('win_rate') or 0:.1f} %")
                c7.metric("Profit Factor", f"{excel_stats.get('profit_factor') or 0:.2f}")
                c8.metric("Sharpe", f"{excel_stats.get('sharpe') or 0:.2f}")

            if strategy.get("pine_code"):
                with st.expander("Pinescript-Code"):
                    st.code(strategy["pine_code"], language="javascript")


def show_strategien():
    st.title("Strategien")
    st.write("Meine Handelsstrategien - Regeln, Zeiten, Code und Performance.")
    st.divider()

    ensure_seed_strategies()

    strategies = load_user_strategies()

    col_info, col_new = st.columns([5, 1.2])
    with col_info:
        st.caption(f"**{len(strategies)}** Strategien")
    with col_new:
        if st.button("Neue Strategie", type="primary", width="stretch"):
            st.session_state["show_new_form"] = True

    if st.session_state.get("show_new_form", False):
        with st.container(border=True):
            st.markdown("### Neue Strategie")
            _strategy_form(existing=None, is_new=True)
        st.divider()

    if not strategies:
        st.info("Noch keine Strategien.")
        return

    for s in strategies:
        _render_card(s)
