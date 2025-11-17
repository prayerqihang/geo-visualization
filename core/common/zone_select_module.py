import streamlit as st
import os
import json
import pandas as pd

from config.settings import ASSETS_MAP_PATH


# @st.cache_data: Streamlit 提供的函数返回值缓存
# 简单来说，这个装饰器让函数保存自己的计算结果。当同一个函数第二次被相同的参数调用时，直接返回之前缓存的结果，而不是重新计算
@st.cache_data
def load_cities_info():
    """缓存加载 pca-code 和 adcode 数据"""
    pca_code_path = os.path.join(ASSETS_MAP_PATH, "pca-code.json")
    with open(file=pca_code_path, mode="r", encoding="utf-8") as f:
        pca_code_data = json.load(f)

    adcode_path = os.path.join(ASSETS_MAP_PATH, "amap_adcode_citycode.xlsx")
    df = pd.read_excel(adcode_path)
    df.set_index("中文名", inplace=True)

    return pca_code_data, df


def select_zone(pca_code_data, adcode_df):
    """
    加载区域选择组件。
    :param pca_code_data: 多级行政区数据
    :param adcode_df: adcode 查找表
    :return: 选择的省，城市，区/县 名称 & adcode 字典
    """
    st.markdown("##### 区域范围")
    col1, col2, col3 = st.columns(3)

    # --- 维度一：省 ---
    province_names = [p["name"] for p in pca_code_data]
    with col1:
        selected_province_name = st.selectbox("请选择省份（或直辖市）：", province_names)
    selected_province_adcode = adcode_df.loc[selected_province_name, "adcode"]
    selected_province_dict = next(
        p for p in pca_code_data if p["name"] == selected_province_name)  # next: 从可迭代对象中返回第一个满足条件的元素

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
            selected_city_adcode = adcode_df.loc[selected_city_name, "adcode"]
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
        selected_district_adcode = adcode_df.loc[selected_district_name, "adcode"]
    except KeyError:
        st.error(f"未找到 {selected_district_name} 对应的 adcode!")
        st.stop()

    # 处理 amap_adcode_citycode.xlsx 中的重名区域
    if isinstance(selected_district_adcode, (pd.DataFrame, pd.Series)):
        if selected_province_name in ["北京市", "天津市", "上海市", "重庆市"]:
            prefix = str(selected_city_adcode)[:3]
        else:
            prefix = str(selected_city_adcode)[:4]
        count = 0
        for name, adcode in selected_district_adcode.items():
            if str(adcode).startswith(prefix):
                selected_district_adcode = adcode
                count += 1
        if count != 1:
            st.warning("展示的地图信息可能存在错误！详细信息：存在重名区域未被区分，adcode 可能错误。")
            st.stop()

    if selected_province_adcode is None or selected_city_adcode is None or selected_district_adcode is None:
        st.error(f"省份/城市/区域对应 adcode 数据错误！")
        st.stop()

    return {
        "province_name": selected_province_name,
        "province_adcode": selected_province_adcode,
        "city_name": selected_city_name,
        "city_adcode": selected_city_adcode,
        "district_name": selected_district_name,
        "district_adcode": selected_district_adcode,
        "all_district_names": district_names  # 城市下的所有区/县列表
    }
