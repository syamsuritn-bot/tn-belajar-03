import streamlit as st


dashboard_page = st.Page(
    "pages/0_Dashboard.py",
    title="Dashboard Analitik",
    default=True,
)
map_page = st.Page(
    "pages/1_Peta_IKPA_Indonesia.py",
)

navigation = st.navigation([dashboard_page, map_page])
navigation.run()
