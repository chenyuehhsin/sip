import json
import math
import os
import re
from bs4 import BeautifulSoup

# 比例尺常數 (Pixel to Meter)
# RB-B104 (356, 673) 到 RB-B105 (299, 674) 校準為 500 cm。
SCALE_FACTOR = 5.0 / math.sqrt((356 - 299)**2 + (673 - 674)**2)
CAMPUS_NODE_PREFIXES = ("Gate-", "Path-", "CoveredPath-", "Building-", "Lawn-", "Pool-", "Court-")
CAMPUS_LANDMARK_COLOR = "#d8c27a"
CAMPUS_LANDMARK_SOURCE_COLORS = ("#ffff00", CAMPUS_LANDMARK_COLOR)
WATER_FOUNTAIN_COLOR = "#00ffff"
WATER_FOUNTAIN_CATEGORY = "water_fountain"
WATER_FOUNTAIN_PATTERN = re.compile(r'^[A-Z0-9-]+-[B]?\d+(?:-\d+)?F-WF-\d+$', re.IGNORECASE)

print("🚀 開始執行 [步驟一]: 全新多樓層 SVG 融合解析管線...")

# ==========================================
# 1. 檔名與樓層對應字典 (支援夾層與地下室)
# ==========================================
def parse_floor_from_filename(filename):
    base = filename.replace("_map.svg", "").upper()
    match = re.match(r'^A(\d+)(?:-(\d+))?$', base)
    if match:
        main_val = int(match.group(1))
        sub_val = match.group(2)
        if main_val == 0:
            return -1.0, "B1"  # B1 地下室
        if sub_val:
            # 夾層，例如 A02-1 對應到數值 2.5 樓，名稱 "2-1"
            return main_val + 0.5, f"{main_val}-1"
        return float(main_val), str(main_val)
    return 1.0, "1"

# ==========================================
# 2. 萃取建築與樓層的強健解析函數 (支援 Contextual Fallback)
# ==========================================
def extract_building_and_floor(node_id, default_building, default_floor, default_floor_name):
    node_id = str(node_id).strip()
    building = default_building
    floor = default_floor
    floor_name = default_floor_name

    # 🌟 A. 優先檢查跨棟傳送門命名 (例如 C-T1-4F-to-RB-3F)
    # 只用 "-to-" 前面的端點判斷，並從端點尾端取樓層，避免 RB-Stack-7F
    # 被拆成 building=RB / floor=Stack-7 之後退回 1F。
    match_bridge = re.match(r'^C-(.+?)-to-', node_id, re.IGNORECASE)
    if match_bridge:
        from_endpoint = match_bridge.group(1)
        match_from_floor = re.match(r'^(.+)-([B]?\d+(?:-\d+)?)F$', from_endpoint, re.IGNORECASE)
        if not match_from_floor:
            return building, floor, floor_name

        parsed_building = match_from_floor.group(1).upper()
        floor_str = match_from_floor.group(2).upper()

        building = parsed_building

        if floor_str == "B1" or floor_str == "-1":
            floor = -1.0
            floor_name = "B1"
        elif "-" in floor_str:
            try:
                parts = floor_str.split('-')
                floor = float(parts[0]) + 0.5
                floor_name = floor_str
            except ValueError:
                floor = 1.0
                floor_name = "1"
        else:
            try:
                floor = float(floor_str)
                floor_name = str(int(floor))
            except ValueError:
                floor = 1.0
                floor_name = "1"
        return building, floor, floor_name

    # 🌟 B. 一般實體大樓識別 (納入 RB-STACK, AU 獨立命名空間)
    match_b = re.match(r'^(RB-STACK|RB|T1|T4|AU)', node_id, re.IGNORECASE)
    if match_b:
        building = match_b.group(1).upper()

    # 🌟 C. 精確判斷樓層後綴
    match_floor = re.search(r'-([B]?\d+(?:-\d+)?)F(?:$|-)', node_id, re.IGNORECASE)
    if match_floor:
        floor_str = match_floor.group(1).upper()
        if floor_str.startswith('B'):
            floor = -float(floor_str[1:])
            floor_name = floor_str
        elif "-" in floor_str:
            parts = floor_str.split('-')
            floor = float(parts[0]) + 0.5
            floor_name = floor_str
        else:
            floor = float(floor_str)
            floor_name = str(int(floor))
    else:
        # 🌟 D. 智慧房號推斷退路
        match_room = re.search(r'\b(B)?(\d)(\d{2})\b', node_id, re.IGNORECASE)
        if match_room:
            is_basement = match_room.group(1) is not None
            floor_num = int(match_room.group(2))
            if is_basement:
                floor = -float(floor_num)
                floor_name = f"B{floor_num}"
            else:
                floor = float(floor_num)
                floor_name = str(floor_num)

    return building, floor, floor_name

