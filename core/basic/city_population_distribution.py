import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import rasterio
import rasterio.mask
import os

from utils import get_geojson_from_aliyun
from config.settings import DATA_CITY_PATH


@st.cache_data
def get_population_from_tif(adcode, year):
    """
    使用 GeoJSON 字典从 GeoTIFF 文件中裁剪数据，并返回详细的人口统计信息。
    Returns:
        dict: 包含人口列表、总和、面积、密度等信息的字典。
              如果裁剪失败，返回 None。
    """
    # 加载人口 tif 数据
    tif_filename = f"chn_pop_{year}_CN_100m_R2025A_v1.tif"
    tif_filepath = os.path.join(DATA_CITY_PATH, tif_filename)
    if not os.path.exists(tif_filepath):
        st.error(f"未找到 {year} 年的人口数据文件：{tif_filename}")
        st.write(f"请检查路径：{tif_filepath}")
        st.stop()

    # --- 步骤 1: 加载 GeoJSON 形状 ---
    geojson_data_dict = get_geojson_from_aliyun(adcode, is_sub=False)
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
def get_city_population_from_tif(province_name, city_adcode, district_names, adcode_df, year):
    """
    获取一个城市下所有区/县的人口和密度数据。
    Args:
        province_name (str): 选定省份名称
        city_adcode (int): 选定城市的 adcode
        district_names (list): 选定城市的 'children' 列表
        adcode_df (pd.DataFrame): adcode 查找表
        year (int): 年份
    Returns:
        pd.DataFrame: 包含 '区域', '总人口', '人口密度' 的 DataFrame
    """
    population_info_list = []

    # 加载人口 tif 数据
    tif_filename = f"chn_pop_{year}_CN_100m_R2025A_v1.tif"
    tif_filepath = os.path.join(DATA_CITY_PATH, tif_filename)
    if not os.path.exists(tif_filepath):
        st.error(f"未找到 {year} 年的人口数据文件：{tif_filename}")
        st.write(f"请检查路径：{tif_filepath}")
        st.stop()

    # 使用 st.progress 来显示进度
    process_bar = st.progress(0, text=f"正在加载各区/县人口数据...")

    for i, district_name in enumerate(district_names):
        process_bar.progress((i + 1) / len(district_names), text=f"正在处理：{district_name} 的人口数据")

        try:
            district_adcode = adcode_df.loc[district_name, "adcode"]
        except KeyError:
            st.warning(f"{district_name} 没有查询到对应的 adcode，跳过处理！")
            continue

        if isinstance(district_adcode, (pd.DataFrame, pd.Series)):
            if province_name in ["北京市", "天津市", "上海市", "重庆市"]:
                prefix = str(city_adcode)[:3]
            else:
                prefix = str(city_adcode)[:4]
            count = 0
            for name, adcode in district_adcode.items():
                if str(adcode).startswith(prefix):
                    district_adcode = adcode
                    count += 1
            if count != 1:
                st.warning("人口信息可能存在错误！详细信息：存在重名区域未被区分，adcode 可能错误。")

        data = get_population_from_tif(district_adcode, year)

        population_info_list.append({
            "district": district_name,
            "total_population": data["total_population"],
            "population_density": data["population_density"],
            "area_km2": data["area_km2"]
        })

    # 完成后移除进度条
    process_bar.empty()
    return pd.DataFrame(population_info_list)
