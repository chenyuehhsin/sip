import csv
import json
import math
import heapq
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="SIP Multi-floor Navigation Engine")
REPO_ROOT = Path(__file__).resolve().parent.parent

# RB-B104 (356, 673) 到 RB-B105 (299, 674) 校準為 500 cm。
SCALE_FACTOR = 5.0 / math.sqrt((356 - 299)**2 + (673 - 674)**2)

print("🚀 啟動 SIP 跨樓層雙向尋路引擎...")

def load_campus_pois(path=REPO_ROOT / 'data/metadata/poi_campus.csv'):
    try:
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                campus_id = str(row.get('id', '')).strip()
                if not campus_id:
                    continue
                rows.append({
                    "id": campus_id,
                    "name": str(row.get('name', '')).strip(),
                    "name_zh": str(row.get('name_zh', '')).strip()
                })
            return rows
    except FileNotFoundError:
        return []

try:
    with open(REPO_ROOT / 'data/generated/routing_nodes.json', 'r', encoding='utf-8') as f:
        routing_data = json.load(f)
    with open(REPO_ROOT / 'data/generated/pois_enriched.json', 'r', encoding='utf-8') as f:
        pois_data = json.load(f)
    with open(REPO_ROOT / 'data/generated/slabs.json', 'r', encoding='utf-8') as f:
        slabs_data = json.load(f)
    try:
        with open(REPO_ROOT / 'data/generated/campus_features.json', 'r', encoding='utf-8') as f:
            campus_features_data = json.load(f)
    except FileNotFoundError:
        campus_features_data = {"features": []}
    with open(REPO_ROOT / 'data/generated/final_connections.json', 'r', encoding='utf-8') as f:
        connections_data = json.load(f)
    campus_pois_data = load_campus_pois()
except FileNotFoundError as e:
    print(f"❌ 嚴重錯誤：找不到 {e.filename}！請先從專案根目錄執行 python run_pipeline.py。")
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

CAMPUS_ROUTE_PREFIXES = ("Gate-", "Path-", "CoveredPath-", "Building-", "Lawn-", "Pool-", "Court-")


def get_rainy_edge_weight(edge):
    weight = edge['distance']
    edge_type = edge.get('type', '')
    source = edge.get('from', '')
    target = edge.get('to', '')
    # Experimental route preference: only campus covered-path weights are adjusted.
    # Indoor routing behavior and source edge data stay unchanged.
    is_covered = edge_type == "covered_walkway" or source.startswith("CoveredPath-") or target.startswith("CoveredPath-")
    is_campus = source.startswith(CAMPUS_ROUTE_PREFIXES) and target.startswith(CAMPUS_ROUTE_PREFIXES)

    if is_covered:
        return weight * 0.45
    if is_campus:
        return weight * 1.35
    return weight


def build_route_graph(mode):
    if mode == "shortest":
        return {node: neighbors.copy() for node, neighbors in base_graph.items()}

    graph = {node: {} for node in base_graph}
    for edge in routing_data['edges']:
        if mode == "elevator_preferred" and edge.get('type') == "stair":
            continue
        u, v = edge['from'], edge['to']
        w = get_rainy_edge_weight(edge) if mode == "rainy_preferred" else edge['distance']
        if u in graph and v in graph:
            graph[u][v] = w
            graph[v][u] = w
    return graph

@app.get("/api/route")
def get_shortest_path(start: str, end: str, mode: str = "shortest"):
    supported_modes = ["shortest", "elevator_preferred", "rainy_preferred"]
    if mode not in set(supported_modes):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_route_mode",
                "message": "Unsupported route mode",
                "mode": mode,
                "supported_modes": supported_modes
            }
        )

    if start not in node_coords or end not in node_coords:
        raise HTTPException(status_code=404, detail=f"找不到起點或終點")

    local_graph = build_route_graph(mode)

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

    main_path, main_dist = run_dijkstra(local_graph, start, end)
    if not main_path:
        if mode == "elevator_preferred":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "route_unavailable",
                    "reason": "no_stair_free_route",
                    "message": "目前圖資中找不到避免樓梯的可達路線。",
                    "mode": mode
                }
            )
        raise HTTPException(status_code=400, detail="這兩個點之間無法連通")

    directions = [f"🚶 從 {start} 出發"]
    if mode == "rainy_preferred":
        directions.append("☔ 雨天路徑：優先使用風雨走廊與遮蔽動線")
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

    return {
        "mode": mode,
        "path": main_path,
        "total_distance": main_dist,
        "directions": directions,
        "alt_path": [],
        "alt_distance": None
    }

@app.get("/api/data")
def get_map_data():
    return {
        "nodes": routing_data['nodes'],
        "edges": routing_data['edges'],
        "pois": pois_data,
        "slabs": slabs_data,
        "campus_features": campus_features_data,
        "campus_pois": campus_pois_data,
        "connections": connections_data 
    }

@app.get("/")
def read_root():
    return FileResponse(REPO_ROOT / "frontend/index.html")
