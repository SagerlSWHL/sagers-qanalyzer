import streamlit as st

# Sidebar importieren
from components.sidebar import show_sidebar

# Seiten importieren
from views.overview import show_overview
from views.analyzer import show_analyzer
from views.portfolio import show_portfolio


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


else:

    st.title(st.session_state["page"])

    st.write("Diese Seite wird noch entwickelt.")