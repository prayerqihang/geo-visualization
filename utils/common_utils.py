def hex_to_rgba(hex_color, alpha=1.0):
    """
    将 HEX 颜色（例如 "#FF0000"）转换为 [R, G, B, A]
    """
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return [rgb[0], rgb[1], rgb[2], int(alpha * 255)]


def extract_geojson_coordinates(geojson_data):
    """
    从 GeoJSON FeatureCollection 中提取所有坐标点，为了配合 PyDeck 计算视图
    """
    points = []
    if not geojson_data or "features" not in geojson_data:
        print("警告：GeoJSON 数据中没有包含任何 Features！")
        return points

    for feature in geojson_data["features"]:
        geom = feature.get("geometry")
        if not geom: continue

        coordinates = geom.get("coordinates")
        geom_type = geom.get("type")

        if geom_type == "Polygon":  # 坐标形式 [[[lon, lat], ...]]
            # 只需要外环的点来确定边界；排除所有的内部洞
            points.extend(coordinates[0])
        elif geom_type == "MultiPolygon":  # 坐标格式 [[[[lon, lat], ...]]]
            # 只需要每一个多边形的外环点
            for polygon in coordinates:
                points.extend(polygon[0])
        elif geom_type == "Point":  # 坐标格式 [lon, lat]
            points.append(coordinates)
        elif geom_type == "MultiPoint":  # 坐标格式 [[lon, lat], ...]
            points.extend(coordinates)
        elif geom_type == "LineString":  # 坐标格式 [[lon, lat], ...]
            points.extend(coordinates)
        elif geom_type == "MultiLineString":  # 坐标格式 [[[lon, lat], ...]]
            for line in coordinates:
                points.extend(line)

    return points
