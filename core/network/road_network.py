import streamlit as st
import geopandas as gpd
import osmnx as ox
import os
import pydeck as pdk
import pydeck.data_utils
import numpy as np
import pandas as pd

from config.settings import DATA_NETWORK_PATH, MAPBOX_STYLE_MAP, COLOR_MAP_HEX
from utils import *

# 关闭 osmnx 的自动缓存功能，禁止在本地生成 ./cache 文件夹
ox.settings.use_cache = False


@st.cache_data(show_spinner=False)
def load_network_from_osm(adcode, network_type):
    """
    从 osm 上下载道路网数据。
    :param adcode (int): 区/县 adcode
    :param network_type (str): 需要获取的交通网络类型
    :return: (gdf_nodes, gdf_edges): 路网"边"/"节点"的 gdf
    """
    adcode_dir = os.path.join(DATA_NETWORK_PATH, str(adcode))
    if not os.path.exists(adcode_dir):
        os.makedirs(adcode_dir)

    edges_file_path = os.path.join(adcode_dir, f"{network_type}_edges.parquet")
    nodes_file_path = os.path.join(adcode_dir, f"{network_type}_nodes.parquet")

    status_placeholder = st.empty()  # 创建 streamlit 提供的占位符，可以动态显示不同的内容

    # 优先检查本地缓存文件
    if os.path.exists(edges_file_path) and os.path.exists(nodes_file_path):
        status_placeholder.info(f"发现本地缓存文件，正在加载 {network_type} 路网...")
        try:
            gdf_edges = gpd.read_parquet(edges_file_path)
            gdf_nodes = gpd.read_parquet(nodes_file_path)
            status_placeholder.success(f"已从本地文件加载 {network_type} 路网！")
            return gdf_nodes, gdf_edges
        except Exception as e:
            st.warning(f"本地文件读取失败，将尝试重新下载。原因: {e}")

    # 如果本地不存在文件
    status_placeholder.info(f"本地无缓存，正在从 OSM 下载 {network_type} 路网（可能需要几分钟，请稍候）...")
    geojson_data_dict = get_geojson_from_aliyun(adcode, is_sub=False)
    gdf = gpd.GeoDataFrame.from_features(geojson_data_dict['features'], crs="EPSG:4326")
    polygon = gdf.geometry.union_all()  # 无论 GeoJSON 中是一个还是多个多边形，都将它们合并
    if not polygon.is_valid:
        st.error("GeoJSON 集合要素无效，请检查！")
        return None, None

    try:
        G = ox.graph_from_polygon(polygon, network_type=network_type)
        gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
        # 格式转换：Parquet 不支持一列数据中同时有 list/non-list/non-null values，因此统一转换为字符串
        for col in gdf_edges.columns:
            if col != 'geometry':
                gdf_edges[col] = gdf_edges[col].astype(str)
        gdf_edges.to_parquet(edges_file_path)
        for col in gdf_nodes.columns:
            if col != 'geometry':
                gdf_nodes[col] = gdf_nodes[col].astype(str)
        gdf_nodes.to_parquet(nodes_file_path)

        status_placeholder.success(f"{network_type} 类型路网下载并构建完成，并成功保存到本地！")
        return gdf_nodes, gdf_edges
    except Exception as e:
        st.error(f"OSM 下载或构建失败: {e}")
        return None, None


