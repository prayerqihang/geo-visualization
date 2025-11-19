import streamlit as st
import os
import warnings
from streamlit_lottie import st_lottie

from core.common import custom_sidebar_pages_order
from utils import load_lottie_file
from config.settings import ASSETS_ANIMATION_PATH

# 针对性处理 geopandas 的 numpy 版本不兼容的问题：忽略包含 "copy=False" 的 FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning, message=".*copy=False.*")

# 1. 定义全局页面配置
# layout: centered (default); wide
# initial_sidebar_state: auto (default); expanded; collapsed
st.set_page_config(
    page_title="地理可视化-App",
    page_icon=":earth_americas:",
    layout="wide"
)

# 2. 定义页面
# 注意一：必须在 entrypoint file 中定义页面，这样 page_link 函数才能找到这些页面
# 注意二：此处页面的其余参数可以不设置，page_link 函数中的参数优先级更高
st.Page(page="streamlit_app.py")
st.Page(page="pages/basic_info.py")
st.Page(page="pages/transport_network.py")

# 3. 渲染侧边栏
custom_sidebar_pages_order()

# 4. 渲染主页面
st.title("欢迎来到 地理可视化 App")

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
