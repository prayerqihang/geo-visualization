import pandas as pd
import pydeck as pdk
import pydeck.data_utils
import numpy as np
from typing import cast


def plot_heatmap(population_data, start_rgba=None, end_rgba=None, steps=5):
    """
    使用 PyDeck 绘制人口密度热力图。
    Args:
        population_data (list): 包含 [lon, lat, population] 的列表。
    Returns:
        pdk.Deck: PyDeck 地图对象。
    """
    df = pd.DataFrame(
        population_data,
        columns=['lon', 'lat', 'population']
    )

    # 计算色阶
    if start_rgba is None:
        start_rgba = [255, 255, 0, 20]  # 黄、低透明度
    if end_rgba is None:
        end_rgba = [255, 0, 0, 255]  # 红、高透明度

    start_array = np.array(start_rgba)
    end_array = np.array(end_rgba)
    gradient_array = np.linspace(start_array, end_array, steps, dtype=int, retstep=False)
    dynamic_color_range = cast(np.ndarray, gradient_array).tolist()

    # 创建视图
    all_points = df[['lon', 'lat']].values.tolist()
    view_state = pdk.data_utils.compute_view(all_points)
    view_state.pitch = 0  # 上下旋转角度，2D 俯视
    view_state.bearing = 0  # 左右旋转角度

    # 创建热力图层
    layer = pdk.Layer(
        'HeatmapLayer',
        data=df,
        get_position=['lon', 'lat'],
        get_weight='population',
        radius_pixels=50,
        intensity=1,  # 每个数据点值的权重（乘数）
        opacity=0.8,
        color_range=dynamic_color_range,
        pickable=False
    )

    # 创建 PyDeck 地图对象
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/dark-v9'
    )
    return r


def plot_population_3d_map(population_data, elevation_scale=10, radius=45, pitch=50):
    """
    使用 PyDeck 绘制人口密度 3D 柱状图。
    Args:
        population_data (list): 包含 [lon, lat, population] 的列表。
        elevation_scale (int): 高度缩放因子。
        radius (int): 柱子半径（米）。
        pitch (int): 视图倾斜角度 (0-90 度)。
    Returns:
        pdk.Deck: PyDeck 地图对象。
    """
    df_3d = pd.DataFrame(
        population_data,
        columns=['lon', 'lat', 'population']
    )

    # 创建视图
    all_points = df_3d[['lon', 'lat']].values.tolist()
    view_state = pdk.data_utils.compute_view(all_points)
    view_state.pitch = pitch
    view_state.bearing = 0

    # 3. 创建 3D 柱状图层
    min_pop = df_3d['population'].min()
    max_pop = df_3d['population'].max()
    layer = pdk.Layer(
        'ColumnLayer',
        data=df_3d,
        get_position=['lon', 'lat'],
        get_elevation='population',
        elevation_scale=elevation_scale,  # 高度缩放因子。人口值（例如 100）相对于地图太小，需要放大
        radius=radius,
        get_fill_color=f"[255, 255 - (population - {min_pop}) / ({max_pop} - {min_pop}) * 255, 0, 150]",
        pickable=True,
        auto_highlight=True
    )

    # 创建 PyDeck 地图对象
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/dark-v9',
        tooltip={
            "html": "<b>人口:</b> {population}<br/><b>经度:</b> {lon}<br/><b>纬度:</b> {lat}",
            "style": {
                "backgroundColor": "#f0f2f6",
                "color": "black",
                "border-radius": "5px"
            }
        }
    )
    return r

