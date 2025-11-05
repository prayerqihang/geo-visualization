import os

# 根目录路径
ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

# 常用路径
ASSETS_PATH = os.path.join(ROOT_PATH, "assets")
ASSETS_ANIMATION_PATH = os.path.join(ASSETS_PATH, "animation")
ASSETS_MAP_PATH = os.path.join(ASSETS_PATH, "map")

PAGES_PATH = os.path.join(ROOT_PATH, "pages")

UTILS_PATH = os.path.join(ROOT_PATH, "utils")

# 常量
# folium 底图类型
FOLIUM_MAP_TYPE = {
    "街道图 (OpenStreetMap)": "OpenStreetMap",
    "地形图 (Stamen Terrain)": "Stamen Terrain",
    "黑白图 (Stamen Toner)": "Stamen Toner",
    "亮色图 (CartoDB positron)": "CartoDB positron",
    "暗色图 (CartoDB dark_matter)": "CartoDB dark_matter",
}
