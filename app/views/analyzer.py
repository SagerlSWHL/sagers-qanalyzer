import streamlit as st


def show_analyzer():
    """
    Zeigt den Analyzer des Sagers qAnalyzer.
    """

    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------

    st.title("Analyzer")

    st.write(
        "Analyze individual trading strategies and trading results."
    )

    st.divider()

    # ---------------------------------------------------------
    # DATEI IMPORT
    # ---------------------------------------------------------

    st.subheader("Import Trading Data")

    uploaded_file = st.file_uploader(
        "CSV- oder Excel-Datei auswählen",
        type=["csv", "xlsx", "xls"]
    )

    # ---------------------------------------------------------
    # DATEI STATUS
    # ---------------------------------------------------------

    if uploaded_file is not None:

        st.success(
            f"Datei geladen: {uploaded_file.name}"
        )

        st.write(
            "Die Datei wird später automatisch analysiert."
        )

    else:

        st.info(
            "Noch keine Trading-Datei geladen."
        )

    st.divider()

    # ---------------------------------------------------------
    # ANALYSE BEREICHE
    # ---------------------------------------------------------

    st.subheader("Analysis")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Net Profit",
            value="$0.00"
        )

    with col2:
        st.metric(
            label="Win Rate",
            value="0.00%"
        )

    with col3:
        st.metric(
            label="Profit Factor",
            value="0.00"
        )

    with col4:
        st.metric(
            label="Max Drawdown",
            value="0.00%"
        )

    st.divider()

    # ---------------------------------------------------------
    # EQUITY CURVE
    # ---------------------------------------------------------

    st.subheader("Equity Curve")

    st.info(
        "Nach dem Import werden hier die "
        "Equity-Daten der Strategie dargestellt."
    )

    # ---------------------------------------------------------
    # TRADE ANALYSIS
    # ---------------------------------------------------------

    st.subheader("Trade Analysis")

    st.write(
        "Hier werden später die einzelnen Trades "
        "und deren Kennzahlen angezeigt."
    )