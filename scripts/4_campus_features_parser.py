import json
import math
import os
import re
from bs4 import BeautifulSoup

print("🏫 開始執行 [步驟四]: L01 校園建築與戶外色塊解析...")

DATA_DIR = "data"
L01_SVG = os.path.join(DATA_DIR, "source", "svg", "campus", "L01_CampusLayout.svg")
A01_SVG = os.path.join(DATA_DIR, "source", "svg", "floors", "A01_map.svg")
OUTPUT_JSON = os.path.join(DATA_DIR, "generated", "campus_features.json")
CAMPUS_BUILDINGS_JSON = os.path.join(DATA_DIR, "metadata", "campus_buildings.json")

OUTDOOR_PREFIXES = ("Court-", "Lawn-", "Pool-", "Athletic-", "Landmark-")
COMPLETED_BUILDINGS = {"RB", "RB-STACK", "T1", "T4", "AU"}

INCOMPLETE_BUILDING_STYLE = {
    "fill": "rgba(255, 255, 255, 0.34)",
    "stroke": "rgba(203, 213, 225, 0.48)",
    "label_fill": "rgba(71, 85, 105, 0.76)",
}
LAWN_STYLE = {
    "fill": "rgba(187, 247, 208, 0.20)",
    "stroke": "rgba(74, 222, 128, 0.22)",
    "label_fill": "rgba(22, 101, 52, 0.56)",
}
OUTDOOR_ACTIVITY_STYLE = {
    "fill": "rgba(186, 230, 253, 0.26)",
    "stroke": "rgba(56, 189, 248, 0.28)",
    "label_fill": "rgba(3, 105, 161, 0.60)",
}
OUTDOOR_WHITE_STYLE = {
    "fill": "rgba(255, 255, 255, 0.34)",
    "stroke": "rgba(203, 213, 225, 0.48)",
    "label_fill": "rgba(71, 85, 105, 0.76)",
}


def get_label(tag):
    return (tag.get("inkscape:label") or tag.get("id") or "").strip()


def tokenize_path(path_d):
    return re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?", path_d or "")


def is_command(token):
    return re.fullmatch(r"[MmLlHhVvCcSsQqTtAaZz]", token or "") is not None


def cubic_point(p0, p1, p2, p3, t):
    mt = 1.0 - t
    return [
        mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0],
        mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1],
    ]


def quadratic_point(p0, p1, p2, t):
    mt = 1.0 - t
    return [
        mt**2 * p0[0] + 2 * mt * t * p1[0] + t**2 * p2[0],
        mt**2 * p0[1] + 2 * mt * t * p1[1] + t**2 * p2[1],
    ]


