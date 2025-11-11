import os
import streamlit as st
import json
import pandas as pd
import requests
import folium
import rasterio
import rasterio.mask
import geopandas as gpd
import numpy as np
from streamlit_folium import st_folium
from folium.plugins import HeatMap

from utils import custom_sidebar_pages_order
from config.settings import ASSETS_MAP_PATH, FOLIUM_MAP_TYPE, COLOR_TYPE, DATA_CITY_PATH


# @st.cache_data: Streamlit 提供的函数返回值缓存
# 简单来说，这个装饰器让函数保存自己的计算结果。当同一个函数第二次被相同的参数调用时，直接返回之前缓存的结果，而不是重新计算
@st.cache_data
def load_cities_info():
    """缓存加载 pca-code 和 adcode 数据"""
    pca_code_path = os.path.join(ASSETS_MAP_PATH, "pca-code.json")
    with open(file=pca_code_path, mode="r", encoding="utf-8") as f:
        data_list = json.load(f)

    adcode_path = os.path.join(ASSETS_MAP_PATH, "amap_adcode_citycode.xlsx")
    df = pd.read_excel(adcode_path)
    df.set_index("中文名", inplace=True)

    return data_list, df


def get_geojson(adcode, is_sub=False):
    """
        从阿里云 DataV 动态获取 GeoJSON 数据。
        - is_sub = False 仅获取当前 adcode 区域边界数据，不包含子区域边界。
        - is_sub = True 获取当前 adcode 区域边界数据，以及一级子区域边界。
    """
    if is_sub:
        url = f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json"
    else:
        url = f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except Exception as e:
        st.error(f"加载地图数据失败: {e}")
        return None


def plot_folium_map(
        adcode, sub_adcode, map_type, do_fill, fill_color, fill_opacity,
        edge_color, sub_edge_color, edge_width, sub_edge_width):
    """
        绘制地图：
        - 父级行政区 adcode (仅边界)
        - 子级行政区 sub_adcode (填充)
    """
    # 获取 GeoJSON
    parent_geojson = get_geojson(adcode, is_sub=True)
    child_geojson = get_geojson(sub_adcode, is_sub=False)

    m = folium.Map(tiles=map_type)

    parent_layer = folium.GeoJson(
        parent_geojson,
        style_function=lambda feature: {
            'fill': False,
            'color': edge_color,
            'weight': edge_width,
        }
    ).add_to(m)

    folium.GeoJson(
        child_geojson,
        style_function=lambda feature: {
            'fill': do_fill,
            'fillColor': fill_color,  # 填充颜色
            'fillOpacity': fill_opacity,  # 填充透明度
            'color': sub_edge_color,  # 边界颜色
            'weight': sub_edge_width  # 边界宽度
        }
    ).add_to(m)

    m.fit_bounds(parent_layer.get_bounds())
    return m


# 子页面配置
st.set_page_config(
    page_title="City",
    page_icon=":earth_americas:",
    layout="wide"
)

# 1. 渲染侧边栏
custom_sidebar_pages_order()

# 2. 渲染主页面——第一部分
st.title("Province-City-District Visualization")
st.divider()

data_list, df = load_cities_info()  # 加载数据

# 2.1. 数据区域选择框
st.markdown("##### 区域范围")

col1, col2, col3 = st.columns(3)
# --- 维度一：省 ---
with col1:
    province_names = [p["name"] for p in data_list]
    selected_province_name = st.selectbox("请选择省份（或直辖市）：", province_names)
selected_province_adcode = df.loc[selected_province_name, "adcode"]
selected_province_dict = next(
    p for p in data_list if p["name"] == selected_province_name)  # next: 从可迭代对象中返回第一个满足条件的元素

# --- 维度二：市 ---
with col2:
    city_names = [c["name"] for c in selected_province_dict["children"]]
    selected_city_name = st.selectbox("请选择城市：", city_names)
# 特殊处理四个直辖市
selected_city_adcode = None
if selected_province_name in ["北京市", "天津市", "上海市", "重庆市"]:
    selected_city_adcode = selected_province_adcode
