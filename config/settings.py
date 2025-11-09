import os

# 根目录路径
ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

# 常用路径
ASSETS_PATH = os.path.join(ROOT_PATH, "assets")
ASSETS_ANIMATION_PATH = os.path.join(ASSETS_PATH, "animation")
ASSETS_MAP_PATH = os.path.join(ASSETS_PATH, "map")

DATA_PATH = os.path.join(ROOT_PATH, "data")
DATA_CITY_PATH = os.path.join(DATA_PATH, "city")

PAGES_PATH = os.path.join(ROOT_PATH, "pages")

UTILS_PATH = os.path.join(ROOT_PATH, "utils")

# 常量
# folium 底图类型
FOLIUM_MAP_TYPE = {
    "街道图": "OpenStreetMap",
    "亮色图": "Stadia.OSMBright",
    "灰白图一": "Stadia.StamenTonerLite",
    "灰白图二": "Stadia.AlidadeSmooth",
    "灰白图三": "Stadia.StamenTerrainLines",
    "暗色图一": "Stadia.AlidadeSmoothDark",
    "暗色图二": "CartoDB.DarkMatter"
}
# 色盘
COLOR_TYPE = {
    "灰色": "#808080",
    "黑色": "#000000",
    "白色": "#FFFFFF",
    "红色": "#FF0000",
    "蓝色": "#0000FF"
}
