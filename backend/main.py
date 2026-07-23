import json
import math
import heapq
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="SIP Multi-floor Navigation Engine")

# RB-B104 (356, 673) 到 RB-B105 (299, 674) 校準為 500 cm。
SCALE_FACTOR = 5.0 / math.sqrt((356 - 299)**2 + (673 - 674)**2)

print("🚀 啟動 SIP 跨樓層雙向尋路引擎 (含備選路徑)...")

try:
    with open('data/routing_nodes.json', 'r', encoding='utf-8') as f:
        routing_data = json.load(f)
    with open('data/pois_enriched.json', 'r', encoding='utf-8') as f:
        pois_data = json.load(f)
    with open('data/slabs.json', 'r', encoding='utf-8') as f:
        slabs_data = json.load(f)
    with open('data/final_connections.json', 'r', encoding='utf-8') as f:
        connections_data = json.load(f)
except FileNotFoundError as e:
    print(f"❌ 嚴重錯誤：找不到 {e.filename}！請確認已完成 1~3 資料融合步驟。")
    exit(1)

base_graph = {}
node_coords = {}
node_floors = {}

for node in routing_data['nodes']:
    base_graph[node['id']] = {}
    node_coords[node['id']] = (node['x'], node['y'])
    node_floors[node['id']] = node['floor']

for edge in routing_data['edges']:
    u, v, w = edge['from'], edge['to'], edge['distance']
    if u in base_graph and v in base_graph:
        base_graph[u][v] = w
        base_graph[v][u] = w

poi_dict = {poi['id']: poi for poi in pois_data}
for poi in pois_data:
    node_coords[poi['id']] = (poi['x'], poi['y'])
    node_floors[poi['id']] = poi['floor']

def calculate_distance(id1, id2):
    f1, f2 = node_floors.get(id1, 1.0), node_floors.get(id2, 1.0)
    if f1 != f2:
        return round(abs(f1 - f2) * 10.0, 2)
    x1, y1 = node_coords[id1]
    x2, y2 = node_coords[id2]
    return round(math.sqrt((x1 - x2)**2 + (y1 - y2)**2) * SCALE_FACTOR, 2)

def run_dijkstra(graph, start, end):
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    pq = [(0, start)]
    previous = {node: None for node in graph}

    while pq:
        current_dist, current_node = heapq.heappop(pq)
        if current_dist > distances[current_node]:
            continue
        if current_node == end:
            break
            
        for neighbor, weight in graph[current_node].items():
            dist = current_dist + weight
            if dist < distances[neighbor]:
                distances[neighbor] = dist
                previous[neighbor] = current_node
                heapq.heappush(pq, (dist, neighbor))

    if distances[end] == float('inf'):
        return [], float('inf')

    path = []
    curr = end
    while curr is not None:
        path.append(curr)
        curr = previous[curr]
    path.reverse()
    return path, round(distances[end], 2)

@app.get("/api/route")
def get_shortest_path(start: str, end: str):
    if start not in node_coords or end not in node_coords:
        raise HTTPException(status_code=404, detail=f"找不到起點或終點")

    local_graph = {node: neighbors.copy() for node, neighbors in base_graph.items()}

    def inject_virtual_node(poi_id):
        if poi_id not in local_graph:
            local_graph[poi_id] = {}
        targets = connections_data.get(poi_id, [])
        for target in targets:
            if target in local_graph:
                dist = calculate_distance(poi_id, target)
                local_graph[poi_id][target] = dist
                local_graph[target][poi_id] = dist 

    if start in poi_dict: inject_virtual_node(start)
    if end in poi_dict: inject_virtual_node(end)

    # 1. 計算主路線
    main_path, main_dist = run_dijkstra(local_graph, start, end)
    if not main_path:
        raise HTTPException(status_code=400, detail="這兩個點之間無法連通")

    # 2. 計算備選路線 (移除主路線中間的骨幹邊)
    alt_path, alt_dist = [], float('inf')
    if len(main_path) > 4:
        # 找中間的一條邊切斷
        idx = len(main_path) // 2
        u, v = main_path[idx], main_path[idx+1]
        
        # 暫時移除該邊
        w_uv = local_graph[u].pop(v, None)
        w_vu = local_graph[v].pop(u, None)
        
        alt_path, alt_dist = run_dijkstra(local_graph, start, end)
        
        # 恢復該邊 (若有其他用途)
        if w_uv: local_graph[u][v] = w_uv
        if w_vu: local_graph[v][u] = w_vu

        # 如果備選路線太繞路(超過 1.5 倍)或是跟主路線一樣，就作廢
        if alt_dist > main_dist * 1.5 or alt_path == main_path:
            alt_path = []
            alt_dist = None

    # 3. 產生文字導航
    directions = [f"🚶 從 {start} 出發"]
    for i in range(1, len(main_path) - 1):
        curr = main_path[i]
        prev = main_path[i-1]
        if curr.startswith('C') and curr.count('-') >= 2:
            if not (prev.startswith('C') and prev.count('-') >= 2):
                directions.append(f"🌉 經過跨棟連通道 ({curr}) 前往另一大樓")
        elif "stair" in curr.lower() or "elevator" in curr.lower() or "樓梯" in curr or "電梯" in curr:
            if node_floors.get(curr) != node_floors.get(prev):
                directions.append(f"🪜 經由 {curr} 轉換樓層")
    directions.append(f"🎯 抵達終點 {end}")

    if not alt_path:
        alt_dist = None

    return {
        "path": main_path,
        "total_distance": main_dist,
        "directions": directions,
        "alt_path": alt_path,
        "alt_distance": alt_dist
    }

@app.get("/api/data")
def get_map_data():
    return {
        "nodes": routing_data['nodes'],
        "edges": routing_data['edges'],
        "pois": pois_data,
        "slabs": slabs_data,
        "connections": connections_data 
    }

@app.get("/")
def read_root():
    return FileResponse("frontend/index.html")