# ==========================================
# 3. 樓板 SVG 幾何解析工具
# ==========================================
def get_floor_label(tag):
    return (tag.get('inkscape:label') or tag.get('id') or '').strip()


def get_circle_label(tag):
    return (tag.get('inkscape:label') or tag.get('id') or '').strip()


def get_svg_style_text(tag):
    return (tag.get('fill', '') + ';' + tag.get('style', '')).lower()


def is_water_fountain_label(label):
    return bool(WATER_FOUNTAIN_PATTERN.match(str(label).strip()))


def parse_svg_path_to_points(path_d):
    """
    支援常見直線 path：M/m, L/l, H/h, V/v, Z/z
    你的 floor-T4 / floor-T1 這種 path 可解析。
    """
    tokens = re.findall(r'[MmLlHhVvZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?', path_d)
    if not tokens:
        return []

    points = []
    i = 0
    cmd = None
    current = [0.0, 0.0]
    start = None

    def read_number(idx):
        return float(tokens[idx]), idx + 1

    while i < len(tokens):
        token = tokens[i]
        if re.fullmatch(r'[MmLlHhVvZz]', token):
            cmd = token
            i += 1
        elif cmd is None:
            raise ValueError(f"path d 解析失敗，缺少命令: {path_d}")

        if cmd in ('M', 'L'):
            while i + 1 < len(tokens) and not re.fullmatch(r'[MmLlHhVvZz]', tokens[i]):
                x, i = read_number(i)
                y, i = read_number(i)
                current = [x, y]
                if start is None:
                    start = current.copy()
                points.append(current.copy())
                if cmd == 'M':
                    cmd = 'L'
        elif cmd in ('m', 'l'):
            while i + 1 < len(tokens) and not re.fullmatch(r'[MmLlHhVvZz]', tokens[i]):
                dx, i = read_number(i)
                dy, i = read_number(i)
                current = [current[0] + dx, current[1] + dy]
                if start is None:
                    start = current.copy()
                points.append(current.copy())
                if cmd == 'm':
                    cmd = 'l'
        elif cmd == 'H':
            while i < len(tokens) and not re.fullmatch(r'[MmLlHhVvZz]', tokens[i]):
                x, i = read_number(i)
                current = [x, current[1]]
                points.append(current.copy())
        elif cmd == 'h':
            while i < len(tokens) and not re.fullmatch(r'[MmLlHhVvZz]', tokens[i]):
                dx, i = read_number(i)
                current = [current[0] + dx, current[1]]
                points.append(current.copy())
        elif cmd == 'V':
            while i < len(tokens) and not re.fullmatch(r'[MmLlHhVvZz]', tokens[i]):
                y, i = read_number(i)
                current = [current[0], y]
                points.append(current.copy())
        elif cmd == 'v':
            while i < len(tokens) and not re.fullmatch(r'[MmLlHhVvZz]', tokens[i]):
                dy, i = read_number(i)
                current = [current[0], current[1] + dy]
                points.append(current.copy())
        elif cmd in ('Z', 'z'):
            if start is not None:
                points.append(start.copy())
            cmd = None
        else:
            raise ValueError(f"目前不支援的 path 命令: {cmd}")

    cleaned = []
    for p in points:
        if not cleaned or cleaned[-1] != p:
            cleaned.append(p)
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    return cleaned


def extract_floor_points(el):
    if el.name == 'polygon' and el.has_attr('points'):
        raw_points = re.findall(r'([-\d.]+)[,\s]+([-\d.]+)', el['points'])
        return [[float(p[0]), float(p[1])] for p in raw_points]

    if el.name == 'path' and el.has_attr('d'):
        try:
            return parse_svg_path_to_points(el['d'])
        except ValueError as e:
            print(f"⚠️ 無法解析樓板 {get_floor_label(el)}: {e}")
            return []

    return []


# ==========================================
# 4. L01 校園節點解析與座標對齊工具
# ==========================================
def extract_building_anchors(soup):
    anchors = {}
    for circle in soup.find_all('circle'):
        label = get_circle_label(circle)
        if not label.startswith('Building-') or label in anchors:
            continue
        anchors[label] = [float(circle.get('cx')), float(circle.get('cy'))]
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

    return {"a": a, "b": b, "tx": tx, "ty": ty}


def apply_transform(point, transform):
    x, y = point
    a = transform["a"]
    b = transform["b"]
    return [
        a * x - b * y + transform["tx"],
        b * x + a * y + transform["ty"],
    ]


