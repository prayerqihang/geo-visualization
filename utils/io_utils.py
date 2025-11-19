import requests
import json


def get_geojson_from_aliyun(adcode, is_sub=False):
    """
    从阿里云 DataV 动态获取 GeoJSON 数据。
    - is_sub = False 仅获取当前 adcode 区域边界数据，不包含子区域边界。
    - is_sub = True 获取当前 adcode 区域边界数据，以及一级子区域边界。
    """
    if is_sub:
        url = f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json"
    else:
        url = f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except Exception as e:
        print(f"加载地图数据失败: {e}")
        return None


def load_lottie_file(filepath):
    """
    从指定路径加载 Lottie JSON 文件
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Lottie 文件未找到: {filepath}")
        return None
