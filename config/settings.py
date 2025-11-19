import os

# 根目录路径
ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

# 常用路径
ASSETS_PATH = os.path.join(ROOT_PATH, "assets")
ASSETS_ANIMATION_PATH = os.path.join(ASSETS_PATH, "animation")
ASSETS_MAP_PATH = os.path.join(ASSETS_PATH, "map")

DATA_PATH = os.path.join(ROOT_PATH, "data")
DATA_CITY_PATH = os.path.join(DATA_PATH, "city")
DATA_NETWORK_PATH = os.path.join(DATA_PATH, "network")

# 常量
# mapbox 底图类型
MAPBOX_STYLE_MAP = {
    "街道图": "mapbox://styles/mapbox/streets-v11",
    "浅色": "mapbox://styles/mapbox/light-v10",
    "深色": "mapbox://styles/mapbox/dark-v10",
    "卫星图": "mapbox://styles/mapbox/satellite-v9",
    "卫星街道图": "mapbox://styles/mapbox/satellite-streets-v11",
    "户外": "mapbox://styles/mapbox/outdoors-v11",
}
# 色盘
# PyDeck 需要 [R, G, B, A] 格式，使用 HEX 并用函数转换
# HEX 十六进制颜色表示，6 位或 8 位，每两位依次表示 RGBA
COLOR_MAP_HEX = {
    "灰色": "#808080",
    "蓝色": "#0000FF",
    "绿色": "#008000",
    "红色": "#FF0000",
    "黄色": "#FFFF00",
    "橙色": "#FFA500",
    "紫色": "#800080",
    "黑色": "#000000",
    "白色": "#FFFFFF",
}
