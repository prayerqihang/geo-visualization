import os
import streamlit as st
import json
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

from utils import custom_sidebar_pages_order
from config.settings import ASSETS_MAP_PATH, FOLIUM_MAP_TYPE


# @st.cache_data: Streamlit 提供的函数返回值缓存
# 简单来说，这个装饰器让函数保存自己的计算结果。当同一个函数第二次被相同的参数调用时，直接返回之前缓存的结果，而不是重新计算
@st.cache_data
def load_cities_info():
    pca_code_path = os.path.join(ASSETS_MAP_PATH, "pca-code.json")
    with open(file=pca_code_path, mode="r", encoding="utf-8") as f:
        data_list = json.load(f)

    adcode_path = os.path.join(ASSETS_MAP_PATH, "amap_adcode_citycode.xlsx")
    df = pd.read_excel(adcode_path)
    df.set_index("中文名", inplace=True)

    return data_list, df


def get_geojson(adcode):
    """从阿里云 DataV 动态获取 GeoJSON"""
    url = f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except Exception as e:
        st.error(f"加载地图数据失败: {e}")
        return None


# 子页面配置
st.set_page_config(
    page_title="City",
    page_icon=":earth_americas:",
    layout="wide"
)

# 1. 渲染侧边栏
custom_sidebar_pages_order()

# 2. 渲染主页面
st.title("City Visualization")

data_list, df = load_cities_info()  # 加载数据

# 2.1. 数据区域选择框
st.header("1. 确定可视化范围：")
# --- 维度一：省 ---
province_names = [p["name"] for p in data_list]
selected_province_name = st.selectbox("选择省份（或直辖市）：", province_names)
selected_province_adcode = df.loc[selected_province_name, "adcode"]
selected_province_dict = next(
    p for p in data_list if p["name"] == selected_province_name)  # next: 从可迭代对象中返回第一个满足条件的元素

# --- 维度二：市 ---
city_names = [c["name"] for c in selected_province_dict["children"]]
selected_city_name = st.selectbox("选择城市：", city_names)
# 特殊处理四个直辖市
selected_city_adcode = None
if selected_province_name in ["北京市", "天津市", "上海市", "重庆市"]:
    selected_city_adcode = selected_province_adcode
else:
    try:
        selected_city_adcode = df.loc[selected_city_name, "adcode"]
    except KeyError:
        st.error(f"未找到 {selected_city_name} 对应的 adcode!")
        st.stop()  #

selected_city_dict = next(c for c in selected_province_dict["children"] if c["name"] == selected_city_name)

# --- 维度三：区 ---
district_names = [d["name"] for d in selected_city_dict["children"]]
if not district_names:
    st.warning(f"城市 {selected_city_name} 下没有找到区/县信息！")
    st.stop()

selected_district_name = st.selectbox("选择区/县：", district_names)
selected_district_adcode = None
try:
    selected_district_adcode = df.loc[selected_district_name, "adcode"]
except KeyError:
    st.error(f"未找到 {selected_district_name} 对应的 adcode!")
    st.stop()

# 处理 amap_adcode_citycode.xlsx 中的重名区域
if isinstance(selected_district_adcode, pd.DataFrame) or isinstance(selected_district_adcode, pd.Series):
    prefix = str(selected_city_adcode)[:3]
    count = 0
    for name, adcode in selected_district_adcode.items():
        if str(adcode).startswith(prefix):
            selected_district_adcode = adcode
            count += 1
    if count != 1:
        st.warning("展示的地图信息可能存在错误！详细信息：存在重名区域未被区分，adcode 可能错误。")

if selected_province_adcode is None or selected_city_adcode is None or selected_district_adcode is None:
    st.error(f"省份/城市/区域对应 adcode 数据错误！")


# 2.2. 可视化选择框
st.header("2. 配置地图选项")
# --- 底图类型 ---
selected_map_type = st.selectbox(
    "选择底图类型：",
    options=list(FOLIUM_MAP_TYPE.keys()),
    index=0  # 默认使用 "街道图"
)
selected_map_type = FOLIUM_MAP_TYPE[selected_map_type]
# --- 是否填充 ---
do_fill = st.checkbox("是否填充区域", value=True)
# --- 填充透明度（0-1 之间，设计成滑动条的形式） ---
fill_opacity = st.slider(
    "填充透明度",
    min_value=0.0,
    max_value=1.0,
    value=0.4,  # 默认值
    step=0.05,
    disabled=(not do_fill)  # 核心：当不填充时，禁用此滑块
)

# 2.2. 绘制 GeoJSON 数据
st.header("3. 可视化")
geojson_data = get_geojson(selected_district_adcode)
if geojson_data:
    st.subheader(f"{selected_district_name} 的地图边界")

    # 1. 创建一个 Folium 地图实例
    m = folium.Map(tiles=selected_map_type)

    # 2. 将 GeoJSON 数据添加为地图上的一个图层
    geojson_layer = folium.GeoJson(
        geojson_data,
        style_function=lambda feature: {
            'fill': do_fill,
            'fillColor': '#FF0000',  # 填充颜色
            'color': 'black',  # 边框颜色
            'weight': 2,  # 边框宽度
            'fillOpacity': fill_opacity  # 填充透明度
        }
    ).add_to(m)

    m.fit_bounds(geojson_layer.get_bounds())

    # 3. 使用 st_folium 在 Streamlit 页面上渲染地图
    st_folium(m, width=700, height=500)


# TODO 1. folium 的底图调试
# TODO 2. 页面排版调整