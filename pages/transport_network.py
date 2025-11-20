import streamlit as st
import altair as alt

from core.network import *
from core.common import *


def network_info_view(nodes_gdf, edges_gdf, key):
    """
    展示不同类型路网的信息
    :param nodes_gdf: 路网节点 gdf
    :param edges_gdf: 路网边 gdf
    :param key: 组件唯一标识符 (如 'drive', 'bike')
    :return:
    """
    # 基本指标
    total_km = edges_gdf["length"].astype(float).sum() / 1000
    avg_len = edges_gdf["length"].astype(float).mean()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.markdown(f"**道路总里程: {total_km:.1f} km**")
    with col2:
        with st.container(border=True):
            st.markdown(f"**平均道路长度: {avg_len:.1f} m**")
    with col3:
        with st.container(border=True):
            st.markdown(f"**道路总数: {len(edges_gdf):,}**")
    with col4:
        with st.container(border=True):
            st.markdown(f"**交叉口总数: {len(nodes_gdf):,}**")

    col1, col2, col3 = st.columns([0.35, 0.25, 0.40])

    # 网络可视化
    with col1:
        st.markdown(
            f"<h5 style='text-align: center;'>网络可视化</h5>",
            unsafe_allow_html=True
        )
        network_style = generate_network_style_widgets(key=key)
        deck = plot_network_map(nodes_gdf, edges_gdf, network_style)
        if deck:
            st.pydeck_chart(deck)

    with col2:
        st.markdown(
            f"<h5 style='text-align: center;'>交叉口度分布</h5>",
            unsafe_allow_html=True
        )
        degree_df = nodes_gdf["degree"].value_counts().reset_index()
        brush = alt.selection_interval(encodings=["x"])
        chart = alt.Chart(degree_df).mark_bar().encode(
            y=alt.Y("count:Q", title="交叉口数量"),
            x=alt.X(
                "degree:O",  # 有序离散数值
                title="度",
                axis=alt.Axis(labelAngle=0)  # 标签角度为 0 度（水平）
            ),
            tooltip=["degree", "count"],
            color=alt.condition(
                brush,
                if_true=alt.value("orange"),  # 选中时的颜色
                if_false=alt.value("steelblue")  # 默认颜色
            )
        ).properties(
            height=600
        ).add_params(
            brush
        ).interactive()

        st.altair_chart(chart, use_container_width=True)

    with col3:
        st.markdown(
            f"<h5 style='text-align: center;'>道路类型和长度分布</h5>",
            unsafe_allow_html=True
        )
        # 注意：OSMnx 的 highway 字段有时是列表，这里统一转为字符串
        chart_data = edges_gdf.reset_index()[["highway", "length"]].copy()
        chart_data["highway"] = chart_data["highway"].astype(str)
        chart_data["length"] = chart_data["length"].astype(float)
        top_k_highways = chart_data["highway"].value_counts().nlargest(6).index.tolist()  # 取 top-k 类型
        chart_data = chart_data[chart_data["highway"].isin(top_k_highways)]  # 过滤，仅剩 top-k 类型的数据

        # 定义交互选择器 fields=['highway']: 表示根据“道路类型”来进行筛选
        selection = alt.selection_point(fields=["highway"], name="Select")

        # 道路类型
        bar_chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X("highway:N", sort="-y", title='道路等级', axis=alt.Axis(labelAngle=0)),  # -y 表示按 y 轴的数量降序排列
            y=alt.Y("count()", title='道路数量'),  # count() 是一个聚合函数，统计 x 轴分组后每一组的记录数量
            color=alt.condition(
                selection,
                if_true=alt.value('steelblue'),
                if_false=alt.value('lightgray')
            ),
            tooltip=["highway", "count()"]
        ).properties(
            height=250,
        ).add_params(
            selection  # 关键：将选择器绑定到图表
        )

        # 道路长度分布
        hist_chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X("length:Q", bin=alt.Bin(maxbins=30), title="道路长度 (米)"),
            y=alt.Y("count()", title="频数"),
            color=alt.value("steelblue"),
            tooltip=["count()"]
        ).properties(
            height=200,
        ).transform_filter(
            selection  # 关键：这一行实现了“过滤”功能
        )

        # 使用 & 符号将两个图表垂直连接
        # 使用 resolve_scale 确保坐标轴 x/y 均独立
        final_chart = (bar_chart & hist_chart).resolve_scale(
            x="independent", y="independent"
        )
        st.altair_chart(final_chart, use_container_width=True)


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
    # 1.1. 网络可视化
    # 加载 gdf 数据
    drive_nodes_gdf, drive_edges_gdf = load_network_from_osm(zone_info["district_adcode"], network_type="drive")
    bike_nodes_gdf, bike_edges_gdf = load_network_from_osm(zone_info["district_adcode"], network_type="bike")
    walk_nodes_gdf, walk_edges_gdf = load_network_from_osm(zone_info["district_adcode"], network_type="walk")
    st.divider()

    if drive_nodes_gdf is not None and drive_edges_gdf is not None:
        st.markdown(
            f"<h4 style='text-align: center;'>机动车网络</h4>",
            unsafe_allow_html=True
        )
        network_info_view(nodes_gdf=drive_nodes_gdf, edges_gdf=drive_edges_gdf, key="drive")

    st.divider()
    if bike_nodes_gdf is not None and bike_edges_gdf is not None:
        st.markdown(
            f"<h4 style='text-align: center;'>骑行网络</h4>",
            unsafe_allow_html=True
        )
        network_info_view(nodes_gdf=bike_nodes_gdf, edges_gdf=bike_edges_gdf, key="bike")

    st.divider()
    if walk_nodes_gdf is not None and walk_edges_gdf is not None:
        st.markdown(
            f"<h4 style='text-align: center;'>步行网络</h4>",
            unsafe_allow_html=True
        )
        network_info_view(nodes_gdf=walk_nodes_gdf, edges_gdf=walk_edges_gdf, key="walk")

# 2. 渲染主页面——第二部分
if view_selection == f"{zone_info['district_name']}地面公交路网信息":
    pass

# 3. 渲染主页面——第三部分
if view_selection == f"{zone_info['district_name']}轨道交通路网信息":
    pass
