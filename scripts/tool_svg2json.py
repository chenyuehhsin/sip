import json
import math
from bs4 import BeautifulSoup
import re

def parse_node_info(node_id):
    """
    根據建築、錯層與設施命名規則，自動萃取 Building 與 Floor。
    """
    node_id = str(node_id).strip()
    
    # 規則 1: Bridge Node (例如 C3-T4-T1, C1-RB-T4, C2-T1-T4)
    # 邏輯: 抓取 C 後面的層級數字，以及中間的主體建築
    match_bridge = re.match(r'^C(\d+)-([A-Za-z0-9]+)-([A-Za-z0-9]+)', node_id)
    if match_bridge:
        c_level = int(match_bridge.group(1))
        building = match_bridge.group(2)
        
        # 處理錯層邏輯：只有 C3 具有錯層屬性
        if c_level == 3:
            floor = 3 if building == "RB" else 4
        else:
            # C1 都是 1 樓，C2 都是 2 樓
            floor = c_level
            
        return building, floor

    # 規則 2: 垂直動線 (例如 T1-S1-4F, T1-SA-4F, RB-E-3F, RB-SB-3F)
    # 邏輯: 抓取第一段的建築，以及最後的數字(去掉F)
    match_vertical = re.match(r'^([A-Za-z0-9]+)-.*-(\d+)F$', node_id)
    if match_vertical:
        building = match_vertical.group(1)
        floor = int(match_vertical.group(2))
        return building, floor

    # 規則 3: 特殊空間/POI (例如 RB-WCM3, T1-WCF4)
    # 邏輯: 抓取第一段的建築，以及最後結尾的數字作為樓層
    match_special = re.match(r'^([A-Za-z0-9]+)-[A-Za-zA-Z]+(\d+)$', node_id)
    if match_special:
        building = match_special.group(1)
        floor = int(match_special.group(2))
        return building, floor

    # 規則 4: 一般空間與教室 (例如 T1-400-1, RB-308)
    # 邏輯: 抓取中間的房間號碼，去掉後兩位數即為樓層
    match_room = re.match(r'^([A-Za-z0-9]+)-(\d{3,4})(?:-.*)?$', node_id)
    if match_room:
        building = match_room.group(1)
        room_number = match_room.group(2)
        floor = int(room_number[:-2]) # 400 -> 4, 308 -> 3
        return building, floor

    # 規則 5: 防呆 Fallback (處理純文字走廊，例如 T1-Corridor-A)
    # 邏輯: 只抓第一段作為建築，樓層給予預設值 (建議之後避免這種命名)
    match_fallback = re.match(r'^([A-Za-z0-9]+)[-_]', node_id)
    if match_fallback:
        building = match_fallback.group(1)
        print(f"⚠️ 警告: 節點 '{node_id}' 缺乏明確樓層標示，暫時預設為 1 樓。")
        return building, 1

    # 終極防呆
    print(f"❌ 錯誤: 節點 '{node_id}' 完全不符合命名規則！已歸入 Unknown。")
    return "Unknown", 1

# ==========================================
# 測試區塊 (你可以直接在終端機跑跑看這段，確認邏輯對不對)
if __name__ == "__main__":
    test_nodes = [
        "C3-T4-T1", "C3-RB-T1",  # C3 錯層測試
        "C1-RB-T4", "C2-T1-T4",  # C1, C2 一般連通測試
        "T1-S1-4F", "RB-SB-3F",  # 垂直動線測試
        "RB-WCM3", "T4-WCF4",    # 特殊 POI 測試
        "T1-400-1", "RB-308"     # 一般教室測試
    ]
    for n in test_nodes:
        print(f"{n:12} -> {parse_node_info(n)}")
# ==========================================


# ==========================================
# 步驟 1：讀取 SVG 檔案並萃取 Nodes (節點)
# ==========================================
nodes = []
try:
    with open('data/A03_map.svg', 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'xml')
        
    for circle in soup.find_all('circle'):
        label = circle.get('inkscape:label')
        if label:
            cx = round(float(circle.get('cx')))
            cy = round(float(circle.get('cy')))
            
            # 取得顏色 (優先找 fill 屬性，沒有的話從 style 字串找)
            color = circle.get('fill')
            if not color:
                style_str = circle.get('style', '')
                match = re.search(r'fill:(#[0-9a-fA-F]{6})', style_str)
                if match:
                    color = match.group(1)
                else:
                    color = '#0000FF' # 預設藍色
            # 呼叫判斷函式
            building, floor = parse_node_info(label)
            
            nodes.append({
                "id": label,
                "building": building, # 🌟 新增的建築屬性
                "floor": floor,       # 🌟 自動判斷的正確樓層
                "x": cx,
                "y": cy,
                "color": color
            })
    print(f"✅ 成功讀取 SVG，共萃取出 {len(nodes)} 個節點。")
except FileNotFoundError:
    print("⚠️ 找不到 map.svg，請確認檔案是否存在。")

# ==========================================
# 步驟 2：定義計算距離的函數
# ==========================================
def calculate_distance(node1, node2):
    # 這裡的像素轉公尺比例尺 (例如 1 像素 = 0.05 公尺，請依你 Figma 的量測做調整)
    SCALE_FACTOR = 0.05 
    pixel_dist = math.sqrt((node2['x'] - node1['x'])**2 + (node2['y'] - node1['y'])**2)
    return round(pixel_dist * SCALE_FACTOR, 2)

# ==========================================
# 步驟 3：讀取 raw_edges.json 並建立 Edges (連線)
# ==========================================
edges = []
try:
    with open('data/raw_edges.json', 'r', encoding='utf-8') as f:
        grouped_edges = json.load(f)
        
    raw_edges = []
    # 把分類的字典攤平成單一陣列
    for group_name, edges_list in grouped_edges.items():
        print(f"讀取連線群組: {group_name} ({len(edges_list)} 條連線)")
        raw_edges.extend(edges_list)
        
    # 轉換為帶有距離與屬性的 Edge 物件
    for edge_data in raw_edges:
        start_id = edge_data[0]
        end_id = edge_data[1]
        
        # 如果有寫第三個參數就用它，沒寫就自動預設為 "walkway"
        edge_type = edge_data[2] if len(edge_data) > 2 else "walkway"
        
        # 從 nodes 列表中找出對應的起點與終點
        n1 = next((n for n in nodes if n['id'] == start_id), None)
        n2 = next((n for n in nodes if n['id'] == end_id), None)
        
        if n1 and n2:
            edges.append({
                "from": start_id,
                "to": end_id,
                "distance": calculate_distance(n1, n2),
                "type": edge_type
            })
        else:
            # 防呆機制：如果 JSON 裡打錯字，會在這裡印出警告，但程式不會當機
            print(f"⚠️ 警告：找不到節點 '{start_id}' 或 '{end_id}'，無法建立連線！請檢查拼字。")
            
    print(f"✅ 成功建立 {len(edges)} 條有效連線。")
    
except FileNotFoundError:
    print("⚠️ 找不到 raw_edges.json，請確認檔案是否存在。")

# ==========================================
# 步驟 4：合併並產出最終的 map_data.json
# ==========================================
json_output = {
    "nodes": nodes,
    "edges": edges
}

with open('data/map_data.json', 'w', encoding='utf-8') as f:
    json.dump(json_output, f, indent=2, ensure_ascii=False)

print("🎉 大功告成！完整圖資已儲存至 map_data.json")