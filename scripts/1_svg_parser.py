import json
import math
from bs4 import BeautifulSoup
import re

# 比例尺常數 (Pixel to Meter)
SCALE_FACTOR = 0.05 

print("🚀 開始執行 [步驟一]: SVG 與圖資基礎解析管線...")

# ==========================================
# 1. 萃取建築與樓層的強健解析函數 (支援明確樓層標示)
# ==========================================
def extract_building_and_floor(node_id):
    node_id = str(node_id).strip()
    building = "Unknown"
    floor = 1

    # 🌟 規則 A：優先攔截跨棟橋樑 (例如 C3-T4-T1-4F)
    match_bridge = re.match(r'^C(\d+)-([A-Za-z0-9]+)-([A-Za-z0-9]+)', node_id, re.IGNORECASE)
    if match_bridge:
        # 直接把對接的第一棟大樓 (如 T4) 抓出來當作建築歸屬
        building = match_bridge.group(2).upper() 
        
        # 尋找明確的樓層標示 (如 4F)
        match_floor = re.search(r'(\d+)F', node_id, re.IGNORECASE)
        if match_floor:
            floor = int(match_floor.group(1))
        else:
            # 備用容錯：萬一你 SVG 裡有橋樑漏了加 -4F，就用橋樑代號 C3 猜測是 3 樓
            floor = int(match_bridge.group(1))
        return building, floor

    # 🌟 規則 B：一般實體大樓解析 (例如 T4-WCM-4F, T1-400-1)
    match_b = re.match(r'^(RB|T1|T4)', node_id, re.IGNORECASE)
    if match_b:
        building = match_b.group(1).upper()

    # 判斷一般大樓的樓層
    match_floor = re.search(r'(\d+)F', node_id, re.IGNORECASE)
    if match_floor:
        floor = int(match_floor.group(1)) # 明確標示 (如 WCM-4F)
    else:
        match_room = re.search(r'(\d{3,4})', node_id)
        if match_room:
            floor = int(match_room.group(1)[:-2]) # 傳統房號推斷 (如 405 -> 4)

    return building, floor

# ==========================================
# 2. 讀取 SVG 原始檔，依「顏色」暴力分流
# ==========================================
routing_nodes = []
pois = []

try:
    with open('data/A03_map.svg', 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'xml')
except FileNotFoundError:
    print("❌ 錯誤：找不到 data/A03_map.svg，請確認檔案位置。")
    exit(1)
    
for circle in soup.find_all('circle'):
    label = circle.get('inkscape:label') or circle.get('id')
    if label:
        cx = round(float(circle.get('cx')))
        cy = round(float(circle.get('cy')))
        
        # 結合 fill 與 style 字串，確保色碼一定抓得到
        attr_str = (circle.get('fill', '') + circle.get('style', '')).lower()
        
        building, floor = extract_building_and_floor(label)
        
        # 共用的基礎節點資訊
        node_data = {
            "id": label,
            "building": building,
            "floor": floor,
            "x": cx,
            "y": cy
        }
        
        # 🎨 色彩語意分流 (Semantic Layering)
        if '#ff9955' in attr_str:
            # 🟠 橘色 -> 屬於 POI Layer
            node_data["color"] = "#ff9955"
            node_data["type"] = "poi"
            pois.append(node_data)
        else:
            # 🔴🔵🟢 其他顏色 -> 屬於 Routing Graph Layer
            if '#ff5555' in attr_str:
                node_data["color"] = "#ff5555" # 紅色走廊
            elif '#5599ff' in attr_str:
                node_data["color"] = "#5599ff" # 藍色樓梯
            elif '#87de87' in attr_str:
                node_data["color"] = "#87de87" # 綠色橋樑
            else:
                node_data["color"] = "#999999" # 防呆
            
            routing_nodes.append(node_data)

# ==========================================
# 3. 讀取 raw_edges.json 建立純粹的骨幹網路
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
        
        # 尋找兩端點 (現在這裡面 100% 不會有橘色 POI 了)
        n1 = next((n for n in routing_nodes if n['id'] == start_id), None)
        n2 = next((n for n in routing_nodes if n['id'] == end_id), None)
        
        if n1 and n2:
            pixel_dist = math.sqrt((n2['x'] - n1['x'])**2 + (n2['y'] - n1['y'])**2)
            edges.append({
                "from": start_id,
                "to": end_id,
                "distance": round(pixel_dist * SCALE_FACTOR, 2),
                "type": edge_type
            })
        else:
            print(f"⚠️ 警告：找不到骨幹節點 '{start_id}' 或 '{end_id}'，請確認 SVG 中是否遺漏該節點。")
except FileNotFoundError:
    print("⚠️ 警告：找不到 data/raw_edges.json，骨幹連線將為空。")

# ==========================================
# 4. 輸出至獨立的 JSON 檔案 (落實資料分離)
# ==========================================
# 產出 A: 純粹的導航骨幹
routing_graph = {
    "nodes": routing_nodes,
    "edges": edges
}
with open('data/routing_nodes.json', 'w', encoding='utf-8') as f:
    json.dump(routing_graph, f, indent=2, ensure_ascii=False)

# 產出 B: 獨立的興趣點 (不含連線)
with open('data/pois.json', 'w', encoding='utf-8') as f:
    json.dump(pois, f, indent=2, ensure_ascii=False)

print("✅ [步驟一] 執行完畢！")
print(f"📊 統計: 導航骨幹 Node {len(routing_nodes)} 個 | 骨幹連線 Edge {len(edges)} 條 | POI 設施 {len(pois)} 個")
print("📁 檔案已成功寫入 data/routing_nodes.json 與 data/pois.json")