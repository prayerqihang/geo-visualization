import streamlit as st
import geopandas as gpd
import osmnx as ox
import pydeck as pdk
import pydeck.data_utils

from core.common import *
from utils import custom_sidebar_pages_order, get_geojson_from_aliyun


@st.cache_data(show_spinner=False)
def load_network_from_geojson(adcode, network_type="driver"):
    """
    从 osm 上下载道路网数据。
    :param adcode (int): 区/县 adcode
    :param network_type (str): 需要获取的交通网络类型，默认为道路网
    :return: gdf_network_edges (GeoDataFrame): 路网边的 gdf
    """
    geojson_data_dict = get_geojson_from_aliyun(adcode, is_sub=False)
    gdf = gpd.GeoDataFrame.from_features(geojson_data_dict['features'], crs="EPSG:4326")
    polygon = gdf.geometry.union_all()  # 无论 GeoJSON 中是一个还是多个多边形，都将它们合并

    if not polygon.is_valid:
        st.error("GeoJSON 集合要素无效，请检查！")
        return None

    status_placeholder = st.empty()  # 创建 streamlit 提供的占位符，可以动态显示不同的内容
    status_placeholder.info(f"正在从OSM下载 {network_type} 类型的路网...")
    G = ox.graph_from_polygon(polygon, network_type=network_type)
    gdf_network_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    status_placeholder.success("路网下载并构建成功！")

    return gdf_network_edges


# 子页面配置
st.set_page_config(
    page_title="交通网络",
    page_icon=":red_car:",
    layout="wide"
)

custom_sidebar_pages_order()  # 渲染侧边栏
st.title("交通网络信息")
st.divider()

pca_code_data, df = load_cities_info()  # 加载数据
zone_info = select_zone(pca_code_data, df)  # 加载区域选择框
st.divider()

view_selection = st.radio(
    "选择需要展示的信息：",
    options=[
        f"{zone_info['district_name']}道路网信息",
        f"{zone_info['district_name']}地面公交路网信息",
        f"{zone_info['district_name']}轨道交通路网信息"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

# 1. 渲染主页面——第一部分
if view_selection == f"{zone_info['district_name']}道路网信息":
    # 加载道路网 gdf 数据
    gdf_network_edges = load_network_from_geojson(zone_info["district_adcode"], network_type="drive")

    # 创建视图
    bounds = gdf_network_edges.total_bounds  # 获取总边界
    points_for_view = [
        [bounds[0], bounds[1]],  # [minx, miny] (西南角)
        [bounds[2], bounds[3]]  # [maxx, maxy] (东北角)
    ]
    view_state = pdk.data_utils.compute_view(points=points_for_view)
    view_state.pitch = 0  # 上下旋转角度，2D 俯视
    view_state.bearing = 0  # 左右旋转角度

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=gdf_network_edges,
        get_line_color="[255, 100, 100]",
        get_line_width=5,
        pickable=True,
        auto_highlight=True,
    )
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v9",
        tooltip={"text": "道路: {name}\n类型: {highway}"}
    )
    st.pydeck_chart(deck)

# 2. 渲染主页面——第二部分
if view_selection == f"{zone_info['district_name']}地面公交路网信息":
    pass

# 3. 渲染主页面——第三部分
if view_selection == f"{zone_info['district_name']}轨道交通路网信息":
    pass
