import streamlit as st

# Sidebar importieren
from components.sidebar import show_sidebar

# Seiten importieren
from views.overview import show_overview
from views.analyzer import show_analyzer
from views.portfolio import show_portfolio
from views.correlation import show_correlation
from views.drawdown import show_drawdown
from views.trades import show_trades



# ---------------------------------------------------------
# STREAMLIT KONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Sagers qAnalyzer",
    page_icon="📊",
    layout="wide"
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

show_sidebar()


# ---------------------------------------------------------
# STANDARDSEITE
# ---------------------------------------------------------

if "page" not in st.session_state:
    st.session_state["page"] = "Overview"


# ---------------------------------------------------------
# SEITENNAVIGATION
# ---------------------------------------------------------

if st.session_state["page"] == "Overview":

    show_overview()


elif st.session_state["page"] == "Analyzer":

    show_analyzer()

elif st.session_state["page"] == "Portfolio":

    show_portfolio()

elif st.session_state["page"] == "Correlation":
    show_correlation()

elif st.session_state["page"] == "Drawdown":
    show_drawdown()

elif st.session_state["page"] == "Trades":
    show_trades()

else:

    st.title(st.session_state["page"])

    st.write("Diese Seite wird noch entwickelt.")