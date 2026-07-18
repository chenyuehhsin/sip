import json
import math
import os
import re
from bs4 import BeautifulSoup

# 比例尺常數 (Pixel to Meter)
SCALE_FACTOR = 0.05 

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
            return -1.0, "B1" # B1 地下室
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
    match_bridge = re.match(r'^C-(.+?)-([A-Z0-9\-]+?)F-to-', node_id, re.IGNORECASE)
    if match_bridge:
        building = match_bridge.group(1).upper()
        floor_str = match_bridge.group(2).upper()
        
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

    # 🌟 C. 精確判斷樓層後綴 (修復 RB-E1-B1F 被誤判為 1.5 的 Bug)
    # 此正則確保只抓取以「連字號」開頭，接續 B1/2/2-1，並以 F 結尾的字串
    match_floor = re.search(r'-([B]?\d+(?:-\d+)?)F(?:$|-)', node_id, re.IGNORECASE)
    if match_floor:
        floor_str = match_floor.group(1).upper()
        if floor_str.startswith('B'):
            # 處理 B1, B2 等地下室
            floor = -float(floor_str[1:])
            floor_name = floor_str
        elif "-" in floor_str:
            # 處理 2-1 等夾層
            parts = floor_str.split('-')
            floor = float(parts[0]) + 0.5
            floor_name = floor_str
        else:
            # 處理正常樓層 1, 2, 3
            floor = float(floor_str)
            floor_name = str(int(floor))
    else:
        # 🌟 D. 智慧房號推斷退路 (解救 T4-B100-1 等地下室與高樓層節點)
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
# 3. 多 SVG 自動化掃描與解析
# ==========================================
routing_nodes = []
pois = []

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
            if '#ff9955' in attr_str:
                node_data["color"] = "#ff9955"
                node_data["type"] = "poi"
                pois.append(node_data)
            else:
                if '#ff5555' in attr_str:
                    node_data["color"] = "#ff5555"
                # 🌟 垂直動線改為淺藍色 (#0ea5e9, #38bdf8 或原本的藍色系)
                elif '#9b59b6' in attr_str or '#5599ff' in attr_str or '#0ea5e9' in attr_str or '#38bdf8' in attr_str:
                    node_data["color"] = "#0ea5e9"  # 淺藍色垂直通道點
                elif '#87de87' in attr_str or '#10b981' in attr_str:
                    node_data["color"] = "#10b981"  # 綠色橋樑通道點
                else:
                    node_data["color"] = "#999999"
                node_data["type"] = "routing_node"
                routing_nodes.append(node_data)

# ==========================================
# 4. 讀取 raw_edges.json 並依跨樓層邏輯解算
# ==========================================
edges = []
try:
    with open('data/raw_edges.json', 'r', encoding='utf-8') as f:
        grouped_edges = json.load(f)
        
    raw_edges = []
    for group_name, edges_list in grouped_edges.items():
        raw_edges.extend(edges_list)
        
    for edge_data in raw_edges:
        start_id = edge_data[0]
        end_id = edge_data[1]
        edge_type = edge_data[2] if len(edge_data) > 2 else "walkway"
        
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
            pass
except FileNotFoundError:
    print("⚠️ 警告：找不到 data/raw_edges.json，骨幹連線為空。")

# ==========================================
# 5. 輸出至獨立 JSON
# ==========================================
routing_graph = {
    "nodes": routing_nodes,
    "edges": edges
}
with open('data/routing_nodes.json', 'w', encoding='utf-8') as f:
    json.dump(routing_graph, f, indent=2, ensure_ascii=False)

with open('data/pois.json', 'w', encoding='utf-8') as f:
    json.dump(pois, f, indent=2, ensure_ascii=False)

print("✅ [步驟一] 執行完畢！")
print(f"📊 統計：總計融合 {len(svg_files)} 個樓層 | 骨幹 Node {len(routing_nodes)} 個 | Edge {len(edges)} 條 | POI {len(pois)} 個")