def extract_campus_building_code(label):
    raw = label.replace("Building-", "", 1)
    parts = raw.split("-")
    if len(parts) > 1 and parts[-1].isdigit():
        parts = parts[:-1]
    return "-".join(parts).upper() if parts else "CAMPUS"


def classify_campus_node(label):
    if label.startswith("Gate-"):
        return {
            "building": "Campus",
            "subtype": "gate",
            "color": "#ff9955",
        }
    if label.startswith("Path-"):
        return {
            "building": "Campus",
            "subtype": "outdoor_path",
            "color": "#ff5555",
        }
    if label.startswith("CoveredPath-"):
        return {
            "building": "Campus",
            "subtype": "covered_path",
            "color": "#10b981",
        }
    if label.startswith("Building-"):
        return {
            "building": extract_campus_building_code(label),
            "subtype": "building_entry",
            "color": "#0ea5e9",
        }
    if label.startswith("Lawn-"):
        return {
            "building": "Campus",
            "subtype": "lawn",
            "color": CAMPUS_LANDMARK_COLOR,
        }
    if label.startswith("Pool-"):
        return {
            "building": "Campus",
            "subtype": "pool",
            "color": CAMPUS_LANDMARK_COLOR,
        }
    if label.startswith("Court-"):
        return {
            "building": "Campus",
            "subtype": "court",
            "color": CAMPUS_LANDMARK_COLOR,
        }
    return None


def is_campus_landmark_color(circle):
    style_text = get_svg_style_text(circle)
    return any(color in style_text for color in CAMPUS_LANDMARK_SOURCE_COLORS)


def is_campus_node_candidate(circle):
    label = get_circle_label(circle)
    if label.startswith(CAMPUS_NODE_PREFIXES):
        return True
    return is_campus_landmark_color(circle)


def parse_campus_nodes(data_dir, existing_node_ids):
    l01_path = os.path.join(data_dir, "L01_CampusLayout.svg")
    a01_path = os.path.join(data_dir, "A01_map.svg")
    if not os.path.exists(l01_path):
        print(f"⚠️ 警告：找不到 {l01_path}，略過 L01 校園節點解析。")
        return []
    if not os.path.exists(a01_path):
        print(f"⚠️ 警告：找不到 {a01_path}，略過 L01 校園節點對齊。")
        return []

    with open(l01_path, 'r', encoding='utf-8') as file:
        l01_soup = BeautifulSoup(file, 'xml')
    with open(a01_path, 'r', encoding='utf-8') as file:
        a01_soup = BeautifulSoup(file, 'xml')

    l01_anchors = extract_building_anchors(l01_soup)
    a01_anchors = extract_building_anchors(a01_soup)
    common_anchor_ids = sorted(set(l01_anchors) & set(a01_anchors))
    if len(common_anchor_ids) < 2:
        print("⚠️ 警告：L01 與 A01 共用 Building-* anchor 少於 2 個，略過 L01 校園節點解析。")
        print(f"   共用 anchors: {common_anchor_ids}")
        return []

    transform = solve_similarity_transform(
        [l01_anchors[key] for key in common_anchor_ids],
        [a01_anchors[key] for key in common_anchor_ids],
    )

    campus_nodes = []
    seen_ids = set(existing_node_ids)
    duplicate_ids = []
    for circle in l01_soup.find_all('circle'):
        label = get_circle_label(circle)
        if not label or not is_campus_node_candidate(circle):
            continue

        classification = classify_campus_node(label)
        if not classification and is_campus_landmark_color(circle):
            classification = {
                "building": "Campus",
                "subtype": "campus_landmark",
                "color": CAMPUS_LANDMARK_COLOR,
            }
        if not classification:
            continue

        if label in seen_ids:
            duplicate_ids.append(label)
            continue
        seen_ids.add(label)

        source_x = float(circle.get('cx'))
        source_y = float(circle.get('cy'))
        x, y = apply_transform([source_x, source_y], transform)
        campus_nodes.append({
            "id": label,
            "building": classification["building"],
            "floor": 0.0,
            "floor_name": "L01",
            "x": round(x),
            "y": round(y),
            "type": "routing_node",
            "scope": "campus",
            "subtype": classification["subtype"],
            "color": classification["color"],
            "source": "L01_CampusLayout.svg",
            "source_x": round(source_x, 3),
            "source_y": round(source_y, 3),
        })

    if duplicate_ids:
        unique_duplicates = sorted(set(duplicate_ids))
        print(f"⚠️ L01 校園節點略過 {len(duplicate_ids)} 個重複 ID: {', '.join(unique_duplicates)}")

    print(f"  🏫 解析 L01_CampusLayout.svg -> 校園 Node {len(campus_nodes)} 個 | 共用 anchors {len(common_anchor_ids)} 個")
    return campus_nodes

