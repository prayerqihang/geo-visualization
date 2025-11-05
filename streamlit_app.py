import streamlit as st
import os
from streamlit_lottie import st_lottie

from config.settings import ASSETS_ANIMATION_PATH
from utils import custom_sidebar_pages_order, load_lottie_file

# 1. 定义全局页面配置
# layout: centered (default); wide
# initial_sidebar_state: auto (default); expanded; collapsed
st.set_page_config(
    page_title="Geo-visualization App",
    page_icon=":earth_americas:",
    layout="wide"
)

# 2. 定义页面
# 注意一：必须在 entrypoint file 中定义页面，这样 page_link 函数才能找到这些页面
# 注意二：此处页面的其余参数可以不设置，page_link 函数中的参数优先级更高
st.Page(page="streamlit_app.py")
st.Page(page="pages/city.py")
st.Page(page="pages/bus.py")
st.Page(page="pages/metro.py")
st.Page(page="pages/car.py")

# 3. 渲染侧边栏
custom_sidebar_pages_order()

# 4. 渲染主页面
st.title("Welcome to Geo-visualization App")

local_lottie_path = os.path.join(ASSETS_ANIMATION_PATH, "home_page_global_map.json")
lottie_json_data = load_lottie_file(local_lottie_path)
if lottie_json_data:
    st_lottie(
        lottie_json_data,
        speed=1,
        loop=True,
        quality="high",
        height=300,
        width=300,
        key="global_map_animation"
    )
