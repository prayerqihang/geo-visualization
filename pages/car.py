import streamlit as st
from streamlit_folium import st_folium

from utils import custom_sidebar_pages_order

# 1. 渲染侧边栏
custom_sidebar_pages_order()

# test_heatmap.py
# -----------------
# 这是一个独立的 Python 脚本，用于演示 Folium HeatMap 的正确用法
# -----------------

import folium
from folium.plugins import HeatMap
import branca.colormap as cm
import numpy as np

# --- 1. 编造简单数据 ---
# 格式: [纬度, 经度, 权重]
# 我们在纽约市设置 4 个点，权重分别为 10, 25, 50, 100
heatmap_data = [
    [40.71, -74.00, 10],  # 曼哈顿下城 (权重 10)
    [40.68, -73.99, 25],  # 布鲁克林 (权重 25)
    [40.75, -73.98, 50],  # 曼哈顿中城 (权重 50)
    [40.78, -73.96, 100]  # 曼哈顿上城 (权重 100)
]

# --- 2. 确定归一化范围 ---
# 这是最关键的一步，我们希望图例和热力图都使用 [0, 100] 这个范围
min_val = 0
max_val = 100  # 我们数据中的最大值

step_colors = ['blue', 'cyan', 'yellow', 'red']
step_index = [0, 25, 50, 75, 100]
norm_index = [i / max_val for i in step_index]

colormap = cm.StepColormap(
    step_colors,
    index=step_index,
    vmin=min_val,  # 确保 vmin 和 vmax 与数据范围一致
    vmax=max_val
)
colormap.caption = '热力图强度 (范围 0 到 100, 分步)'


gradient_map = {}

# 设置第一个颜色
gradient_map[norm_index[0]] = step_colors[0]  # 0.0 = 'blue'
# 遍历中间的断点
for i in range(1, len(step_colors)):
    color_stop = norm_index[i]
    prev_color = step_colors[i - 1]
    curr_color = step_colors[i]
    gradient_map[color_stop - 0.0001] = prev_color
    gradient_map[color_stop] = curr_color
# 设置最后一个颜色
gradient_map[norm_index[-1]] = step_colors[-1]
print(gradient_map)

m = folium.Map(location=[40.75, -73.98], zoom_start=12, tiles='cartodbdarkmatter')

HeatMap(
    heatmap_data,  # 传入我们的原始数据
    name='热力图层',
    radius=30,  # 半径 (像素)
    blur=20,  # 模糊度 (像素)
    gradient=gradient_map # 使用我们特制的分步 gradient_map
).add_to(m)

colormap.add_to(m)
folium.LayerControl().add_to(m)
st_folium(m, key="map", height=400)

st.title("Car Network")