# ==========================================
# 5. 多 SVG 自動化掃描與解析
# ==========================================
routing_nodes = []
pois = []
slabs_data = {}

data_dir = 'data'
if not os.path.exists(data_dir):
    print(f"❌ 錯誤：找不到 {data_dir} 資料夾！")
    exit(1)

svg_files = [f for f in os.listdir(data_dir) if f.startswith('A') and f.endswith('_map.svg')]
if not svg_files:
    print("⚠️ 警告：data/ 資料夾下沒有找到任何 A*_map.svg 地圖檔案！")
    exit(1)

print(f"📂 偵測到 {len(svg_files)} 個樓層地圖檔案，開始進行解析...")

for svg_file in sorted(svg_files):
    filepath = os.path.join(data_dir, svg_file)
    default_floor, default_floor_name = parse_floor_from_filename(svg_file)
    default_building = "Unknown"

    print(f"  📖 解析 {svg_file} -> 預設樓層: {default_floor_name} (數值: {default_floor})")

    with open(filepath, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'xml')

    for circle in soup.find_all('circle'):
        label = circle.get('inkscape:label') or circle.get('id')
        if label:
            label = label.strip()
            if label.startswith('Building-'):
                continue

            cx = round(float(circle.get('cx')))
            cy = round(float(circle.get('cy')))

            # 色彩與風格萃取
            attr_str = (circle.get('fill', '') + circle.get('style', '')).lower()
            building, floor, floor_name = extract_building_and_floor(label, default_building, default_floor, default_floor_name)

            node_data = {
                "id": label,
                "building": building,
                "floor": floor,
                "floor_name": floor_name,
                "x": cx,
                "y": cy
            }

            # 依色彩進行圖學渲染分層歸類
            if is_water_fountain_label(label):
                node_data["color"] = WATER_FOUNTAIN_COLOR
                node_data["type"] = "poi"
                node_data["category"] = WATER_FOUNTAIN_CATEGORY
                node_data["name_zh"] = "飲水機"
                node_data["public_access"] = "public"
                node_data["source"] = "floor_plan"
                node_data["status"] = "active"
                node_data["subtype"] = WATER_FOUNTAIN_CATEGORY
                pois.append(node_data)
            elif '#ff9955' in attr_str:
                node_data["color"] = "#ff9955"
                node_data["type"] = "poi"
                pois.append(node_data)
            else:
                if '#ff5555' in attr_str:
                    node_data["color"] = "#ff5555"
                elif '#9b59b6' in attr_str or '#5599ff' in attr_str or '#0ea5e9' in attr_str or '#38bdf8' in attr_str:
                    node_data["color"] = "#0ea5e9"
                elif '#87de87' in attr_str or '#10b981' in attr_str:
                    node_data["color"] = "#10b981"
                else:
                    node_data["color"] = "#999999"
                node_data["type"] = "routing_node"
                routing_nodes.append(node_data)

    # ✅ 修正 1：抓 inkscape:label 或 id，以 floor- 開頭的 polygon/path
    floor_elements = soup.find_all(
        lambda tag: tag.name in ('polygon', 'path') and get_floor_label(tag).lower().startswith('floor-')
    )

    for el in floor_elements:
        # ✅ 修正 2：真正使用 label，例如 floor-T4 / floor-RB-STACK
        floor_label = get_floor_label(el)
        bldg_name = floor_label.replace('floor-', '').upper()

        # ✅ 修正 3：同時支援 polygon 與 path
        points_array = extract_floor_points(el)

        if points_array:
            slabs_data[bldg_name] = points_array
        else:
            print(f"⚠️ 樓板 {floor_label} 沒有成功解析出座標")

existing_node_ids = {node["id"] for node in routing_nodes}
routing_nodes.extend(parse_campus_nodes(data_dir, existing_node_ids))


