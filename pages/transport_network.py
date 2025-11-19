import streamlit as st

from core.network import *
from core.common import *

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
    # 加载 gdf 数据
    driver_nodes_gdf, driver_edges_gdf = load_network_from_osm(zone_info["district_adcode"], network_type="drive")
    bike_nodes_gdf, bike_edges_gdf = load_network_from_osm(zone_info["district_adcode"], network_type="bike")
    walk_nodes_gdf, walk_edges_gdf = load_network_from_osm(zone_info["district_adcode"], network_type="walk")

    col1, col2, col3 = st.columns(3)

    # 道路网
    with col1:
        st.markdown(
            f"<h5 style='text-align: center;'>机动车网络</h5>",
            unsafe_allow_html=True
        )
        drive_style = generate_network_style_widgets(key="drive")
        deck_drive = plot_network_map(driver_nodes_gdf, driver_edges_gdf, drive_style)
        if deck_drive:
            st.pydeck_chart(deck_drive)

    # 骑行网路
    with col2:
        st.markdown(
            f"<h5 style='text-align: center;'>骑行网络</h5>",
            unsafe_allow_html=True
        )
        bike_style = generate_network_style_widgets(key="bike")
        deck_bike = plot_network_map(bike_nodes_gdf, bike_edges_gdf, bike_style)
        if deck_bike:
            st.pydeck_chart(deck_bike)

    # 步行网络
    with col3:
        st.markdown(
            f"<h5 style='text-align: center;'>步行网络</h5>",
            unsafe_allow_html=True
        )
        walk_style = generate_network_style_widgets(key="walk")
        deck_walk = plot_network_map(walk_nodes_gdf, walk_edges_gdf, walk_style)
        if deck_walk:
            st.pydeck_chart(deck_walk)

# 2. 渲染主页面——第二部分
if view_selection == f"{zone_info['district_name']}地面公交路网信息":
    pass

# 3. 渲染主页面——第三部分
if view_selection == f"{zone_info['district_name']}轨道交通路网信息":
    pass
