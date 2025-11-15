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
import pydeck as pdk
import altair as alt
import branca.colormap as cm
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


@st.cache_data
def get_population_from_tif(adcode, tif_filepath):
    """
    使用 GeoJSON 字典从 GeoTIFF 文件中裁剪数据，并返回详细的人口统计信息。
    Returns:
        dict: 包含人口列表、总和、面积、密度等信息的字典。
              如果裁剪失败，返回 None。
    """
    # --- 步骤 1: 加载 GeoJSON 形状 ---
    geojson_data_dict = get_geojson(adcode, is_sub=False)
    features = geojson_data_dict['features']
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")  # WorldPop 通常使用 'EPSG:4326' (WGS84)

    # --- 步骤 2: 计算面积 ---
    gdf_projected = gdf.to_crs(gdf.estimate_utm_crs())  # 自动选择一个合适的坐标系
    area_m2 = gdf_projected.area.sum()
    area_km2 = area_m2 / 1_000_000

    # --- 步骤 3: 裁剪 TIF 文件 ---
    with rasterio.open(tif_filepath) as src:
        # 统一坐标系
        if gdf.crs != src.crs:
            print(f"转换坐标系：从 {gdf.crs} 转换为 {src.crs}")
            gdf = gdf.to_crs(src.crs)
        geometries = gdf.geometry
        # 裁剪
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
            return []

        # --- 步骤 4: 处理裁剪后的数据 ---
        clipped_array = clipped_array[0]
        population_data = []  # 用于绘制热力图 / 3D 图
        population_values = []  # 用于统计人口信息
        for r in range(clipped_array.shape[0]):
            for c in range(clipped_array.shape[1]):
                population = clipped_array[r, c]
                # 过滤掉无数据 (NaN) 和人口为 0 的点
                if not np.isnan(population) and population > 0:
                    # 将像素坐标 (c, r) 转换为经纬度 (lon, lat)
                    lon, lat = clipped_transform * (c, r)
                    # 需要将 numpy 的类型转换为 python 内置类型，否则 st_folium 在 JSON 序列化时无法识别
                    # 注意：PyDeck 需要 [lon, lat, val]
                    population_data.append([float(lon), float(lat), float(population)])
                    population_values.append(float(population))

        return {
            "population_data": population_data,
            "population_values": population_values,
            "total_population": round(sum(population_values)),
            "area_km2": round(area_km2, 2),
            "population_density": round(sum(population_values) / area_km2, 2),
            "max_population_density": round(max(population_values), 2),
            "min_population_density": round(min(population_values), 2)
        }


@st.cache_data(show_spinner=False)
def get_city_population_from_tif(city_adcode, district_names, city_adcode_df, tif_filepath):
    """
    获取一个城市下所有区/县的人口和密度数据。
    Args:
        city_adcode (int): 选定城市的 adcode
        district_names (list): 选定城市的 'children' 列表
        city_adcode_df (pd.DataFrame): adcode 查找表
        tif_filepath (str): TIF 文件的路径
    Returns:
        pd.DataFrame: 包含 '区域', '总人口', '人口密度' 的 DataFrame
    """
    population_info_list = []
    # 使用 st.progress 来显示进度
    process_bar = st.progress(0, text=f"正在加载各区/县人口数据...")

    for i, district_name in enumerate(district_names):
        process_bar.progress((i + 1) / len(district_names), text=f"正在处理：{district_name} 的人口数据")

        district_adcode = city_adcode_df.loc[district_name, "adcode"]
        if isinstance(district_adcode, (pd.DataFrame, pd.Series)):
            prefix = str(city_adcode)[:3]
            count = 0
            for name, adcode in district_adcode.items():
                if str(adcode).startswith(prefix):
                    district_adcode = adcode
                    count += 1
            if count != 1:
                st.warning("展示的地图信息可能存在错误！详细信息：存在重名区域未被区分，adcode 可能错误。")

        data = get_population_from_tif(district_adcode, tif_filepath)

        population_info_list.append({
            "district": district_name,
            "total_population": data["total_population"],
            "population_density": data["population_density"],
            "area_km2": data["area_km2"]
        })

    # 完成后移除进度条
    process_bar.empty()
    return pd.DataFrame(population_info_list)