else:
    try:
        selected_city_adcode = df.loc[selected_city_name, "adcode"]
    except KeyError:
        st.error(f"未找到 {selected_city_name} 对应的 adcode!")
        st.stop()  # 立刻停止当前脚本的执行

selected_city_dict = next(c for c in selected_province_dict["children"] if c["name"] == selected_city_name)

# --- 维度三：区 ---
with col3:
    district_names = [d["name"] for d in selected_city_dict["children"]]
    if not district_names:
        st.warning(f"城市 {selected_city_name} 下没有找到区/县信息！")
        st.stop()
    selected_district_name = st.selectbox("请选择区/县：", district_names)

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
st.markdown("##### 地图配置")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**底图样式**")
    # --- 底图类型 ---
    map_type = st.selectbox(
        "请选择底图类型：",
        options=list(FOLIUM_MAP_TYPE.keys()),
        index=0  # 默认使用 "街道图"
    )
    selected_map_type = FOLIUM_MAP_TYPE[map_type]

with col2:
    st.markdown("**填充样式**")
    # --- 是否填充 ---
    do_fill = st.checkbox("是否填充子行政区", value=True)
    # --- 填充颜色 ---
    fill_color = st.selectbox(
        "请选择子行政区地图填充色：",
        options=list(COLOR_TYPE.keys()),
        index=0  # 默认使用"灰色"
    )
    selected_fill_color = COLOR_TYPE[fill_color]
    # --- 填充透明度（0-1 之间，设计成滑动条的形式） ---
    fill_opacity = st.slider(
        "请选择填充透明度",
        min_value=0.1,
        max_value=1.0,
        value=0.4,  # 默认值
        step=0.05,
        disabled=(not do_fill)  # 核心：当不填充时，禁用此滑块
    )

with col3:
    st.markdown("**边界样式**")

    edge_color = st.selectbox(
        "请选择父行政区边界颜色：",
        options=list(COLOR_TYPE.keys()),
        index=0  # 默认使用"灰色"
    )
    selected_edge_color = COLOR_TYPE[edge_color]
    edge_width = st.slider(
        "请选择父行政区边界宽度",
        min_value=1.0,
        max_value=5.0,
        value=1.0,  # 默认值
        step=0.5
    )

    sub_edge_color = st.selectbox(
        "请选择子行政区边界颜色：",
        options=list(COLOR_TYPE.keys()),
        index=0  # 默认使用"灰色"
    )
    selected_sub_edge_color = COLOR_TYPE[sub_edge_color]
    sub_edge_width = st.slider(
        "请选择子行政区边界宽度",
        min_value=1.0,
        max_value=5.0,
        value=1.5,  # 默认值
        step=0.5
    )

# 2.2. 绘制 GeoJSON 数据
st.divider()
st.markdown("### 1. 地理位置信息")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"<h5 style='text-align: center;'>父行政区：全国 | 子行政区：{selected_province_name}</h5>",
        unsafe_allow_html=True
    )
    map1 = plot_folium_map(
        adcode=100000,  # 100000 代表中国
        sub_adcode=selected_province_adcode,
        map_type=selected_map_type,
        do_fill=do_fill,
        fill_color=selected_fill_color,
        fill_opacity=fill_opacity,
        edge_color=selected_edge_color,
        sub_edge_color=selected_sub_edge_color,
        edge_width=edge_width,
        sub_edge_width=sub_edge_width
    )
    if map1:
        st_folium(map1, key="map-country2province", height=400)

with col2:
    st.markdown(
        f"<h5 style='text-align: center;'>父行政区：{selected_province_name} | 子行政区：{selected_city_name}</h5>",
        unsafe_allow_html=True
    )
    map2 = plot_folium_map(
        adcode=selected_province_adcode,
        sub_adcode=selected_city_adcode,
        map_type=selected_map_type,
        do_fill=do_fill,
        fill_color=selected_fill_color,
        fill_opacity=fill_opacity,
        edge_color=selected_edge_color,
        sub_edge_color=selected_sub_edge_color,
        edge_width=edge_width,
        sub_edge_width=sub_edge_width
    )
    if map2:
        st_folium(map2, key="map-province2city", height=400)

