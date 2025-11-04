import streamlit as st


def custom_sidebar_pages_order():
    """自定义渲染侧边栏页面"""
    st.sidebar.markdown("# :streamlit: App Navigation")

    st.sidebar.divider()

    st.sidebar.page_link(page="streamlit_app.py", label="Home", icon="🌟")
    st.sidebar.page_link(page="pages/city.py", label="City", icon="🏠")
    st.sidebar.page_link(page="pages/bus.py", label="Bus Network", icon="🚌")
    st.sidebar.page_link(page="pages/metro.py", label="Metro Network", icon="🚊")
    st.sidebar.page_link(page="pages/car.py", label="Car Network", icon="🚗")

    st.sidebar.divider()

    st.sidebar.markdown("## About")
    st.sidebar.info(
        """
        - **Web App URL:** [localhost](http://10.203.193.41:8501)
        - **GitHub repository:** [github.com/prayerqihang/geo-visualization](https://github.com/prayerqihang/geo-visualization)
        """
    )
    st.sidebar.markdown("## Contact")
    st.sidebar.write("Email: 220233460@seu.edu.cn")

