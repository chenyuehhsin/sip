import json
import math
import heapq
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="SIP Navigation Engine")

# 比例尺常數
SCALE_FACTOR = 0.05 

print("🚀 啟動 SIP 後端導航引擎...")

# ==========================================
# 1. 載入我們精心準備的「三神裝」資料檔
# ==========================================
try:
    with open('data/routing_nodes.json', 'r', encoding='utf-8') as f:
        routing_data = json.load(f)
    with open('data/pois.json', 'r', encoding='utf-8') as f:
        pois_data = json.load(f)
    with open('data/final_connections.json', 'r', encoding='utf-8') as f:
        connections_data = json.load(f)
except FileNotFoundError as e:
    print(f"❌ 嚴重錯誤：找不到 {e.filename}！請確認已執行完 1~3 步驟的管線腳本。")
    exit(1)

# ==========================================
# 2. 建立靜態骨幹網路 (Base Graph) 與座標字典
# ==========================================
base_graph = {}
node_coords = {}

# 載入骨幹節點座標
for node in routing_data['nodes']:
    base_graph[node['id']] = {}
    node_coords[node['id']] = (node['x'], node['y'])

# 載入骨幹連線 (雙向邊)
for edge in routing_data['edges']:
    u, v, w = edge['from'], edge['to'], edge['distance']
    if u in base_graph and v in base_graph:
        base_graph[u][v] = w
        base_graph[v][u] = w

# 載入 POI 座標 (為了計算虛擬連線的距離)
poi_dict = {poi['id']: poi for poi in pois_data}
for poi in pois_data:
    node_coords[poi['id']] = (poi['x'], poi['y'])

def calculate_distance(id1, id2):
    x1, y1 = node_coords[id1]
    x2, y2 = node_coords[id2]
    return round(math.sqrt((x1 - x2)**2 + (y1 - y2)**2) * SCALE_FACTOR, 2)

# ==========================================
# 3. 核心 API：Dijkstra 尋路 (搭載虛擬節點技術)
# ==========================================
@app.get("/api/route")
def get_shortest_path(start: str, end: str):
    if start not in node_coords:
        raise HTTPException(status_code=404, detail=f"找不到起點 {start}")
    if end not in node_coords:
        raise HTTPException(status_code=404, detail=f"找不到終點 {end}")

    # 🌟 複製一份臨時的 Graph，用來注入虛擬節點
    local_graph = {node: neighbors.copy() for node, neighbors in base_graph.items()}

    # 注入虛擬節點的閉包函數
    def inject_virtual_node(poi_id):
        if poi_id not in local_graph:
            local_graph[poi_id] = {}
        # 去 final_connections 查這個 POI 有幾個門
        targets = connections_data.get(poi_id, [])
        for target in targets:
            if target in local_graph:
                dist = calculate_distance(poi_id, target)
                local_graph[poi_id][target] = dist
                local_graph[target][poi_id] = dist # 雙向連通

    # 如果起終點是教室(POI)，就把他們動態插進地圖裡
    if start in poi_dict:
        inject_virtual_node(start)
    if end in poi_dict:
        inject_virtual_node(end)

    # 🧠 標準 Dijkstra 演算法 (跑在包含虛擬點的 local_graph 上)
    distances = {node: float('inf') for node in local_graph}
    distances[start] = 0
    pq = [(0, start)]
    previous = {node: None for node in local_graph}

    while pq:
        current_dist, current_node = heapq.heappop(pq)
        
        if current_dist > distances[current_node]:
            continue
        if current_node == end:
            break
            
        for neighbor, weight in local_graph[current_node].items():
            dist = current_dist + weight
            if dist < distances[neighbor]:
                distances[neighbor] = dist
                previous[neighbor] = current_node
                heapq.heappush(pq, (dist, neighbor))

    if distances[end] == float('inf'):
        raise HTTPException(status_code=400, detail="這兩個點之間無法連通")

    # 回溯路徑
    path = []
    curr = end
    while curr is not None:
        path.append(curr)
        curr = previous[curr]
    path.reverse()

    # ==========================================
    # 產出「人類語意化」的精簡文字導航
    # ==========================================
    directions = []
    directions.append(f"🚶 從 {path[0]} 出發，進入走廊")
    
    # 只抓取「重大轉換節點」進行提示 (例如跨棟橋樑、電梯、樓梯)
    for i in range(1, len(path) - 1):
        curr = path[i]
        
        # 判斷是否為跨棟橋樑 (例如 C3-T4-T1)
        if curr.startswith('C') and curr.count('-') >= 2:
            # 避免連續播報兩個橋樑點，檢查上一個點是不是也是橋樑
            prev = path[i-1]
            if not (prev.startswith('C') and prev.count('-') >= 2):
                directions.append(f"🌉 途經連通道 ({curr}) 前往另一棟建築")
                
        # 判斷是否為垂直動線 (樓梯、電梯)
        elif "stair" in curr.lower() or "elevator" in curr.lower() or "樓梯" in curr:
             directions.append(f"🪜 經由 {curr} 轉換樓層")

    directions.append(f"🎯 抵達終點 {path[-1]}")

    return {
        "path": path,
        "total_distance": round(distances[end], 2),
        "directions": directions
    }

# ==========================================
# 4. 前端資料供應與靜態網頁路由
# ==========================================
@app.get("/api/data")
def get_map_data():
    """將乾淨的分層資料吐給前端渲染"""
    return {
        "nodes": routing_data['nodes'],
        "edges": routing_data['edges'],
        "pois": pois_data,
        "connections": connections_data # 🌟 前端畫灰線需要這個！
    }

@app.get("/")
def read_root():
    return FileResponse("frontend/index.html")