# 子页面配置
st.set_page_config(
    page_title="City",
    page_icon=":earth_americas:",
    layout="wide"
)

custom_sidebar_pages_order()

# 1. 渲染主页面——第一部分
st.title("Province-City-District Visualization")
st.divider()

st.markdown("### 1. 地理位置")
data_list, df = load_cities_info()  # 加载数据

# 1.1. 数据区域选择框
st.markdown("##### 区域范围")

col1, col2, col3 = st.columns(3)
# --- 维度一：省 ---
province_names = [p["name"] for p in data_list]
with col1:
    selected_province_name = st.selectbox("请选择省份（或直辖市）：", province_names)
selected_province_adcode = df.loc[selected_province_name, "adcode"]
selected_province_dict = next(
    p for p in data_list if p["name"] == selected_province_name)  # next: 从可迭代对象中返回第一个满足条件的元素

# --- 维度二：市 ---
city_names = [c["name"] for c in selected_province_dict["children"]]
with col2:
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
district_names = [d["name"] for d in selected_city_dict["children"]]
if not district_names:
    st.warning(f"城市 {selected_city_name} 下没有找到区/县信息！")
    st.stop()
with col3:
    selected_district_name = st.selectbox("请选择区/县：", district_names)

selected_district_adcode = None
try:
    selected_district_adcode = df.loc[selected_district_name, "adcode"]
except KeyError:
    st.error(f"未找到 {selected_district_name} 对应的 adcode!")
    st.stop()

# 处理 amap_adcode_citycode.xlsx 中的重名区域
if isinstance(selected_district_adcode, (pd.DataFrame, pd.Series)):
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

# 1.2. 可视化选择框
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

# 1.3. 绘制区域地理位置 Map
st.divider()
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

# 2. 渲染主页面——第二部分
st.divider()
st.markdown("### 2. 人口信息")
col1, col2 = st.columns(2)

# 2.1. 年份选择器
st.markdown("##### 年份选择")
selected_year = st.selectbox(
    "请选择人口数据年份：",
    options=[2020, 2021, 2022, 2023, 2024],
    index=0,  # 默认 2020 年
    label_visibility="collapsed"
)

tif_filename = f"chn_pop_{selected_year}_CN_100m_R2025A_v1.tif"
tif_filepath = os.path.join(DATA_CITY_PATH, tif_filename)
if not os.path.exists(tif_filepath):
    st.error(f"未找到 {selected_year} 年的人口数据文件：{tif_filename}")
    st.write(f"请检查路径：{tif_filepath}")
    st.stop()
else:
    st.success(f"已加载 {selected_year} 年人口数据。")

