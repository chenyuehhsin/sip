import json
import math

print("🤖 開始執行 [步驟二]: KNN 智慧連線推薦器 (AI 小幫手)...")

# ==========================================
# 1. 載入第一步產生的 Ground Truth 資料
# ==========================================
try:
    with open('data/routing_nodes.json', 'r', encoding='utf-8') as f:
        routing_data = json.load(f)
        routing_nodes = routing_data.get('nodes', [])
    
    with open('data/pois.json', 'r', encoding='utf-8') as f:
        pois = json.load(f)
except FileNotFoundError as e:
    print(f"❌ 錯誤：找不到必要檔案 {e.filename}。請先執行 1_svg_parser.py")
    exit(1)

# ==========================================
# 2. 定義圖譜語意規則 (Semantic Graph Rules)
# ==========================================
# 🌟 核心邏輯：POI 只能連接水平動線，嚴格排除垂直動線(樓梯/電梯)
VALID_NAVIGATION_COLORS = ['#ff5555', '#87de87'] # 紅色走廊、綠色空橋
K_CANDIDATES = 2 # 每個 POI 預設推薦最近的 2 個 Anchor (前門、後門候選)

draft_connections = {}
warnings = 0

# ==========================================
# 3. 執行 KNN 空間演算法
# ==========================================
for poi in pois:
    poi_id = poi['id']
    
    # 篩選候選名單：必須是「同棟、同樓層」且「符合 Navigation 語意」的節點
    valid_candidates = [
        n for n in routing_nodes 
        if n['building'] == poi['building'] 
        and n['floor'] == poi['floor']
        and n.get('color', '').lower() in VALID_NAVIGATION_COLORS
    ]
    
    if not valid_candidates:
        print(f"⚠️ 警告：POI '{poi_id}' 在同層找不到合法的走廊/空橋點 (已被樓梯防呆阻擋或無節點)。")
        draft_connections[poi_id] = []
        warnings += 1
        continue
        
    # 計算 Euclidean 幾何距離
    for node in valid_candidates:
        node['distance_to_poi'] = math.sqrt((node['x'] - poi['x'])**2 + (node['y'] - poi['y'])**2)
        
    # 依照距離排序 (由近到遠)
    valid_candidates.sort(key=lambda n: n['distance_to_poi'])
    
    # 取出前 K 名最近的節點 ID 作為推薦
    top_k_nodes = valid_candidates[:K_CANDIDATES]
    target_ids = [n['id'] for n in top_k_nodes]
    
    draft_connections[poi_id] = target_ids

# ==========================================
# 4. 輸出推薦草稿
# ==========================================
with open('data/draft_connection.json', 'w', encoding='utf-8') as f:
    json.dump(draft_connections, f, indent=2, ensure_ascii=False)

print("✅ [步驟二] 執行完畢！")
print(f"📊 統計: 成功為 {len(pois)} 個 POI 產生連線草稿 (包含 {warnings} 個警告)。")
print("📁 推薦清單已成功寫入 data/draft_connection.json")
print("💡 提示: KNN 預設提供最近的 2 個節點。請打開 draft 檢查，若有錯連或多連，請登記到 connection_overrides.json 中。")