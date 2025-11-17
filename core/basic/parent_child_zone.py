import streamlit as st
import pydeck as pdk
import pydeck.data_utils

from utils import get_geojson_from_aliyun, hex_to_rgba, extract_geojson_coordinates
from config.settings import MAPBOX_STYLE_MAP, COLOR_MAP_HEX


def plot_zone_map(adcode, sub_adcode, map_type_url,
                    do_fill, fill_color_hex, fill_opacity,
                    edge_color_hex, sub_edge_color_hex, edge_width, sub_edge_width):
    """
    绘制地图：
    - 父级行政区 adcode (仅边界)
    - 子级行政区 sub_adcode (填充)
    """
    # 获取 GeoJSON
    parent_geojson = get_geojson_from_aliyun(adcode, is_sub=True)
    child_geojson = get_geojson_from_aliyun(sub_adcode, is_sub=False)
    # 颜色转换
    fill_alpha = fill_opacity if do_fill else 0.0
    fill_rgba = hex_to_rgba(fill_color_hex, fill_alpha)
    edge_rgba = hex_to_rgba(edge_color_hex, 1.0)
    sub_edge_rgba = hex_to_rgba(sub_edge_color_hex, 1.0)

    # 定义图层
    parent_layer = pdk.Layer(
        type="GeoJsonLayer",  # 图层类型，用于绘制不同类型地理要素
        id=f"parent_geojson_{adcode}",
        data=parent_geojson,
        stroked=True,  # 绘制边界
        filled=False,  # 不填充
        get_line_color=edge_rgba,
        get_line_width=edge_width,
        line_width_units="pixels",
        pickable=False
    )
    child_layer = pdk.Layer(
        type="GeoJsonLayer",
        id=f"child_geojson_{adcode}",
        data=child_geojson,
        stroked=True,
        filled=do_fill,
        get_fill_color=fill_rgba,
        get_line_color=sub_edge_rgba,
        get_line_width=sub_edge_width,
        line_width_units="pixels",
        pickable=False
    )

    # 创建视图
    all_points = extract_geojson_coordinates(parent_geojson)
    view_state = pdk.data_utils.compute_view(all_points)
    view_state.pitch = 0  # 上下旋转角度，2D 俯视
    view_state.bearing = 0  # 左右旋转角度

    # 创建地图
    r = pdk.Deck(
        layers=[parent_layer, child_layer],
        initial_view_state=view_state,
        map_style=map_type_url
    )
    return r


def generate_style_widgets(key, edge_width_base):
    """
    生成一套独立的地图样式控制小部件。
    :parameter
    - key (str): 用于控制组件 ID 不重复
    - edge_width_base (int): 边框粗细的乘数
    """
    with st.expander("配置此地图样式", expanded=False):
        # --- 0. 底图样式 ---
        st.markdown("**底图样式**")
        # --- 底图类型 ---
        map_type = st.selectbox(
            "请选择底图类型：",
            options=list(MAPBOX_STYLE_MAP.keys()),
            index=0,  # 默认使用 "街道图"
            key=f"map_type_{key}"
        )
        selected_map_type = MAPBOX_STYLE_MAP[map_type]

        st.divider()

        # --- 1. 填充样式 ---
        st.markdown("**填充样式**")
        # --- 是否填充 ---
        do_fill = st.checkbox("是否填充子行政区", value=True, key=f"do_fill_{key}")
        # --- 填充颜色 ---
        fill_color_name = st.selectbox(
            "请选择子行政区地图填充色：",
            options=list(COLOR_MAP_HEX.keys()),
            index=0,  # 默认使用"灰色"
            key=f"fill_color_name_{key}"
        )
        selected_fill_color = COLOR_MAP_HEX[fill_color_name]
        # --- 填充透明度（0-1 之间，设计成滑动条的形式） ---
        fill_opacity = st.slider(
            "请选择填充透明度",
            min_value=0.1,
            max_value=1.0,
            value=0.7,  # 默认值
            step=0.05,
            disabled=(not do_fill),  # 核心：当不填充时，禁用此滑块
            key=f"fill_opacity_{key}"
        )

        st.divider()

        # --- 2. 边界样式 ---
        st.markdown("**边界样式**")
        # 父行政区
        edge_color = st.selectbox(
            "请选择父行政区边界颜色：",
            options=list(COLOR_MAP_HEX.keys()),
            index=0,  # 默认使用"灰色"
            key=f"edge_color_{key}"
        )
        selected_edge_color = COLOR_MAP_HEX[edge_color]
        edge_width = st.slider(
            "请选择父行政区边界宽度",
            min_value=1.0,
            max_value=10.0,
            value=2.0,  # 默认值
            step=0.5,
            key=f"edge_width_{key}"
        )
        # 子行政区
        sub_edge_color = st.selectbox(
            "请选择子行政区边界颜色：",
            options=list(COLOR_MAP_HEX.keys()),
            index=0,  # 默认使用"灰色"
            key=f"sub_edge_color_{key}"
        )
        selected_sub_edge_color = COLOR_MAP_HEX[sub_edge_color]
        sub_edge_width = st.slider(
            "请选择子行政区边界宽度",
            min_value=1.0,
            max_value=10.0,
            value=3.0,  # 默认值
            step=0.5,
            key=f"sub_edge_width_{key}"
        )

    # 返回一个与 plot_pydeck_map 参数匹配的字典
    return {
        "map_type_url": selected_map_type,
        "do_fill": do_fill,
        "fill_color_hex": selected_fill_color,
        "fill_opacity": fill_opacity,
        "edge_color_hex": selected_edge_color,
        "sub_edge_color_hex": selected_sub_edge_color,
        "edge_width": edge_width * edge_width_base,
        "sub_edge_width": sub_edge_width * edge_width_base
    }