with col3:
    st.markdown(
        f"<h5 style='text-align: center;'>父行政区：{selected_city_name} | 子行政区：{selected_district_name}</h5>",
        unsafe_allow_html=True
    )
    map3 = plot_folium_map(
        adcode=selected_city_adcode,
        sub_adcode=selected_district_adcode,
        map_type=selected_map_type,
        do_fill=do_fill,
        fill_color=selected_fill_color,
        fill_opacity=fill_opacity,
        edge_color=selected_edge_color,
        sub_edge_color=selected_sub_edge_color,
        edge_width=edge_width,
        sub_edge_width=sub_edge_width
    )
    if map3:
        st_folium(map3, key="map-city2district", height=400)

# 3. 渲染主页面——第二部分
st.divider()
st.markdown("### 2. 人口信息")


def get_data_from_tif(adcode, tif_filepath):
    """
    使用 GeoJSON 字典从 GeoTIFF 文件中裁剪数据。
    Returns:
        list: 一个列表，格式为 [[lat, lon, population], ...]
    """

    # --- 步骤 1: 加载 GeoJSON 形状 ---
    geojson_data_dict = get_geojson(adcode, is_sub=False)
    features = geojson_data_dict['features']
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")  # WorldPop 通常使用 'EPSG:4326' (WGS84)

    # --- 步骤 2: 打开 TIF 文件 ---
    with rasterio.open(tif_filepath) as src:
        # --- 步骤 3: 统一坐标系 ---
        if gdf.crs != src.crs:
            print(f"转换坐标系：从 {gdf.crs} 转换为 {src.crs}")
            gdf = gdf.to_crs(src.crs)
        geometries = gdf.geometry

        # --- 步骤 4: 裁剪 ---
        try:
            # clipped_array：3D numpy 数组 (bands, height, width)。brands 为波段，此处包含人口信息；height/width 表示像素数量
            # clipped_transform：包含 6 个浮点数的数学变换矩阵，用于计算返回矩阵中每一个位置的实际经纬度
            clipped_array, clipped_transform = rasterio.mask.mask(
                src,  # tif 数据
                geometries,  # 裁剪的目标形状
                crop=True,  # True：返回恰好能覆盖目标形状的 tif 像素矩阵；False：返回全量 tif 像素矩阵（目标区域有数据，非目标区域填充 nodata 值）
                all_touched=True,  # True：目标形状边界触及的像素均保留；False：只有当一个像素的中心点完全在目标形状内部时，才保留
                nodata=np.nan  # 和 crop=True 协同工作，将 TIF 的 nodata 值设为 NaN
            )
        except ValueError as e:
            print(f"裁剪失败: {e}")
            print("一个常见原因是 GeoJSON 边界超出了 TIF 文件的范围。")
            return []

        # --- 步骤 5: 处理裁剪后的数据 ---
        clipped_array = clipped_array[0]
        heatmap_data = []
        for r in range(clipped_array.shape[0]):
            for c in range(clipped_array.shape[1]):
                population = clipped_array[r, c]
                # 过滤掉无数据 (NaN) 和人口为 0 的点
                if not np.isnan(population) and population > 0:
                    # 将像素坐标 (c, r) 转换为经纬度 (lon, lat)
                    lon, lat = clipped_transform * (c, r)
                    heatmap_data.append([float(lat), float(lon), float(
                        population)])  # 需要将 numpy 的类型转换为 python 内置类型，否则 st_folium 在 JSON 序列化时无法识别
        return heatmap_data


tif_filepath = os.path.join(DATA_CITY_PATH, "chn_pop_2020_CN_100m_R2025A_v1.tif")
heatmap_data = get_data_from_tif(selected_district_adcode, tif_filepath)

m = folium.Map(tiles=selected_map_type)
heatmap_layer = HeatMap(
    heatmap_data,
    name='WorldPop 人口热力图',  # 图层名称
    radius=7,  # 热力点半径 (可调整)
    blur=5,  # 模糊度 (可调整)
    max_zoom=10  # 在哪个缩放级别停止聚合
).add_to(m)
m.fit_bounds(heatmap_layer.get_bounds())
st_folium(m, key="map-district-population", height=400)

# 1. 明确人口数值的含义
# 2. 添加热力图图例
# 3. 规范化代码
# 4. 统计区总人口