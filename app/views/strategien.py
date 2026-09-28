"""
strategien.py
-------------
Strategie-Bibliothek mit CRUD-Funktionen.

  - ➕ Plus-Button oben: neue Strategie
  - 🗂️ Karten collapsed: Name + CAGR
  - Klick auf Karte: expandiert
  - ⚙️ Zahnrad: bearbeiten
  - 🗑️ Löschen-Button
"""

import pandas as pd
import streamlit as st

from core.strategies_store import (
    add_strategy,
    delete_strategy,
    load_all,
    load_excel_summary,
    save_uploaded_file,
    update_strategy,
)


# =========================================================
# FORMULAR (für Neu + Edit)
# =========================================================

def _strategy_form(existing: dict | None = None, is_new: bool = True):
    """Formular zum Anlegen oder Bearbeiten einer Strategie."""

    prefix = "new" if is_new else existing["id"]

    name = st.text_input(
        "Name",
        value=existing.get("name", "") if existing else "",
        key=f"f_name_{prefix}",
    )

    col1, col2, col3 = st.columns(3)
    symbol = col1.text_input(
        "Symbol",
        value=existing.get("symbol", "") if existing else "",
        placeholder="z.B. NASDAQ:QQQ",
        key=f"f_symbol_{prefix}",
    )
    timeframe = col2.text_input(
        "Zeitrahmen",
        value=existing.get("timeframe", "") if existing else "",
        placeholder="z.B. 1 Stunde, 1 Tag",
        key=f"f_tf_{prefix}",
    )
    typ = col3.text_input(
        "Typ",
        value=existing.get("typ", "") if existing else "",
        placeholder="z.B. Mean Reversion",
        key=f"f_typ_{prefix}",
    )

    beschreibung = st.text_area(
        "Beschreibung",
        value=existing.get("beschreibung", "") if existing else "",
        height=80,
        key=f"f_desc_{prefix}",
    )

    # Regeln (mehrzeilig)
    regeln_text = "\n".join(existing.get("regeln", [])) if existing else ""
    regeln_raw = st.text_area(
        "Regeln (eine pro Zeile)",
        value=regeln_text,
        height=100,
        key=f"f_rules_{prefix}",
    )
    regeln = [r.strip() for r in regeln_raw.split("\n") if r.strip()]

    pine_code = st.text_area(
        "Pinescript-Code (optional)",
        value=existing.get("pine_code", "") if existing else "",
        height=150,
        key=f"f_pine_{prefix}",
    )

    uploaded = st.file_uploader(
        "Performance-Datei (Excel oder CSV)",
        type=["xlsx", "xls", "csv"],
        key=f"f_file_{prefix}",
    )

    if existing and existing.get("excel_path"):
        st.caption(f"Aktuell verknüpft: `{existing['excel_path']}`")

    # Speichern / Abbrechen
    col_save, col_cancel = st.columns([1, 1])

    with col_save:
        save_clicked = st.button(
            "💾  Speichern",
            type="primary",
            width="stretch",
            key=f"f_save_{prefix}",
        )

    with col_cancel:
        cancel_clicked = st.button(
            "Abbrechen",
            width="stretch",
            key=f"f_cancel_{prefix}",
        )

    # ---------- Speichern ----------
    if save_clicked:

        if not name.strip():
            st.error("Name ist erforderlich.")
            return

        excel_path = existing.get("excel_path") if existing else None

        if uploaded is not None:
            excel_path = save_uploaded_file(uploaded)

        data = {
            "name": name.strip(),
            "symbol": symbol.strip(),
            "timeframe": timeframe.strip(),
            "typ": typ.strip(),
            "beschreibung": beschreibung.strip(),
            "regeln": regeln,
            "pine_code": pine_code.strip(),
            "excel_path": excel_path,
        }

        if is_new:
            add_strategy(data)
        else:
            update_strategy(existing["id"], data)

        # State zurücksetzen
        if is_new:
            st.session_state["show_new_form"] = False
        else:
            st.session_state[f"editing_{existing['id']}"] = False

        st.rerun()

    # ---------- Abbrechen ----------
    if cancel_clicked:
        if is_new:
            st.session_state["show_new_form"] = False
        else:
            st.session_state[f"editing_{existing['id']}"] = False
        st.rerun()


# =========================================================
# KARTE
# =========================================================

def _render_card(strategy: dict):
    """Rendert eine Strategie-Karte."""

    sid = strategy["id"]
    expanded_key = f"expanded_{sid}"
    editing_key = f"editing_{sid}"

    # Edit-Modus → Formular
    if st.session_state.get(editing_key, False):
        with st.container(border=True):
            st.markdown(f"### ✏️  {strategy.get('name', 'Ohne Namen')} bearbeiten")
            _strategy_form(existing=strategy, is_new=False)
        return

    expanded = st.session_state.get(expanded_key, False)

    # Kennzahlen aus Excel
    excel_stats = load_excel_summary(strategy.get("excel_path", ""))

    # ---------- Kopfzeile (immer sichtbar) ----------
    with st.container(border=True):

        col_left, col_meta, col_cagr, col_gear = st.columns([4, 2, 1.2, 0.6])

        with col_left:
            st.markdown(f"#### {strategy.get('name', 'Ohne Namen')}")

            meta_parts = []
            if strategy.get("symbol"):
                meta_parts.append(f"`{strategy['symbol']}`")
            if strategy.get("timeframe"):
                meta_parts.append(strategy["timeframe"])
            if strategy.get("typ"):
                meta_parts.append(strategy["typ"])
            if meta_parts:
                st.caption("  ·  ".join(meta_parts))

        with col_meta:
            # Platzhalter, damit Zahnrad rechts bleibt
            pass

        with col_cagr:
            if excel_stats.get("cagr") is not None:
                st.metric("CAGR", f"{excel_stats['cagr']:.2f} %")

        with col_gear:
            with st.popover("⚙️", use_container_width=False):
                st.markdown("**Aktionen**")
                if st.button("✏️  Bearbeiten", width="stretch", key=f"edit_{sid}"):
                    st.session_state[editing_key] = True
                    st.rerun()
                if st.button("🗑️  Löschen", width="stretch", key=f"del_{sid}"):
                    delete_strategy(sid)
                    st.rerun()

        # ---------- Toggle-Button für Details ----------
        toggle_label = (
            "▲  Details ausblenden" if expanded else "▼  Details anzeigen"
        )
        if st.button(toggle_label, key=f"toggle_{sid}", width="stretch"):
            st.session_state[expanded_key] = not expanded
            st.rerun()

        # ---------- Detailbereich ----------
        if expanded:
            st.divider()

            # Beschreibung
            if strategy.get("beschreibung"):
                st.markdown("**Beschreibung**")
                st.write(strategy["beschreibung"])

            # Regeln
            if strategy.get("regeln"):
                st.markdown("**Regeln**")
                for r in strategy["regeln"]:
                    st.markdown(f"- {r}")

            # Excel-Kennzahlen
            if excel_stats.get("nettogewinn") is not None:
                st.markdown("**Performance (aus Excel)**")

                # Zeile 1 – Profit & Risk
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(
                    "Net Profit",
                    f"${excel_stats['nettogewinn']:,.0f}",
                )
                c2.metric(
                    "Return",
                    f"{excel_stats['nettogewinn_pct']:.1f} %"
                    if excel_stats.get("nettogewinn_pct") is not None
                    else "—",
                )
                c3.metric(
                    "CAGR",
                    f"{excel_stats['cagr']:.2f} %"
                    if excel_stats.get("cagr") is not None
                    else "—",
                )
                c4.metric(
                    "Max DD",
                    f"{excel_stats['max_dd']:.2f} %"
                    if excel_stats.get("max_dd") is not None
                    else "—",
                    help="Intraday (wie TradingView). Close-to-Close: "
                    + (
                        f"{excel_stats['max_dd_close']:.2f} %"
                        if excel_stats.get("max_dd_close") is not None
                        else "—"
                    ),
                )

                # Zeile 2 – Trade-Stats
                c5, c6, c7, c8 = st.columns(4)
                c5.metric(
                    "Trades",
                    f"{int(excel_stats['trades'])}"
                    if excel_stats.get("trades") is not None
                    else "—",
                )
                c6.metric(
                    "Win Rate",
                    f"{excel_stats['win_rate']:.1f} %"
                    if excel_stats.get("win_rate") is not None
                    else "—",
                )
                c7.metric(
                    "Profit Factor",
                    f"{excel_stats['profit_factor']:.2f}"
                    if excel_stats.get("profit_factor") is not None
                    else "—",
                )
                c8.metric(
                    "Sharpe",
                    f"{excel_stats['sharpe']:.2f}"
                    if excel_stats.get("sharpe") is not None
                    else "—",
                )

            # Pinescript
            if strategy.get("pine_code"):
                with st.expander("📜  Pinescript-Code"):
                    st.code(strategy["pine_code"], language="javascript")


# =========================================================
# HAUPTFUNKTION
# =========================================================

def show_strategien():
    """Zeigt die Strategie-Bibliothek."""

    st.title("Strategien")
    st.write("Meine Handelsstrategien – Regeln, Code und Performance.")
    st.divider()

    # ---------- Top-Bar mit + Button ----------
    col_info, col_new = st.columns([5, 1.2])

    with col_info:
        strategies = load_all()
        st.caption(f"**{len(strategies)}** Strategien in der Bibliothek")

    with col_new:
        if st.button("➕  Neue Strategie", type="primary", width="stretch"):
            st.session_state["show_new_form"] = True

    # ---------- Neues-Strategie-Formular ----------
    if st.session_state.get("show_new_form", False):
        with st.container(border=True):
            st.markdown("### ➕  Neue Strategie anlegen")
            _strategy_form(existing=None, is_new=True)
        st.divider()

    # ---------- Karten ----------
    if not strategies:
        st.info("Noch keine Strategien. Klicke auf **➕ Neue Strategie**.")
        return

    for s in strategies:
        _render_card(s)