def parse_svg_path_to_points(path_d):
    tokens = tokenize_path(path_d)
    if not tokens:
        return []

    points = []
    i = 0
    cmd = None
    current = [0.0, 0.0]
    start = None
    last_cubic_ctrl = None
    last_quad_ctrl = None

    def read_number():
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    def has_number(count=1):
        return i + count - 1 < len(tokens) and not is_command(tokens[i])

    def add_point(point):
        nonlocal current
        current = [float(point[0]), float(point[1])]
        points.append(current.copy())

    while i < len(tokens):
        token = tokens[i]
        if is_command(token):
            cmd = token
            i += 1
        elif cmd is None:
            raise ValueError(f"path d 解析失敗，缺少命令: {path_d}")

        if cmd in ("M", "m"):
            is_relative = cmd == "m"
            first = True
            while has_number(2):
                x, y = read_number(), read_number()
                point = [current[0] + x, current[1] + y] if is_relative else [x, y]
                add_point(point)
                if first:
                    start = current.copy()
                    first = False
                    cmd = "l" if is_relative else "L"
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif cmd in ("L", "l"):
            is_relative = cmd == "l"
            while has_number(2):
                x, y = read_number(), read_number()
                add_point([current[0] + x, current[1] + y] if is_relative else [x, y])
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif cmd in ("H", "h"):
            is_relative = cmd == "h"
            while has_number():
                x = read_number()
                add_point([current[0] + x, current[1]] if is_relative else [x, current[1]])
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif cmd in ("V", "v"):
            is_relative = cmd == "v"
            while has_number():
                y = read_number()
                add_point([current[0], current[1] + y] if is_relative else [current[0], y])
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif cmd in ("C", "c"):
            is_relative = cmd == "c"
            while has_number(6):
                p0 = current.copy()
                vals = [read_number() for _ in range(6)]
                if is_relative:
                    p1 = [p0[0] + vals[0], p0[1] + vals[1]]
                    p2 = [p0[0] + vals[2], p0[1] + vals[3]]
                    p3 = [p0[0] + vals[4], p0[1] + vals[5]]
                else:
                    p1, p2, p3 = [vals[0], vals[1]], [vals[2], vals[3]], [vals[4], vals[5]]
                for step in range(1, 9):
                    add_point(cubic_point(p0, p1, p2, p3, step / 8))
                last_cubic_ctrl = p2
                last_quad_ctrl = None
        elif cmd in ("S", "s"):
            is_relative = cmd == "s"
            while has_number(4):
                p0 = current.copy()
                p1 = [2 * p0[0] - last_cubic_ctrl[0], 2 * p0[1] - last_cubic_ctrl[1]] if last_cubic_ctrl else p0.copy()
                vals = [read_number() for _ in range(4)]
                if is_relative:
                    p2 = [p0[0] + vals[0], p0[1] + vals[1]]
                    p3 = [p0[0] + vals[2], p0[1] + vals[3]]
                else:
                    p2, p3 = [vals[0], vals[1]], [vals[2], vals[3]]
                for step in range(1, 9):
                    add_point(cubic_point(p0, p1, p2, p3, step / 8))
                last_cubic_ctrl = p2
                last_quad_ctrl = None
        elif cmd in ("Q", "q"):
            is_relative = cmd == "q"
            while has_number(4):
                p0 = current.copy()
                vals = [read_number() for _ in range(4)]
                if is_relative:
                    p1 = [p0[0] + vals[0], p0[1] + vals[1]]
                    p2 = [p0[0] + vals[2], p0[1] + vals[3]]
                else:
                    p1, p2 = [vals[0], vals[1]], [vals[2], vals[3]]
                for step in range(1, 7):
                    add_point(quadratic_point(p0, p1, p2, step / 6))
                last_quad_ctrl = p1
                last_cubic_ctrl = None
        elif cmd in ("T", "t"):
            is_relative = cmd == "t"
            while has_number(2):
                p0 = current.copy()
                p1 = [2 * p0[0] - last_quad_ctrl[0], 2 * p0[1] - last_quad_ctrl[1]] if last_quad_ctrl else p0.copy()
                x, y = read_number(), read_number()
                p2 = [p0[0] + x, p0[1] + y] if is_relative else [x, y]
                for step in range(1, 7):
                    add_point(quadratic_point(p0, p1, p2, step / 6))
                last_quad_ctrl = p1
                last_cubic_ctrl = None
        elif cmd in ("A", "a"):
            is_relative = cmd == "a"
            while has_number(7):
                vals = [read_number() for _ in range(7)]
                end = [current[0] + vals[5], current[1] + vals[6]] if is_relative else [vals[5], vals[6]]
                add_point(end)
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif cmd in ("Z", "z"):
            if start is not None:
                add_point(start)
            cmd = None
            last_cubic_ctrl = None
            last_quad_ctrl = None
        else:
            raise ValueError(f"目前不支援的 path 命令: {cmd}")

    cleaned = []
    for point in points:
        rounded = [round(point[0], 3), round(point[1], 3)]
        if not cleaned or cleaned[-1] != rounded:
            cleaned.append(rounded)
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    return cleaned


def extract_points(el):
    if el.name == "polygon" and el.has_attr("points"):
        raw_points = re.findall(r"([-\d.]+)[,\s]+([-\d.]+)", el["points"])
        return [[float(x), float(y)] for x, y in raw_points]
    if el.name == "path" and el.has_attr("d"):
        return parse_svg_path_to_points(el["d"])
    return []


def load_svg(path):
    if not os.path.exists(path):
        print(f"❌ 錯誤：找不到 {path}")
        raise SystemExit(1)
    with open(path, "r", encoding="utf-8") as file:
        return BeautifulSoup(file, "xml")


def load_campus_buildings_metadata():
    if not os.path.exists(CAMPUS_BUILDINGS_JSON):
        return {"default_floor_height_m": 3.8, "buildings": {}}
    with open(CAMPUS_BUILDINGS_JSON, "r", encoding="utf-8") as file:
        return json.load(file)


def extract_building_anchors(soup):
    anchors = {}
    for circle in soup.find_all("circle"):
        label = get_label(circle)
        if not label.startswith("Building-"):
            continue
        if label in anchors:
            continue
        anchors[label] = [float(circle.get("cx")), float(circle.get("cy"))]
    return anchors


