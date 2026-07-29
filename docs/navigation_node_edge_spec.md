# SIP 導航 Node 與 Edge 定義規格

更新日期：2026-07-29

這份文件整理室內地圖 `A*_map.svg` 與校園大尺度地圖 `L01_CampusLayout.svg` 的 node、building footprint、edge 命名與用途。SVG 裡請以 `inkscape:label` 作為正式資料 ID；顏色只作為繪圖與 parser 分類輔助。

## 1. 基本原則

- `inkscape:label` 是穩定 ID，後續 JSON、edge、POI 對接都應使用這個值。
- ID 應優先表達功能，再表達區域或序號。
- 只有使用者可能搜尋或選作起終點的地點，才應設定為 POI。
- 純路徑轉折點、幾何對齊點、入口錨點不應預設混進一般 POI。
- 所有 SVG 合併後，node ID 必須全域唯一。
- 跨尺度對齊點必須在兩個 SVG 使用完全相同 label，例如 L01 與 A01 都標 `Building-RB-1`。

## 2. 室內 Node 定義

室內 node 主要位於 `A*_map.svg`，目前 `scripts/1_svg_parser.py` 已會解析 `A*_map.svg` 的 `circle` 與 `floor-*` 圖形。

### 2.1 紅色：室內水平動線點

用途：一般走廊、轉折點、交會點、POI 對接點。

建議命名：

```text
{BUILDING}-{FLOOR_CODE}00-{SEQ}
```

例子：

```text
RB-100-1
RB-300-4
T4-B100-3
AU-100-7
```

規則：

- 顏色：紅色，現行 parser 辨識 `#ff5555`。
- 資料型別：`routing_node`。
- 常用 edge type：`backbone`。
- 這類點不是 POI，是室內路網骨幹。

### 2.2 藍色：室內樓梯、電梯、跨棟連接點

用途：垂直動線與跨棟通道端點。

建議命名：

```text
{BUILDING}-S{STAIR_ID}-{FLOOR}F
{BUILDING}-E{ELEVATOR_ID}-{FLOOR}F
C-{FROM_BUILDING}-{FROM_FLOOR}F-to-{TO_BUILDING}-{TO_FLOOR}F
```

例子：

```text
RB-SA-1F
RB-E1-3F
T4-S1-2F
C-T4-1F-to-T1-1F
C-RB-3F-to-T1-4F
```

規則：

- 顏色：藍色，現行 parser 會正規化為 `#0ea5e9`。
- 資料型別：`routing_node`。
- 常用 edge type：`stair`、`elevator`、`bridge`。
- 樓梯與電梯應每一層各有一個 node。
- 跨棟連接點用 `C-...-to-...` 表達兩端位置，再用 `bridge` edge 連接。

### 2.3 綠色：室內優先或特殊連接點

用途：特殊通道、連接橋、受保護或優先動線。

建議命名：

```text
C-{FROM}-to-{TO}
```

如果只是一般路徑點，仍沿用室內水平點規則：

```text
{BUILDING}-{FLOOR_CODE}00-{SEQ}
```

規則：

- 顏色：綠色，現行 parser 辨識 `#10b981` 或相近綠色。
- 資料型別：`routing_node`。
- 常用 edge type：`bridge` 或 `backbone`，依實際功能決定。
- 若未來室內也要表示風雨走廊或優先路徑，可改用 `covered_walkway` edge type。

### 2.4 橘色：室內 POI

用途：使用者可搜尋或選作起終點的房間、實驗室、辦公室、服務設施、命名空間。

建議命名：

```text
{BUILDING}-{ROOM_OR_PLACE_ID}
```

例子：

```text
RB-307
RB-B104
T4-101
```

規則：

- 顏色：橘色，現行 parser 辨識 `#ff9955`。
- 資料型別：`poi`。
- POI 目前不是常駐路網點；backend 只有在 POI 作為起終點時，才把它臨時接進 graph。
- POI 與紅/綠路網點的連接關係目前由 `data/final_connections.json` 管理。

## 3. L01 校園大尺度 Node 定義

L01 node 位於 `data/L01_CampusLayout.svg`。目前 parser 尚未正式掃描 `L01_CampusLayout.svg`，所以本節是建議採用的目標規格。

### 3.1 橘色：校園大門 Gate

用途：校園入口與出口。

建議命名：

```text
Gate-{SIDE_CODE}{SEQ}
```

方向代碼：

```text
1 = 北側
2 = 東側
3 = 南側
4 = 西側
5 = 校內特殊邊界入口或非典型入口
```

例子：

```text
Gate-101  # 北側第 1 個大門
Gate-201  # 東側第 1 個大門
Gate-301  # 南側第 1 個大門
Gate-302  # 南側第 2 個大門
Gate-401  # 西側第 1 個大門
```

規則：

- 顏色：橘色，建議 `#ff9955`。
- 建議角色：同時是 `routing_node` 與可搜尋 POI。
- Gate 需要直接接到附近的 `Path-*` 或 `CoveredPath-*`。
- 若只把 Gate 當 POI，校園路網可能無法把它當成可通過的入口節點，因此建議在 L01 parser 中讓 Gate 具備 routing node 身分。

### 3.2 紅色：校園水平動線點

用途：一般戶外道路、人行路徑、轉折點、交會點。

建議命名：

```text
Path-{ZONE_CODE}{SEQ}
```

建議區域代碼：

```text
1 = 北側校園
2 = 東側校園
3 = 南側校園
4 = 西側校園
5 = 中央校園
6 = 建築群或中庭連接區
```

例子：

```text
Path-101
Path-102
Path-501
Path-602
```

結論：`Path-101`、`Path-102` 這種命名是合理的，而且比 `Path-001` 更好，因為百位數可以保留區域語意。

規則：

- 顏色：紅色，建議 `#ff5555`。
- 資料型別：`routing_node`。
- 常用 edge type：`walkway`。
- `Path-*` 只表示戶外路網幾何，不表示建築入口，也不表示 POI。

### 3.3 藍色：建築入口與跨尺度對齊錨點

用途：建築入口、校園路網接入室內路網的連接點、A01 與 L01 的幾何對齊參考點。

建議命名：

```text
Building-{BUILDING_CODE}-{SEQ}
```

例子：

```text
Building-RB-1
Building-T4-1
Building-T4-2
Building-T4-3
Building-AU-1
```

結論：這種藍色點不建議設定為一般 POI。它應該是 `routing_node`，並帶有 `building_anchor` 或 `building_entry` 這類 subtype。未來若想讓使用者搜尋「RB 大樓」，可以另外建立 building-level destination，但不要把 `Building-RB-1` 混在教室/辦公室 POI 清單裡。

規則：

- 顏色：藍色。
- 建議資料型別：`routing_node`。
- 建議 subtype：`building_anchor` 或 `building_entry`。
- 同一個實體位置在 L01 與 A01 必須使用完全相同 label。
- 每棟已建模建築至少要有 1 個 anchor。
- 若要做穩定幾何對齊，建議每棟至少 2 個 anchor；若要處理縮放、旋轉、非等比縮放或微小歪斜，建議 3 個不共線 anchor。

### 3.4 綠色：風雨走廊 Covered Path

用途：戶外但受遮蔽的風雨走廊、優先通行路徑。

建議命名：

```text
CoveredPath-{ZONE_CODE}{SEQ}
```

例子：

```text
CoveredPath-101
CoveredPath-501
CoveredPath-602
```

結論：綠色點的拓樸意義與紅色 `Path-*` 很接近，都是戶外 routing node；差別在於綠色代表「受遮蔽」或「偏好較高」。我建議用 `CoveredPath-*`，不要用 `Rain-*`。`Rain-*` 描述天氣，`CoveredPath-*` 描述路徑本身，比較穩定。

規則：

- 顏色：綠色，建議 `#10b981`。
- 資料型別：`routing_node`。
- 常用 edge type：`covered_walkway`。
- 一般模式下可以跟 `walkway` 使用相同距離成本。
- 雨天模式、遮蔽優先模式、無障礙偏好模式中，可以讓 `covered_walkway` 擁有較低 penalty 或較高優先權。

## 4. 校園建築輪廓 Floor / Footprint 定義

L01 內的其他建築輪廓建議繼續使用：

```text
floor-{BUILDING_CODE}
```

例子：

```text
floor-T2
floor-Library
floor-E1
floor-Gym
```

建議呈現方式：

- 對於尚未完成室內建模的建築，例如 `T2`、`Library`、`E1`，網頁預設用「單層平面半透明灰色 footprint」表示即可。
- 不建議重複多層樓板，因為那會暗示每層樓都已經有可導航資料。
- 預設校園 2D 視圖中，也不建議用太高的半透明體量，容易遮住路網。
- 若未來 3D 視圖需要校園量體，可將未完成建築做成簡單灰色低調 massing，但要與已完成建築有清楚視覺差異。

對於已完成或正在精繪的 `RB`、`T1`、`T4`、`AU`：

- 進入室內模式時，使用 A01 的實際多樓層 slab。
- 校園總覽模式中，可以使用已對齊後的 footprint，或用不同樣式表示「可進入室內導航」的建築。

## 5. A01 與 L01 的對齊方式

目前有兩個尺度座標系：

```text
L01 = 校園總圖座標
A01 = RB / T1 / T4 / AU 室內群組座標
```

建議資料拼接流程：

1. 在 L01 與 A01 標上相同名稱的 `Building-*` anchor。
2. 以完全相同的 `inkscape:label` 配對，例如兩邊都有 `Building-RB-1`。
3. 用配對點計算 A01 到 L01 的幾何 transform。
4. 前端或資料管線在顯示校園總圖時，將 A01 的 nodes、POIs、slabs 套用 transform 後疊到 L01 上。
5. 尋路資料上，用 `building_entry` edge 把 L01 的 `Building-*` anchor 接到 A01 內部真正的入口走廊 node。

anchor 數量的意義：

- 1 個配對點：只能做平移；前提是兩張 SVG 的比例、旋轉已經完全一致。
- 2 個配對點：可解平移、旋轉、等比縮放。
- 3 個不共線配對點：可解 affine transform，能處理非等比縮放與輕微歪斜。

本專案建議：

- 如果 A01 內 `RB / T1 / T4 / AU` 的相對位置已經正確，優先做一組共用的 `A01 -> L01` transform。
- 可先用目前已有的 `Building-T4-1`、`Building-T4-2`、`Building-T4-3`、`Building-RB-1` 做初版對齊。
- `RB` 目前若只有一個 `Building-RB-1`，建議再補 `Building-RB-2`、`Building-RB-3`。
- `T1` 與 `AU` 也建議補上至少 2 到 3 個 anchor，例如 `Building-T1-1`、`Building-T1-2`、`Building-AU-1`、`Building-AU-2`。
- 如果發現某一棟建築對齊後仍有明顯偏差，再改成每棟各自計算 transform。

你可以協助的部分：

- 在 L01 與 A01 標同一個實體點，而且 label 完全一致。
- 優先選穩定明確的位置：主入口中心、樓梯/電梯廳中心、清楚的建築角點。
- 避免用概略目測點或之後可能移動的位置。
- 每棟建築盡量提供 3 個不共線 anchor。

## 6. Edge 定義

手動 edge 目前存在 `data/raw_edges.json`，格式為：

```json
["NODE_A", "NODE_B", "edge_type"]
```

目前 backend 會把 edge 當作無向邊，也就是 `A -> B` 與 `B -> A` 都可通行。

### 6.1 室內 Edge Type

```text
backbone
```

同樓層室內水平動線，通常連接紅色走廊 node。

```text
stair
```

樓梯垂直動線，通常連接同一樓梯在不同樓層的 node。

```text
elevator
```

電梯垂直動線，通常連接同一電梯在不同樓層的 node。

```text
bridge
```

跨棟或特殊連通道，例如 T4 到 T1、T1 到 RB。

```text
poi_connection
```

POI 接到附近 routing node 的邏輯連線。目前不是直接寫在 `raw_edges.json`，而是由 `data/final_connections.json` 管理。

### 6.2 校園 Edge Type

```text
walkway
```

一般戶外路徑，常連接 `Path-*`、`Gate-*`、`Building-*`。

```text
covered_walkway
```

風雨走廊或遮蔽路徑，常連接 `CoveredPath-*`。

```text
gate_access
```

大門與最近校園路徑的連線。距離上可先等同 `walkway`，但保留 type 方便未來 UI 或權重調整。

```text
building_entry
```

校園 `Building-*` anchor 與室內入口走廊 node 的連線。

例子：

```json
["Path-501", "Building-RB-1", "building_entry"]
```

### 6.3 Edge 權重建議

目前行為：

- 同樓層或同校園平面 edge 用像素距離乘上 `SCALE_FACTOR`。
- `stair` 與 `elevator` 用樓層差乘上 `10.0` 估算距離。
- backend 目前主要使用 distance 做 Dijkstra；edge type 目前更多是資料語意與前端顯示用途。

未來建議：

- distance 保留為實體距離基礎成本。
- 偏好邏輯放在 routing engine，例如雨天模式、遮蔽優先、少樓梯模式。
- `covered_walkway` 不要直接改短實體距離；應在特定 routing mode 中降低 penalty。
- `building_entry` 建議給一個小固定成本，避免進出建築在路徑計算上完全免費。

## 7. 目前 L01 的建議決策

- 校園大門使用 `Gate-101`、`Gate-201`、`Gate-301`、`Gate-302`、`Gate-401`。
- 校園紅色水平動線使用 `Path-101`、`Path-102`，百位數保留區域語意。
- 藍色建築入口/對齊點使用 `Building-{BUILDING}-{SEQ}`。
- 藍色 `Building-*` 不設定為一般 POI；它是入口 routing anchor 與跨尺度 alignment anchor。
- 綠色風雨走廊使用 `CoveredPath-101`、`CoveredPath-102`，不建議用 `Rain-*`。
- 尚未完成室內建模的建築，在校園網頁中以單層平面半透明灰色 footprint 表示。
- A01 與 L01 靠同名 `Building-*` anchor 對齊；只有一個 anchor 的建築建議補到至少 2 個，最好 3 個。
