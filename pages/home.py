import os
import streamlit as st
from streamlit_lottie import st_lottie
from utils import load_lottie_file
from config.settings import ASSETS_PATH

st.title("Welcome to Geo-visualization")

local_lottie_path = os.path.join(ASSETS_PATH, "home_page_global_map.json")
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