def solve_similarity_transform(source_points, target_points):
    n = len(source_points)
    if n < 2:
        raise ValueError("至少需要 2 個共用 Building-* anchor 才能解出 L01 -> A01 transform")

    src_mean = [
        sum(point[0] for point in source_points) / n,
        sum(point[1] for point in source_points) / n,
    ]
    dst_mean = [
        sum(point[0] for point in target_points) / n,
        sum(point[1] for point in target_points) / n,
    ]

    denom = 0.0
    a_num = 0.0
    b_num = 0.0
    for src, dst in zip(source_points, target_points):
        x = src[0] - src_mean[0]
        y = src[1] - src_mean[1]
        X = dst[0] - dst_mean[0]
        Y = dst[1] - dst_mean[1]
        denom += x * x + y * y
        a_num += x * X + y * Y
        b_num += x * Y - y * X

    if denom == 0:
        raise ValueError("共用 anchor 重疊，無法計算 transform")

    a = a_num / denom
    b = b_num / denom
    tx = dst_mean[0] - a * src_mean[0] + b * src_mean[1]
    ty = dst_mean[1] - b * src_mean[0] - a * src_mean[1]

    return {
        "a": a,
        "b": b,
        "tx": tx,
        "ty": ty,
        "scale": math.sqrt(a * a + b * b),
        "rotation_degrees": math.degrees(math.atan2(b, a)),
    }


def apply_transform(point, transform):
    x, y = point
    a = transform["a"]
    b = transform["b"]
    return [
        round(a * x - b * y + transform["tx"], 3),
        round(b * x + a * y + transform["ty"], 3),
    ]


def is_green_outdoor_feature(label):
    lower_label = label.lower()
    return lower_label.startswith("lawn-") or lower_label.startswith("court-")


def is_white_outdoor_feature(label):
    return label.lower() == "athletic-field"


def get_building_massing(label, metadata):
    buildings = metadata.get("buildings", {})
    entry = buildings.get(label, {})
    default_floor_height = float(metadata.get("default_floor_height_m") or 3.8)
    floor_height = float(entry.get("floor_height_m") or default_floor_height)
    floors = entry.get("floors")
    height_m = entry.get("height_m")

    if height_m is None and floors is not None:
        height_m = float(floors) * floor_height

    if height_m is None:
        height_m = 0

    return {
        "display_name": entry.get("display_name"),
        "floors": floors,
        "floor_height_m": floor_height,
        "height_m": round(float(height_m), 2),
        "height_z": round(float(height_m) * 100, 2),
        "status": entry.get("status", "footprint_only"),
    }


def classify_feature(label, metadata):
    if label.startswith("floor-"):
        building = label.replace("floor-", "", 1).upper()
        if building in COMPLETED_BUILDINGS:
            return None
        massing = get_building_massing(label, metadata)
        return {
            "category": "building",
            "name": massing["display_name"] or building,
            "massing": massing,
            **INCOMPLETE_BUILDING_STYLE,
        }
    if label.startswith(OUTDOOR_PREFIXES):
        if is_white_outdoor_feature(label):
            style = OUTDOOR_WHITE_STYLE
        elif is_green_outdoor_feature(label):
            style = LAWN_STYLE
        else:
            style = OUTDOOR_ACTIVITY_STYLE
        return {
            "category": "outdoor",
            "name": label,
            **style,
        }
    return None


l01_soup = load_svg(L01_SVG)
a01_soup = load_svg(A01_SVG)
campus_buildings_metadata = load_campus_buildings_metadata()

l01_anchors = extract_building_anchors(l01_soup)
a01_anchors = extract_building_anchors(a01_soup)
common_anchor_ids = sorted(set(l01_anchors) & set(a01_anchors))

if len(common_anchor_ids) < 2:
    print("❌ 錯誤：L01 與 A01 共用 Building-* anchor 少於 2 個，無法穩定對齊。")
    print(f"   共用 anchors: {common_anchor_ids}")
    raise SystemExit(1)

transform = solve_similarity_transform(
    [l01_anchors[key] for key in common_anchor_ids],
    [a01_anchors[key] for key in common_anchor_ids],
)

features = []
for el in l01_soup.find_all(lambda tag: tag.name in ("polygon", "path")):
    label = get_label(el)
    feature_info = classify_feature(label, campus_buildings_metadata)
    if not feature_info:
        continue

    points = extract_points(el)
    if len(points) < 3:
        print(f"⚠️ 略過 {label}：解析座標少於 3 點")
        continue

    transformed_points = [apply_transform(point, transform) for point in points]
    features.append({
        "id": label,
        "label": label,
        "source": "L01_CampusLayout.svg",
        **feature_info,
        "points": transformed_points,
    })

payload = {
    "source": L01_SVG,
    "target_coordinate_space": "A01_map.svg",
    "matched_anchors": common_anchor_ids,
    "transform": {
        key: round(value, 8) for key, value in transform.items()
    },
    "features": features,
}

with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
    json.dump(payload, file, indent=2, ensure_ascii=False)

building_count = sum(1 for feature in features if feature["category"] == "building")
outdoor_count = sum(1 for feature in features if feature["category"] == "outdoor")
print("✅ [步驟四] 執行完畢！")
print(f"📊 共用 anchors: {', '.join(common_anchor_ids)}")
print(f"📊 解析校園建築 footprint {building_count} 個 | 戶外色塊 {outdoor_count} 個")
print(f"📁 已寫入 {OUTPUT_JSON}")
