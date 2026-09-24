import streamlit as st


def show_overview():
    """
    Zeigt die Startseite des Sagers qAnalyzer.
    """

    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------

    st.title("Overview")

    st.write(
        "Portfolio & Strategy Analysis"
    )

    st.divider()

    # ---------------------------------------------------------
    # KPI-KARTEN
    # ---------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Net Profit",
            value="$0.00"
        )

    with col2:
        st.metric(
            label="Return",
            value="0.00%"
        )

    with col3:
        st.metric(
            label="Max Drawdown",
            value="0.00%"
        )

    with col4:
        st.metric(
            label="Sharpe Ratio",
            value="0.00"
        )

    st.divider()

    # ---------------------------------------------------------
    # EQUITY CURVE
    # ---------------------------------------------------------

    st.subheader("Equity Curve")

    st.info(
        "Noch keine Daten geladen. "
        "Die Equity Curve wird später automatisch "
        "aus den importierten Trading-Daten erstellt."
    )

    # ---------------------------------------------------------
    # RECENT ANALYSIS
    # ---------------------------------------------------------

    st.subheader("Recent Analysis")

    st.write(
        "Hier werden später die zuletzt analysierten "
        "Strategien und Portfolios angezeigt."
    )