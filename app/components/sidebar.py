"""
sidebar.py
----------
Erzeugt die Sidebar-Navigation des Sagers qAnalyzer.
"""

import streamlit as st


def show_sidebar():
    """
    Erstellt die Sidebar des Sagers qAnalyzer.
    """

    with st.sidebar:

        # -----------------------------------------------------
        # BRANDING
        # -----------------------------------------------------

        st.html(
            """
            <div style="
                margin-bottom: 32px;
                padding-top: 8px;
                text-align: center;
            ">

                <div style="
                    font-size: 34px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    line-height: 1.1;
                ">
                    Sagers
                </div>

                <div style="
                    font-size: 22px;
                    font-weight: 500;
                    color: #8b8b8b;
                    letter-spacing: 1.5px;
                    line-height: 1.2;
                    margin-top: 2px;
                ">
                    qAnalyzer
                </div>

                <div style="
                    margin: 18px auto 12px auto;
                    width: 70%;
                    height: 1px;
                    background-color: #333333;
                "></div>

                <div style="
                    font-size: 12px;
                    color: #777777;
                    letter-spacing: 3px;
                ">
                    SAGERS QUANT
                </div>

            </div>
            """
        )

        # -----------------------------------------------------
        # ANALYSE
        # -----------------------------------------------------

        st.markdown("### ANALYSE")

        if st.button("🏠  Overview", use_container_width=True):
            st.session_state["page"] = "Overview"

        if st.button("📊  Analyzer", use_container_width=True):
            st.session_state["page"] = "Analyzer"

        if st.button("📈  Portfolio", use_container_width=True):
            st.session_state["page"] = "Portfolio"

        if st.button("📉  Drawdown", use_container_width=True):
            st.session_state["page"] = "Drawdown"

        if st.button("💹  Trades", use_container_width=True):
            st.session_state["page"] = "Trades"

        if st.button("📅  Monthly", use_container_width=True):
            st.session_state["page"] = "Monthly"

        if st.button("📐  Statistics", use_container_width=True):
            st.session_state["page"] = "Statistics"

        if st.button("🔗  Correlation", use_container_width=True):
            st.session_state["page"] = "Correlation"

        # -----------------------------------------------------
        # RESEARCH
        # -----------------------------------------------------

        st.markdown("### RESEARCH")

        if st.button("🗄️  Daten", use_container_width=True):
            st.session_state["page"] = "Daten"

        if st.button("🧪  Backtesting", use_container_width=True):
            st.session_state["page"] = "Backtesting"

        if st.button("🎯  Strategien", use_container_width=True):
            st.session_state["page"] = "Strategien"

        # -----------------------------------------------------
        # LEARNING
        # -----------------------------------------------------

        st.markdown("### LEARNING")

        if st.button("📚  Grundlagen", use_container_width=True):
            st.session_state["page"] = "Grundlagen"

        if st.button("📐  Mathe", use_container_width=True):
            st.session_state["page"] = "Mathe"

        if st.button("🐍  Python & AI", use_container_width=True):
            st.session_state["page"] = "Python & AI"