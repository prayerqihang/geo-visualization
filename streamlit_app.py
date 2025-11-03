import streamlit as st

# layout: centered (default); wide
# initial_sidebar_state: auto (default); expanded; collapsed
st.set_page_config(
    page_title="Geospatial App",
    page_icon=":earth_americas:",
    layout="wide",
    initial_sidebar_state="auto"
)

st.sidebar.markdown("# :streamlit: App Navigation")

home_page = st.Page("pages/home.py", title="Home", icon="⭐️")
city_page = st.Page("pages/city.py", title="City", icon="🏠")
bus_page = st.Page("pages/bus.py", title="Bus Network", icon="🚌")
metro_page = st.Page("pages/metro.py", title="Metro Network", icon="🚊")
car_page = st.Page("pages/car.py", title="Car Network", icon="🚗")

page = st.navigation([home_page, bus_page, metro_page, car_page])

st.sidebar.markdown("## About")
st.sidebar.info(
    """
    - **Web App URL:** [localhost](http://10.203.193.41:8501)
    - **GitHub repository:** [github.com/giswqs/streamlit-geospatial](https://github.com/giswqs/streamlit-geospatial)
    """
)
st.sidebar.markdown("## Contact")
st.sidebar.write("Email: 220233460@seu.edu.cn")

page.run()
