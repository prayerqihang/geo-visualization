import streamlit as st


def custom_sidebar_pages_order():
    """自定义渲染侧边栏页面"""
    st.sidebar.markdown("# :streamlit: App 导航")

    st.sidebar.divider()

    st.sidebar.page_link(page="streamlit_app.py", label="主页", icon="🌟")
    st.sidebar.page_link(page="pages/basic_info.py", label="基本信息", icon="🏠")
    st.sidebar.page_link(page="pages/transport_network.py", label="交通网络", icon="🚗")

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

