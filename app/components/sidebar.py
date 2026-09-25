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
                margin-bottom: 36px;
                padding-top: 10px;
                text-align: center;
            ">

                <div style="
                    font-size: 42px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    line-height: 1.1;
                ">
                    Sagers
                </div>

                <div style="
                    font-size: 26px;
                    font-weight: 500;
                    color: #8b8b8b;
                    letter-spacing: 1.8px;
                    line-height: 1.2;
                    margin-top: 4px;
                ">
                    qAnalyzer
                </div>

                <div style="
                    margin: 22px auto 14px auto;
                    width: 75%;
                    height: 1px;
                    background-color: #333333;
                "></div>

                <div style="
                    font-size: 13px;
                    color: #888888;
                    letter-spacing: 3.5px;
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

        if st.button("🏠  Overview", width="stretch"):
            st.session_state["page"] = "Overview"

        if st.button("📊  Analyzer", width="stretch"):
            st.session_state["page"] = "Analyzer"

        if st.button("📈  Portfolio", width="stretch"):
            st.session_state["page"] = "Portfolio"

        
        if st.button("📉  Drawdown", width="stretch"):
            st.session_state["page"] = "Drawdown"
        
        if st.button("💹  Trades", width="stretch"):
            st.session_state["page"] = "Trades"
        """
        if st.button("📅  Monthly", width="stretch"):
            st.session_state["page"] = "Monthly"

        if st.button("📐  Statistics", width="stretch"):
            st.session_state["page"] = "Statistics"
        """
        if st.button("🔗  Correlation", width="stretch"):
            st.session_state["page"] = "Correlation"
        

        # -----------------------------------------------------
        # RESEARCH
        # -----------------------------------------------------

        st.markdown("### RESEARCH")

        if st.button("🗄️  Daten", width="stretch"):
            st.session_state["page"] = "Daten"

        if st.button("🧪  Backtesting", width="stretch"):
            st.session_state["page"] = "Backtesting"

        if st.button("🎯  Strategien", width="stretch"):
            st.session_state["page"] = "Strategien"

        # -----------------------------------------------------
        # LEARNING
        # -----------------------------------------------------

        st.markdown("### LEARNING")

        if st.button("📚  Grundlagen", width="stretch"):
            st.session_state["page"] = "Grundlagen"

        if st.button("📐  Mathe", width="stretch"):
            st.session_state["page"] = "Mathe"

        if st.button("🐍  Python & AI", width="stretch"):
            st.session_state["page"] = "Python & AI"


        # -----------------------------------------------------
        # ABOUT / VERSION
        # -----------------------------------------------------

        st.markdown("---")

        st.markdown(
            """
            <div style="
                text-align: center;
                font-size: 13px;
                color: #888;
                line-height: 1.7;
                padding-top: 12px;
                padding-bottom: 8px;
            ">
                <strong style="color: #bbb; font-size: 14px; letter-spacing: 1px;">
                    Sagers qAnalyzer
                </strong>
                <br>
                <span style="font-size: 12px; color: #777;">
                    Version 0.1 · 2026
                </span>
                <br>
                <span style="font-size: 12px; color: #666;">
                    by Leon Sager
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )