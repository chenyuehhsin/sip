from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import json
import heapq

app = FastAPI(title="北車/台科大室內導航 API")

# 1. 啟動時載入資料並建立 Graph
with open('data/map_data.json', 'r', encoding='utf-8') as f:
    map_data = json.load(f)

# 建立字典格式的 Graph，方便演算法快速讀取
# 格式: { 'NodeA': {'NodeB': 5.0, 'NodeC': 2.5}, ... }
graph = {node['id']: {} for node in map_data['nodes']}

for edge in map_data['edges']:
    u, v, w = edge['from'], edge['to'], edge['distance']
    # 雙向連通
    if u in graph and v in graph:
        graph[u][v] = w
        graph[v][u] = w

# 2. Dijkstra 演算法核心函式
def calculate_dijkstra(start_id: str, end_id: str):
    # queue 裡面放的是 Tuple: (目前累積距離, 目前節點ID, 走過的路徑陣列)
    queue = [(0, start_id, [])]
    seen = set()
    
    while queue:
        (current_dist, current_node, path) = heapq.heappop(queue)
        
        if current_node in seen:
            continue
            
        seen.add(current_node)
        path = path + [current_node]
        
        # 如果走到終點了，直接回傳結果
        if current_node == end_id:
            return current_dist, path
            
        # 探索相鄰的節點
        for neighbor, weight in graph.get(current_node, {}).items():
            if neighbor not in seen:
                heapq.heappush(queue, (current_dist + weight, neighbor, path))
                
    return None, [] # 找不到路徑

# 3. API 路由定義
@app.get("/api/data")
def get_map_data():
    return map_data

@app.get("/api/route")
def get_shortest_path(start: str, end: str):
    if start not in graph or end not in graph:
        raise HTTPException(status_code=404, detail="找不到指定的起點或終點")
        
    distance, path = calculate_dijkstra(start, end)
    
    if not path:
        raise HTTPException(status_code=400, detail="這兩個點之間無法連通")
        
    # === 酷炫功能：自動生成人類文字導航指引 ===
    directions = []
    directions.append(f"🏃‍♂️ 從 {start} 出發")
    
    # 建立一個快速查詢 edge type 的字典
    edge_type_map = {}
    for edge in map_data['edges']:
        edge_type_map[(edge['from'], edge['to'])] = edge['type']
        edge_type_map[(edge['to'], edge['from'])] = edge['type']
        
    previous_type = None  # 🌟 關鍵變數：記住上一步的動作
        
    for i in range(len(path) - 1):
        current_node = path[i]
        next_node = path[i+1]
        e_type = edge_type_map.get((current_node, next_node), "walkway")
        
        # 🌟 邏輯優化：只有當「路徑類型改變」時，才增加導航文字，避免瘋狂洗版！
        if e_type != previous_type:
            if e_type == "elevator":
                directions.append(f"🛗 搭乘電梯垂直移動至 {next_node}")
            elif e_type == "stair":
                directions.append(f"🚶‍♂️ 走樓梯移動至 {next_node}")
            elif e_type == "bridge":
                directions.append(f"🌉 通過跨棟連通道天橋（注意：錯層連通通道）")
            elif e_type == "corridor" or e_type == "backbone":
                directions.append(f"🚶‍♂️ 進入主幹道，沿著走廊持續前進")
            else:
                # 一般走道 (walkway) 的跨棟提示
                if current_node[:2] != next_node[:2] and previous_type != "bridge":
                    directions.append(f"🏢 跨越建築物，進入 {next_node[:2]} 大樓區域")
                    
        previous_type = e_type  # 更新狀態，讓下一次迴圈知道剛剛在做什麼
                
    directions.append(f"🎯 到達目的地：{end}！")
    
    return {
        "start": start,
        "end": end,
        "total_distance": round(distance, 2),
        "path": path,
        "directions": directions # 丟給前端印出來！
    }

@app.get("/")
def get_dashboard():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        return HTMLResponse(content=f.read())