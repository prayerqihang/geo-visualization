import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from core.basic import *
from core.common import *
from utils import custom_sidebar_pages_order

# 子页面配置
st.set_page_config(
    page_title="基本信息",
    page_icon=":earth_americas:",
    layout="wide"
)

custom_sidebar_pages_order()  # 侧边栏
st.title("基本信息")
st.divider()

pca_code_data, df = load_cities_info()  # 加载数据
zone_info = select_zone(pca_code_data, df)  # 加载区域选择框
st.divider()

# 1. 渲染主页面——第一部分
st.markdown("### 1. 地理位置信息")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"<h5 style='text-align: center;'>父行政区：全国 | 子行政区：{zone_info['province_name']}</h5>",
        unsafe_allow_html=True
    )
    style_settings = generate_style_widgets(key="lv1", edge_width_base=5000)
    map1 = plot_zone_map(
        adcode=100000,
        sub_adcode=zone_info["province_adcode"],
        **style_settings
    )
    st.pydeck_chart(map1, use_container_width=True)

with col2:
    st.markdown(
        f"<h5 style='text-align: center;'>父行政区：{zone_info['province_name']} | 子行政区：{zone_info['city_name']}</h5>",
        unsafe_allow_html=True
    )
    style_settings = generate_style_widgets(key="lv2", edge_width_base=400)
    map2 = plot_zone_map(
        adcode=zone_info["province_adcode"],
        sub_adcode=zone_info["city_adcode"],
        **style_settings
    )
    st.pydeck_chart(map2, use_container_width=True)

with col3:
    st.markdown(
        f"<h5 style='text-align: center;'>父行政区：{zone_info['city_name']} | 子行政区：{zone_info['district_name']}</h5>",
        unsafe_allow_html=True
    )
    style_settings = generate_style_widgets(key="lv3", edge_width_base=150)
    map3 = plot_zone_map(
        adcode=zone_info["city_adcode"],
        sub_adcode=zone_info["district_adcode"],
        **style_settings
    )
    st.pydeck_chart(map3, use_container_width=True)

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

# 2.2. 人口信息展示
st.markdown("##### 信息维度选择")
view_selection = st.radio(
    "选择视图：",
    options=[
        f"{zone_info['city_name']}: 市级人口信息概览",
        f"{zone_info['district_name']}：区/县级人口信息概览"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

df_city_population_info = get_city_population_from_tif(zone_info["province_name"], zone_info["city_adcode"],
                                                       zone_info["all_district_names"], df,
                                                       selected_year)  # 加载指定年份城市人口统计数据
district_data = get_population_from_tif(zone_info["district_adcode"], selected_year)  # 加载指定年份区/县人口详细数据

st.divider()

if view_selection == f"{zone_info['city_name']}: 市级人口信息概览":
    col1, col2, col3 = st.columns(3)
    brush = alt.selection_interval(encodings=['y'])  # 用于鼠标交互，用户可以在 y 轴方向选择数据
    # 总人口条形图
    with col1:
        st.markdown(
            f"<h5 style='text-align: center;'>{zone_info['city_name']}各区域人口分布</h5>",
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
            f"<h5 style='text-align: center;'>{zone_info['city_name']}各区域人口密度分布</h5>",
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
            f"<h5 style='text-align: center;'>{zone_info['city_name']}各区域面积分布</h5>",
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
if view_selection == f"{zone_info['district_name']}：区/县级人口信息概览":
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
        f"<h5 style='text-align: center;'>{zone_info['district_name']}网格人口分布直方图</h5>",
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
            f"<h5 style='text-align: center;'>{zone_info['district_name']}人口密度热力图</h5>",
            unsafe_allow_html=True
        )
        r = plot_heatmap(district_data['population_data'])
        st.pydeck_chart(r, use_container_width=True)

    # 人口分布3D图
    with col2:
        st.markdown(
            f"<h5 style='text-align: center;'>{zone_info['district_name']}人口密度3D图</h5>",
            unsafe_allow_html=True
        )
        r = plot_population_3d_map(district_data['population_data'])
        st.pydeck_chart(r, use_container_width=True)