def generate_network_style_widgets(key):
    """
    生成路网地图的样式控制组件
    :param key: 组件唯一标识符 (如 'drive', 'bike')
    """
    config_dict = {}
    with st.expander(f"配置 {key} 图层样式", expanded=False):
        # 底图选择
        map_type = st.selectbox(
            "底图风格",
            options=list(MAPBOX_STYLE_MAP.keys()),
            index=0,  # 默认街道图
            key=f"map_type_{key}"
        )
        config_dict["map_style"] = MAPBOX_STYLE_MAP[map_type]

        st.divider()

        col1, col2 = st.columns(2)
        # 道路（Edges）配置
        with col1:
            st.markdown("#### 道路样式配置")

            config_dict["show_edges"] = st.checkbox("显示道路", value=True, key=f"show_edges_{key}")
            if config_dict["show_edges"]:
                # 是否开启渐变渲染
                config_dict["use_gradient_edges"] = st.checkbox("按道路长度渐变渲染", value=False, key=f"grad_edge_{key}")
                if not config_dict["use_gradient_edges"]:
                    # 不开启渐变，才显示单色选择器
                    edge_color = st.selectbox(
                        "道路颜色",
                        options=list(COLOR_MAP_HEX.keys()),
                        index=list(COLOR_MAP_HEX.keys()).index("红色"),
                        key=f"edge_color_{key}"
                    )
                    config_dict["edge_color"] = COLOR_MAP_HEX[edge_color]
                else:
                    config_dict["edge_color"] = "#000000"  # 占位，不会用到
                # 线条宽度
                config_dict["edge_width"] = st.slider(
                    "道路宽度 (px)", 0.5, 10.0, 1.5, 0.5,
                    key=f"edge_width_{key}"
                )
                # 线条透明度
                config_dict["edge_opacity"] = st.slider(
                    "道路透明度", 0.0, 1.0, 0.8, 0.1,
                    key=f"edge_opacity_{key}"
                )

        # 节点（Nodes）配置
        with col2:
            st.markdown("#### 交叉口样式配置")

            config_dict["show_nodes"] = st.checkbox("显示节点", value=False, key=f"show_nodes_{key}")
            if config_dict["show_nodes"]:
                # 是否开启渐变渲染
                config_dict["use_gradient_nodes"] = st.checkbox("按度渐变渲染", value=False, key=f"grad_node_{key}")
                if not config_dict["use_gradient_nodes"]:
                    node_color = st.selectbox(
                        "节点颜色",
                        options=list(COLOR_MAP_HEX.keys()),
                        index=list(COLOR_MAP_HEX.keys()).index("蓝色"),
                        key=f"node_color_{key}"
                    )
                    config_dict["node_color"] = COLOR_MAP_HEX[node_color]
                else:
                    config_dict["node_color"] = "#000000"  # 占位
                # 节点半径
                config_dict["node_radius"] = st.slider(
                    "节点半径 (meter)", 10.0, 50.0, 20.0, 1.0,
                    key=f"node_radius_{key}"
                )
                # 节点透明度
                config_dict["node_opacity"] = st.slider(
                    "节点透明度", 0.0, 1.0, 0.9, 0.1,
                    key=f"node_opacity_{key}"
                )

    return config_dict