def collect_edge_rows(edge_payload, source_name, default_type=None):
    if isinstance(edge_payload, dict):
        groups = edge_payload.items()
    elif isinstance(edge_payload, list):
        groups = [(source_name, edge_payload)]
    else:
        print(f"⚠️ {source_name} 格式錯誤：edge 檔必須是 object 或 array，已略過。")
        return []

    edge_rows = []
    skipped_count = 0
    for group_name, edges_list in groups:
        if not isinstance(edges_list, list):
            print(f"⚠️ {source_name} / {group_name} 不是 edge array，已略過。")
            continue
        for edge_data in edges_list:
            if not isinstance(edge_data, list) or len(edge_data) < 2:
                skipped_count += 1
                continue
            start_id = str(edge_data[0]).strip()
            end_id = str(edge_data[1]).strip()
            edge_type = str(edge_data[2]).strip() if len(edge_data) > 2 and str(edge_data[2]).strip() else default_type
            if not start_id or not end_id or not edge_type:
                skipped_count += 1
                continue
            edge_rows.append([start_id, end_id, edge_type])

    if skipped_count:
        print(f"⚠️ {source_name} 略過 {skipped_count} 筆 schema 不完整的 edge。")
    return edge_rows


def edge_key(edge_data):
    return tuple(sorted((edge_data[0], edge_data[1])))


# ==========================================
# 6. 讀取 raw_edges.json 與可選 campus_edges_draft.json，並依跨樓層邏輯解算
# ==========================================
edges = []
raw_edges = []
try:
    with open('data/raw_edges.json', 'r', encoding='utf-8') as f:
        grouped_edges = json.load(f)
    raw_edges.extend(collect_edge_rows(grouped_edges, "raw_edges.json", default_type="walkway"))
except FileNotFoundError:
    print("⚠️ 警告：找不到 data/raw_edges.json，骨幹連線為空。")

campus_draft_edges_path = os.path.join(data_dir, "campus_edges_draft.json")
if os.path.exists(campus_draft_edges_path):
    try:
        with open(campus_draft_edges_path, 'r', encoding='utf-8') as f:
            campus_draft_payload = json.load(f)
        campus_draft_edges = collect_edge_rows(campus_draft_payload, "campus_edges_draft.json")
        existing_edge_keys = {edge_key(edge_data) for edge_data in raw_edges}
        unique_campus_draft_edges = []
        duplicate_count = 0
        for edge_data in campus_draft_edges:
            key = edge_key(edge_data)
            if key in existing_edge_keys:
                duplicate_count += 1
                continue
            existing_edge_keys.add(key)
            unique_campus_draft_edges.append(edge_data)
        raw_edges.extend(unique_campus_draft_edges)
        print(f"  🧩 合併 campus_edges_draft.json -> Edge {len(unique_campus_draft_edges)} 條" + (f" | 略過重複 {duplicate_count} 條" if duplicate_count else ""))
    except json.JSONDecodeError as e:
        print(f"⚠️ campus_edges_draft.json JSON 格式錯誤，已略過: {e}")

missing_edge_count = 0
for edge_data in raw_edges:
    start_id = edge_data[0]
    end_id = edge_data[1]
    edge_type = edge_data[2]

    n1 = next((n for n in routing_nodes if n['id'] == start_id), None)
    n2 = next((n for n in routing_nodes if n['id'] == end_id), None)

    if n1 and n2:
        # 跨樓層 (垂直動線) 核心權重算式
        if n1['floor'] != n2['floor'] and edge_type in ["stair", "elevator"]:
            floor_diff = abs(n1['floor'] - n2['floor'])
            distance = round(floor_diff * 10.0, 2)
        else:
            pixel_dist = math.sqrt((n2['x'] - n1['x'])**2 + (n2['y'] - n1['y'])**2)
            distance = round(pixel_dist * SCALE_FACTOR, 2)

        edges.append({
            "from": start_id,
            "to": end_id,
            "distance": distance,
            "type": edge_type
        })
    else:
        missing_edge_count += 1

if missing_edge_count:
    print(f"⚠️ Edge 略過 {missing_edge_count} 條：找不到對應 node。")

# ==========================================
# 7. 輸出至獨立 JSON
# ==========================================
routing_graph = {
    "nodes": routing_nodes,
    "edges": edges
}

with open('data/routing_nodes.json', 'w', encoding='utf-8') as f:
    json.dump(routing_graph, f, indent=2, ensure_ascii=False)
with open('data/pois.json', 'w', encoding='utf-8') as f:
    json.dump(pois, f, indent=2, ensure_ascii=False)
with open('data/slabs.json', 'w', encoding='utf-8') as f:
    json.dump(slabs_data, f, indent=2, ensure_ascii=False)

print("✅ [步驟一] 執行完畢！")
campus_node_count = sum(1 for node in routing_nodes if node.get("scope") == "campus")
indoor_node_count = len(routing_nodes) - campus_node_count
print(f"📊 統計：總計融合 {len(svg_files)} 個樓層 | 室內 Node {indoor_node_count} 個 | 校園 Node {campus_node_count} 個 | Edge {len(edges)} 條 | POI {len(pois)} 個 | 解析樓板 {len(slabs_data)} 棟")
