import json
import math

print("🤖 開始執行 [步驟二]: KNN 智慧連線推薦器 (多樓層對齊版)...")

try:
    with open('data/routing_nodes.json', 'r', encoding='utf-8') as f:
        routing_data = json.load(f)
        routing_nodes = routing_data.get('nodes', [])
    
    with open('data/pois.json', 'r', encoding='utf-8') as f:
        pois = json.load(f)
except FileNotFoundError as e:
    print(f"❌ 錯誤：找不到必要檔案 {e.filename}。請先執行 1_svg_parser.py")
    exit(1)

VALID_NAVIGATION_COLORS = ['#ff5555', '#87de87'] # 紅色走廊、綠色空橋
K_CANDIDATES = 2 

draft_connections = {}
warnings = 0

for poi in pois:
    poi_id = poi['id']
    
    # 🌟 多樓層對齊：必須是同棟大樓、數值樓層完全相等，且屬於合法的水平走廊點
    valid_candidates = [
        n for n in routing_nodes 
        if n['building'] == poi['building'] 
        and n['floor'] == poi['floor']
        and n.get('color', '').lower() in VALID_NAVIGATION_COLORS
    ]
    
    if not valid_candidates:
        print(f"⚠️ 警告：POI '{poi_id}' 在大樓 '{poi['building']}' 樓層 '{poi['floor_name']}' 找不到合法的走廊連線點。")
        draft_connections[poi_id] = []
        warnings += 1
        continue
        
    for node in valid_candidates:
        node['distance_to_poi'] = math.sqrt((node['x'] - poi['x'])**2 + (node['y'] - poi['y'])**2)
        
    valid_candidates.sort(key=lambda n: n['distance_to_poi'])
    top_k_nodes = valid_candidates[:K_CANDIDATES]
    target_ids = [n['id'] for n in top_k_nodes]
    
    draft_connections[poi_id] = target_ids

with open('data/draft_connection.json', 'w', encoding='utf-8') as f:
    json.dump(draft_connections, f, indent=2, ensure_ascii=False)

print("✅ [步驟二] 執行完畢！")
print(f"📊 統計：已為 {len(pois)} 個跨樓層 POI 完成智慧草稿對接。")