# 2.2. 人口信息展示
st.markdown("##### 信息维度选择")
view_selection = st.radio(
    "选择视图：",
    options=[
        f"{selected_city_name}: 市级人口信息概览",
        f"{selected_district_name}：区/县级人口信息概览"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

# 加载数据
df_city_population_info = get_city_population_from_tif(selected_city_adcode, district_names, df, tif_filepath)
st.divider()

if view_selection == f"{selected_city_name}: 市级人口信息概览":
    col1, col2, col3 = st.columns(3)
    brush = alt.selection_interval(encodings=['y'])  # 用于鼠标交互，用户可以在 y 轴方向选择数据
    # 总人口条形图
    with col1:
        st.markdown(
            f"<h5 style='text-align: center;'>{selected_city_name}各区域人口分布</h5>",
            unsafe_allow_html=True
        )
        chart = alt.Chart(df_city_population_info).mark_bar().encode(
            y=alt.Y("district:N", title="区域"),
            x=alt.X("total_population:Q", title="人口"),
            tooltip=["district", "total_population"],  # 鼠标悬停时展示的信息
            color=alt.condition(
                brush,
                if_true=alt.value("orange"),  # 选中时的颜色
                if_false=alt.value("steelblue")  # 默认颜色
            )
        ).properties(
        ).add_params(
            brush
        ).interactive()  # 允许缩放和滚动

        st.altair_chart(chart, use_container_width=True)

    with col2:
        st.markdown(
            f"<h5 style='text-align: center;'>{selected_city_name}各区域人口密度分布</h5>",
            unsafe_allow_html=True
        )
        chart = alt.Chart(df_city_population_info).mark_bar().encode(
            y=alt.Y("district:N", title="区域"),
            x=alt.X("population_density:Q", title="人口密度"),
            tooltip=["district", "population_density"],  # 鼠标悬停时展示的信息
            color=alt.condition(
                brush,
                if_true=alt.value("orange"),  # 选中时的颜色
                if_false=alt.value("steelblue")  # 默认颜色
            )
        ).properties(
        ).add_params(
            brush
        ).interactive()  # 允许缩放和滚动

        st.altair_chart(chart, use_container_width=True)

    with col3:
        st.markdown(
            f"<h5 style='text-align: center;'>{selected_city_name}各区域面积分布</h5>",
            unsafe_allow_html=True
        )
        chart = alt.Chart(df_city_population_info).mark_bar().encode(
            y=alt.Y("district:N", title="区域"),
            x=alt.X("area_km2:Q", title="面积（km²）"),
            tooltip=["district", "area_km2"],  # 鼠标悬停时展示的信息
            color=alt.condition(
                brush,
                if_true=alt.value("orange"),  # 选中时的颜色
                if_false=alt.value("steelblue")  # 默认颜色
            )
        ).properties(
        ).add_params(
            brush
        ).interactive()  # 允许缩放和滚动

        st.altair_chart(chart, use_container_width=True)

# 2.3. 区/县级人口空间分布
if view_selection == f"{selected_district_name}：区/县级人口信息概览":
    district_data = get_population_from_tif(selected_district_adcode, tif_filepath)

    # 基本指标
    pop_val = f"{district_data['total_population']:,}"
    density_val = f"{district_data['population_density']:,}"
    area_val = f"{district_data['area_km2']:,}"
    max_density_val = f"{district_data['max_population_density']:,}"
    min_density_val = f"{district_data['min_population_density']:,}"
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        with st.container(border=True):
            st.markdown(f"**总人口 (人): {pop_val}**")
    with col2:
        with st.container(border=True):
            st.markdown(f"**人口密度 (人/km²): {density_val}**")
    with col3:
        with st.container(border=True):
            st.markdown(f"**面积 (km²): {area_val}**")
    with col4:
        with st.container(border=True):
            st.markdown(f"**最高密度点 (人/100*100m²): {max_density_val}**")
    with col5:
        with st.container(border=True):
            st.markdown(f"**最低密度点 (人/100*100m²): {min_density_val}**")

    # 人口分布直方图
    st.markdown(
        f"<h5 style='text-align: center;'>{selected_district_name}网格人口分布直方图</h5>",
        unsafe_allow_html=True
    )
    df_hist = pd.DataFrame({
        'population': district_data["population_values"]
    })
    df_hist['bin'] = pd.cut(df_hist['population'], bins=50)  # 进行直方图分箱
    df_agg = df_hist.groupby('bin', observed=False).size().reset_index(name='count')

    df_agg['percent'] = df_agg['count'] / len(df_hist)  # 'percent' = 每个箱的数量 / 总数量
    df_agg['bin_start'] = df_agg['bin'].apply(lambda x: x.left)  # 用于 x 轴坐标排序
    df_agg['bin_label'] = df_agg['bin'].apply(
        lambda x: f"({np.ceil(x.left).astype(int)}, {np.ceil(x.right).astype(int)})")  # x 轴坐标 label

    brush = alt.selection_interval(encodings=['x'])
    chart = alt.Chart(df_agg).mark_bar().encode(
        y=alt.Y("percent:Q", title="网格数量比例", axis=alt.Axis(format="%")),  # 柱子顶部值（格式化为百分比）
        x=alt.X('bin_label:N', title="网格人口数量（人/100*100m²）", sort=alt.SortField("bin_start")),  # 需要指定排序列，否则会按照字典序
        tooltip=[
            alt.Tooltip('bin_label', title='人口范围'),
            alt.Tooltip('count:Q', title='网格单元数量'),
            alt.Tooltip('percent:Q', title='所占比例', format='.2%')
        ],
        opacity=alt.when(brush).then(alt.value(1)).otherwise(alt.value(0.6))  # 被选中时颜色深度增加
    ).add_params(
        brush
    ).interactive()

    line = alt.Chart(df_agg).mark_rule(color='firebrick').encode(
        y='mean(percent):Q',
        size=alt.SizeValue(3)  # 控制线条粗细
    ).transform_filter(
        brush
    )

    combined_chart = alt.layer(chart, line)  # 叠加两个图像
    st.altair_chart(combined_chart, use_container_width=True)

    col1, col2 = st.columns(2)
    # 人口分布热力图
    with col1:
        st.markdown(
            f"<h5 style='text-align: center;'>{selected_district_name}人口密度热力图</h5>",
            unsafe_allow_html=True
        )
        # 创建一个 Branca Colormap 对象
        population_values_district = [item[2] for item in district_data['population_data']]
        min_pop = np.percentile(population_values_district, 1)
        max_pop = np.percentile(population_values_district, 99)
        colormap = cm.linear.YlOrRd_09.scale(min_pop, max_pop)

        # 创建 gradient 字典：让热力图的颜色与图例的颜色完全匹配
        # 格式：{stop_point: color} stop_point 是 0 到 1 的浮点数
        gradient_map = {}
        for i in np.linspace(0, 1, 10):  # 在 0% 到 100% 之间取 10 个点
            # 将 0-1 的 i 映射回 人口值
            pop_value = min_pop + i * (max_pop - min_pop)
            # 获取该人口值对应的十六进制颜色
            gradient_map[i] = colormap.rgb_hex_str(pop_value)

        m = folium.Map(tiles="Stadia.AlidadeSmoothDark")
        heatmap_layer = HeatMap(
            [[d[1], d[0], d[2]] for d in district_data['population_data']],  # HeatMap 需要 [lat, lon, pop]
            radius=6,  # 热力点半径 (可调整)
            blur=10,  # 模糊度 (可调整)
            max_zoom=12,  # 在哪个缩放级别停止聚合
            gradient=gradient_map
        ).add_to(m)
        # colormap.add_to(m)  # 注意：这里选择不添加色带图例，感觉不太好看！！！
        m.fit_bounds(heatmap_layer.get_bounds(), padding=(20, 20))
        st_folium(m, key="map-district-population", use_container_width=True, height=600)

    # 人口分布3D图
    with col2:
        st.markdown(
            f"<h5 style='text-align: center;'>{selected_district_name}人口密度3D图</h5>",
            unsafe_allow_html=True
        )
        df_3d = pd.DataFrame(
            district_data['population_data'],
            columns=['lon', 'lat', 'population']
        )

        # 定义视图
        mid_lon = df_3d['lon'].mean()
        mid_lat = df_3d['lat'].mean()
        view_state = pdk.ViewState(
            longitude=mid_lon,
            latitude=mid_lat,
            zoom=10,  # 缩放级别 (1-20)。11 级别适合区/县
            pitch=50,  # 倾斜角度 (0-90 度)。50 度有很好的 3D 效果
            bearing=0  # 旋转角度
        )

        # 创建 3D 柱状图层
        min_pop = df_3d['population'].min()
        max_pop = df_3d['population'].max()
        layer = pdk.Layer(
            'ColumnLayer',
            data=df_3d,
            get_position=['lon', 'lat'],  # 柱子在地图上的 [经度, 纬度]
            get_elevation='population',  # 柱子的高度
            elevation_scale=10,  # 高度缩放因子。人口值（例如 100）相对于地图太小，需要放大
            radius=45,  # 每个柱子的半径（米）。TIF 是 100m 精度，因此设置 50m 半径
            get_fill_color=f"[255, 255 - (population - {min_pop}) / ({max_pop} - {min_pop}) * 255, 0, 150]",
            # 动态设置填充色：[R, G, B, A]
            pickable=True,  # 允许鼠标悬停
            auto_highlight=True  # 鼠标悬停时高亮
        )

        # 创建 PyDeck 地图对象
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style='mapbox://styles/mapbox/dark-v9',  # 使用暗色底图，匹配热力图
            tooltip={
                "html": "<b>人口:</b> {population}<br/><b>经度:</b> {lon}<br/><b>纬度:</b> {lat}",
                "style": {
                    "backgroundColor": "#f0f2f6",
                    "color": "black",
                    "border-radius": "5px"
                }
            }
        )
        st.pydeck_chart(r, use_container_width=True, height=600)

# 1. 重构代码 folium -> mapbox
# 2. 父区域填充功能
