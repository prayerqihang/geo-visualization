import os

import streamlit as st
import json
import pandas as pd

from utils import custom_sidebar_pages_order
from config.settings import ASSETS_MAP_PATH


# @st.cache_data: Streamlit 提供的函数返回值缓存
# 简单来说，这个装饰器让函数保存自己的计算结果。当同一个函数第二次被相同的参数调用时，直接返回之前缓存的结果，而不是重新计算
@st.cache_data
def load_cities_info():
    pca_code_path = os.path.join(ASSETS_MAP_PATH, "pca-code.json")
    with open(file=pca_code_path, mode="r", encoding="utf-8") as f:
        data_list = json.load(f)

    adcode_path = os.path.join(ASSETS_MAP_PATH, "amap_adcode_citycode.xlsx")
    df = pd.read_excel(adcode_path)

    return data_list, df


# 1. 渲染侧边栏
custom_sidebar_pages_order()

# 2. 渲染主页面
st.title("City Visualization")

data_list, df = load_cities_info()  # 加载数据

# --- 维度一：省 ---
province_names = [p["name"] for p in data_list]
selected_province_name = st.selectbox("选择省份（或直辖市）：", province_names)
# --- 维度二：市 ---
selected_city_name = None
selected_province_dict = None
if selected_province_name:
    selected_province_dict = next(
        p for p in data_list if p["name"] == selected_province_name)  # next: 从可迭代对象中返回第一个满足条件的元素
    city_names = [c["name"] for c in selected_province_dict["children"]]
    selected_city_name = st.selectbox("选择城市：", city_names)
# --- 维度三：区 ---
if selected_city_name:
    # 找到被选中的城市对象
    selected_city_dict = next(c for c in selected_province_dict["children"] if c["name"] == selected_city_name)
    district_names = [d["name"] for d in selected_city_dict["children"]]
    selected_district_name = st.selectbox("选择区/县：", district_names)