def plot_network_map(nodes_gdf, edges_gdf, config_dict):
    """
    绘制路网地图
    :param nodes_gdf: 包含交叉口 geometry 的 GeoDataFrame
    :param edges_gdf: 包含道路 geometry 的 GeoDataFrame
    :param config_dict: 由 generate_network_style_widgets 生成的配置字典
    """
    # 如果用户没有选择展示任何内容，则直接返回 None
    if not config_dict["show_edges"] and not config_dict["show_nodes"]:
        return None

    # 创建图层
    layers = []
    if config_dict["show_edges"] and edges_gdf is not None:
        edges_gdf["length"] = edges_gdf["length"].astype(float)  # 转换格式

        if config_dict["use_gradient_edges"]:
            edges_gdf["render_color"] = calculate_gradient_color(
                values=edges_gdf["length"], start_rgba=[255, 230, 0, 150], end_rgba=[255, 0, 0, 255])  # 计算颜色列
            get_line_color = "render_color"
        else:
            get_line_color = hex_to_rgba(config_dict["edge_color"], config_dict["edge_opacity"])

        edge_layer = pdk.Layer(
            type="GeoJsonLayer",
            id="layer_edges",
            data=edges_gdf,
            get_line_color=get_line_color,  # 传入列名，或固定颜色列表
            get_line_width=config_dict["edge_width"],
            line_width_units="pixels",  # 使用像素单位
            line_width_min_pixels=1,
            line_joint_rounded=True,
            pickable=True,
            auto_highlight=True
        )
        layers.append(edge_layer)

    # 计算度（必须要在 if 条件外计算，否则后续绘图时会找不到 degree 列）
    all_nodes = list(edges_gdf.index.get_level_values("u")) + list(
        edges_gdf.index.get_level_values("u"))  # 汇总所有边两端的节点。注意 u,v 列是索引
    node_counts = pd.Series(all_nodes).value_counts()  # 统计每个节点出现了几次
    # plot_nodes 的 index 即为 nodes 的编号，根据编号去 node_counts 中匹配对应的值；如果没有匹配到，则说明这个节点没有边相连
    nodes_gdf["degree"] = nodes_gdf.index.map(node_counts).fillna(0)
    nodes_gdf["degree"] = nodes_gdf["degree"] / 2  # 有向图，除以 2

    if config_dict["show_nodes"] and nodes_gdf is not None:
        if config_dict["use_gradient_nodes"]:
            nodes_gdf["render_color"] = calculate_gradient_color(
                values=nodes_gdf["degree"], start_rgba=[144, 238, 144, 255], end_rgba=[0, 0, 255, 255])
            get_fill_color = "render_color"
        else:
            get_fill_color = hex_to_rgba(config_dict["node_color"], config_dict["node_opacity"])

        node_layer = pdk.Layer(
            type="GeoJsonLayer",
            id="layer_nodes",
            data=nodes_gdf,
            stroked=False,
            filled=True,
            get_fill_color=get_fill_color,
            get_radius=config_dict["node_radius"],
            radius_units="pixels",  # 使用像素单位
            radius_min_pixels=2,
            pickable=True,
            auto_highlight=True
        )
        layers.append(node_layer)

    # 创建视图
    # 优先使用 edges 的边界，如果没有则尝试使用 nodes
    if edges_gdf is not None and not edges_gdf.empty:
        bounds = edges_gdf.total_bounds
    else:
        bounds = nodes_gdf.total_bounds

    points_for_view = [
        [bounds[0], bounds[1]],  # sw
        [bounds[2], bounds[3]]  # ne
    ]
    view_state = pdk.data_utils.compute_view(points=points_for_view)
    view_state.pitch = 0
    view_state.bearing = 0

    # 创建 Deck 对象
    tooltip = {
        "html": """
                <b>类型:</b> {highway}<br/>
                <b>名称/ID:</b> {name}<br/>
            """,
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=config_dict["map_style"],
        tooltip=tooltip
    )

    return deck


def calculate_gradient_color(values, start_rgba=None, end_rgba=None, steps=5):
    """
    基于数值列计算分级渐变颜色
    :param values: pd.Series, 数值列
    :param start_rgba: list, [r, g, b, a] 或 [r, g, b], 默认黄色
    :param end_rgba: list, [r, g, b, a] 或 [r, g, b], 默认红色
    :param steps: int, 分级数量 (例如 5 表示将数据分为 5 个颜色等级)
    :return: list of [r, g, b, a]
    """
    if start_rgba is None:
        start_rgba = [255, 255, 0, 150]  # 默认淡黄
    if end_rgba is None:
        end_rgba = [255, 0, 0, 255]  # 默认深红

    start_arr = np.array(start_rgba)
    end_arr = np.array(end_rgba)
    palette = np.linspace(start_arr, end_arr, steps, dtype=int)

    # 数据归一化与分箱
    val_array = values.to_numpy()
    min_val = np.min(val_array)
    max_val = np.max(val_array)
    norm_values = (val_array - min_val) / (max_val - min_val)
    # 将数据映射到索引 0 ~ (steps-1)。例如 steps=5, norm=0.99 -> index=4
    indices = (norm_values * steps).astype(int)
    # 边界处理：最大值 1.0 会变成 steps (越界)，需限制在 steps-1
    indices = np.clip(indices, 0, steps - 1)

    # 花式索引：用一个整数数组 (indices) 去索引另一个数组
    mapped_colors = np.take(palette, indices, axis=0)

    return mapped_colors.tolist()
