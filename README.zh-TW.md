# SIP 智慧校園導航系統

SIP 是一個以 SVG 圖資為基礎的校園室內外導航原型。專案會把樓層 SVG、校園 SVG、手動 edge、POI metadata CSV 轉成 runtime JSON，後端用 FastAPI 提供地圖資料與路線 API，前端用單頁 HTML/CSS/JavaScript Canvas 呈現互動式 2D / 2.5D 導航介面。

目前主要支援台科大校園與 RB、T1、T4、AU 等建築，包含室內跨樓層、跨棟連通、校園配置、科系屬性視圖、POI 搜尋與多種路線偏好。

## 功能

- 室內與校園節點整合尋路。
- 支援 POI 作為起點與終點，例如教室、實驗室、辦公室、飲水機。
- 起點/終點搜尋支援 `id`、`name_zh`、`name_en`、`aliases`、`faculty_leads`、`occupants`。
- 路線模式：
  - 最短距離
  - 電梯優先
  - 雨天路徑，偏好 `CoveredPath-*` / `covered_walkway`
- 視圖模式：
  - 建築室內：建築空間、室內服務、水平動線、垂直動線、量體模式
  - 校園配置：校園模式
  - 科系屬性：科系分類、點、設計、建築、資工、應外、其他
- 校園模式可顯示建築名稱與校園 POI 名稱。
- 科系屬性模式依 `department` 顯示 POI 與樓板色系。
- Hover POI 會顯示膠囊資訊，包含名稱、位置、department 等 metadata。
- Developer Edge Editor 可用於維護 indoor/campus edge source。
- Experimental Academic Community View 已保留程式碼，但預設從正式選單隱藏，只在 debug / beta 參數下顯示。

## 技術架構

- Backend：FastAPI、Uvicorn、Python 3.12
- Data pipeline：Python、BeautifulSoup、lxml
- Frontend：單一 `frontend/index.html`，使用 Canvas 繪圖
- Environment：Conda

## 快速啟動

第一次使用先建立 Conda 環境：

```bash
conda env create -f environment.yml
conda activate indoor
```

之後啟動後端：

```bash
conda run --no-capture-output -n indoor python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

開啟：

```text
http://127.0.0.1:8000
```

如果 `--reload` 在目前環境遇到檔案監看權限問題，可以改用：

```bash
conda run --no-capture-output -n indoor python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## 公開與私有資料

公開 repo 不包含 `A*_map.svg` 室內樓層 SVG。這些檔案包含向學校申請的建築圖，僅供本機學術研究使用。

可公開資料：

- `data/source/public/svg/campus/L01_CampusLayout.svg`
- source edge files
- metadata CSV files
- generated JSON files，目前暫時保留公開

本機私有資料：

- `data/source/private/svg/floors/A*_map.svg`

Pipeline 預設會從 `data/source/private/svg/floors/` 讀取室內樓層 SVG。這個資料夾已被 Git 忽略。若私有檔案放在其他位置，可以設定：

```bash
SIP_FLOOR_SVG_DIR=/path/to/private/floors conda run --no-capture-output -n indoor python run_pipeline.py
```

## 常用指令

重新產生所有圖資與 metadata：

```bash
conda run --no-capture-output -n indoor python run_pipeline.py
```

只檢查 `poi_master.csv` 錯誤與重複 ID：

```bash
conda run --no-capture-output -n indoor python scripts/check_poi_master.py
```

只重新合併 POI metadata：

```bash
conda run --no-capture-output -n indoor python scripts/enrich_pois.py
```

檢查後端語法：

```bash
python -m py_compile backend/main.py
```

## 資料更新流程

### 更新 `poi_master.csv`

如果只是修改 POI 名稱、科系、老師、alias、分類等 metadata：

1. 編輯 `data/metadata/poi_master.csv`。
2. 執行檢查：

   ```bash
   conda run --no-capture-output -n indoor python scripts/check_poi_master.py
   ```

3. 重新合併 POI：

   ```bash
   conda run --no-capture-output -n indoor python scripts/enrich_pois.py
   ```

4. 如果後端已經在跑，重啟後端或使用 `--reload`。

如果你也改了 SVG、edge、connection overrides，請直接跑完整 pipeline：

```bash
conda run --no-capture-output -n indoor python run_pipeline.py
```

### 更新 SVG 節點

如果你在 SVG 新增、刪除或移動節點：

1. 編輯本機私有室內 SVG：`data/source/private/svg/floors/A*_map.svg`，或編輯可公開的校園 SVG：`data/source/public/svg/campus/L01_CampusLayout.svg`。
2. 確認每個重要物件的 `inkscape:label` 正確。
3. 執行：

   ```bash
   conda run --no-capture-output -n indoor python run_pipeline.py
   ```

4. 重啟後端，重新整理網頁。

### 更新 edge

Source of truth 是：

- `data/source/edges/indoor_edges.json`
- `data/source/edges/campus_edges.json`
- `data/source/overrides/connection_overrides.json`

不要手動改 `data/generated/` 裡的 JSON。那些檔案會被 pipeline 覆寫。

如果要重新整理 campus edge，建議流程：

1. 備份並編輯 `data/source/edges/campus_edges.json`。
2. 跑完整 pipeline。
3. 開啟網頁，用 Developer Edge Editor 檢查或重新畫 edge。
4. 匯出後把結果整理回 `data/source/edges/campus_edges.json`。
5. 再跑一次完整 pipeline。

不需要刪除 `data/generated/`，pipeline 會重新輸出。

## POI Metadata Schema

`data/metadata/poi_master.csv` 欄位：

```text
id,name_zh,name_en,category,department,faculty_leads,occupants,aliases,description,public_access,source,status
```

欄位用途：

- `id`：必須對應 SVG 解析出的 POI ID。
- `name_zh`：中文顯示名稱。
- `name_en`：英文顯示名稱。
- `category`：分類，需符合 `data/metadata/dictionary.csv`。
- `department`：科系或單位，科系屬性視圖會使用。
- `faculty_leads`：實驗室主持人，搜尋與 Academic Community beta 會使用。
- `occupants`：辦公室使用者，搜尋與 Academic Community beta 會使用。
- `aliases`：別名、舊房號、簡寫，搜尋會使用。
- `description`：補充說明。
- `public_access`：開放狀態，例如 `public`、`restricted`。
- `source`：資料來源。
- `status`：狀態，例如 `active`。

多值欄位使用分號分隔：

```text
faculty_leads: 王小明;李小華
occupants: 王小明;李小華
aliases: RB308;RB-308-1
```

## SVG 命名規則

Parser 主要讀取 SVG 裡的 `inkscape:label`。請優先維持 ID 穩定，不要任意改名，因為 edge、metadata、connection 都會引用它。

常見命名：

- 室內路網點：`RB-100-1`、`T4-300-2`
- 樓梯：`RB-SA-3F`
- 電梯：`RB-E1-3F`
- 跨棟連通：`C-T4-2F-to-T1-2F`
- POI：`RB-308-1`、`T4-512`
- 飲水機：`{大樓}-{樓層}F-WF-{編號}`，例如 `RB-3F-WF-1`
- 校園大門：`Gate-101`
- 校園一般路徑：`Path-101`
- 風雨走廊：`CoveredPath-101`
- 建築入口或校園 anchor：`Building-RB-1`

飲水機會被 parser 視為 POI，並由 pipeline 連到最近的有效路網點。若想讓搜尋與顯示資訊完整，建議也把飲水機補進 `poi_master.csv`。

樓梯與電梯通常不需要填入 `poi_master.csv`。它們是 routing node，前端搜尋與 hover 會以「樓梯 / 電梯 + 位置」顯示，不直接要求 metadata。

## Data Layout

```text
sip/
|-- backend/
|   `-- main.py
|-- frontend/
|   `-- index.html
|-- scripts/
|   |-- 1_svg_parser.py
|   |-- enrich_pois.py
|   |-- 2_knn_recommender.py
|   |-- 3_merge_connections.py
|   |-- 4_campus_features_parser.py
|   `-- check_poi_master.py
|-- data/
|   |-- source/
|   |   |-- public/
|   |   |   `-- svg/
|   |   |       |-- campus/
|   |   |       `-- floors/         # 公開 placeholder；不 commit 私有 A*.svg
|   |   |-- private/                # Git 忽略；本機私有樓層 SVG
|   |   |   `-- svg/floors/A*_map.svg
|   |   |-- edges/
|   |   `-- overrides/
|   |-- metadata/
|   |   |-- poi_master.csv
|   |   |-- poi_campus.csv
|   |   |-- dictionary.csv
|   |   `-- campus_buildings.json
|   `-- generated/
|-- docs/
|   `-- navigation_node_edge_spec.md
|-- run_pipeline.py
|-- environment.yml
`-- README.md
```

### `data/source/`

手動維護的圖資來源。改 SVG、edge、connection override 時應改這裡。

### `data/metadata/`

手動維護的 metadata。POI 顯示名稱、科系、老師、alias 等資料放這裡。

### `data/generated/`

Pipeline 產物。不要手動修改。

後端啟動時會讀：

- `data/generated/routing_nodes.json`
- `data/generated/pois_enriched.json`
- `data/generated/slabs.json`
- `data/generated/campus_features.json`
- `data/generated/final_connections.json`
- `data/metadata/poi_campus.csv`

## Pipeline

完整流程由 `run_pipeline.py` 串起：

1. `scripts/1_svg_parser.py`
   - 解析室內樓層 SVG。
   - 解析校園 L01 SVG。
   - 合併 indoor/campus edge source。
   - 輸出 routing nodes、POI geometry、slabs。

2. `scripts/enrich_pois.py`
   - 讀 `data/generated/pois.json`。
   - 讀 `data/metadata/poi_master.csv`。
   - 驗證欄位、重複 ID、category。
   - 輸出 `data/generated/pois_enriched.json`。

3. `scripts/2_knn_recommender.py`
   - 為 POI 推薦最近的路網連接點。
   - 輸出 `data/generated/draft_connection.json`。

4. `scripts/3_merge_connections.py`
   - 套用人工 add/remove override。
   - 輸出 `data/generated/final_connections.json`。

5. `scripts/4_campus_features_parser.py`
   - 解析校園建築 footprint 與戶外色塊。
   - 輸出 `data/generated/campus_features.json`。

## API

### `GET /`

回傳 `frontend/index.html`。

### `GET /api/data`

回傳前端繪圖資料：

- `nodes`
- `edges`
- `pois`
- `slabs`
- `campus_features`
- `campus_pois`
- `connections`

### `GET /api/route`

參數：

- `start`：起點 node 或 POI ID
- `end`：終點 node 或 POI ID
- `mode`：`shortest`、`elevator_preferred`、`rainy_preferred`

範例：

```bash
curl "http://127.0.0.1:8000/api/route?start=T4-512&end=RB-308-1&mode=shortest"
```

## 前端維護重點

主要程式在 `frontend/index.html`。

重要狀態：

- `currentViewMode`：目前視圖模式。
- `currentDepartmentSubMode`：科系屬性子模式。
- `currentRouteMode`：目前路線偏好。
- `selectedSpaceIds`：起點/終點選取狀態。
- `currentRoute`：目前導航路徑。

搜尋來源：

- `poisData`
- `nodesData`

搜尋支援欄位：

- `id`
- `name_zh`
- `name_en`
- `name`
- `aliases` / `alias`
- `faculty_leads`
- `occupants`
- `department`
- `category`
- `building`
- `floor_name`

## Academic Community Beta

Academic Community View 是實驗功能，目前不在正式視圖選單顯示。

要顯示此功能，使用：

```text
http://127.0.0.1:8000?academic_beta=1
```

或：

```text
http://127.0.0.1:8000?debug=1
```

此功能只用前端從 `pois_enriched.json` 動態建立測試 graph，不會修改 routing graph、raw edge 或 POI source。

## 常見問題

### 更新 `poi_master.csv` 後，為什麼網頁沒變？

需要重新產生 `pois_enriched.json`：

```bash
conda run --no-capture-output -n indoor python scripts/enrich_pois.py
```

如果後端已經啟動，還需要重啟後端或使用 `--reload`。

### 更新 SVG 或 edge 後要跑什麼？

跑完整 pipeline：

```bash
conda run --no-capture-output -n indoor python run_pipeline.py
```

### 要不要刪除 `data/generated/`？

通常不用。Pipeline 會覆寫需要更新的 generated 檔案。

### 飲水機要不要填入 `poi_master.csv`？

建議填。Parser 可以自動把 `*-WF-*` 當 POI，但填進 CSV 才能讓名稱、分類、搜尋與顯示資訊更完整。

### 樓梯和電梯要不要填入 `poi_master.csv`？

通常不用。樓梯與電梯是 routing node，不是一般 POI。前端已經會在搜尋與 hover 顯示「樓梯」或「電梯」與位置。

### Developer Edge Editor 匯入沒有反應怎麼辦？

先確認你改的是 source edge：

- `data/source/edges/indoor_edges.json`
- `data/source/edges/campus_edges.json`

再跑 `run_pipeline.py`。不要直接改 `data/generated/routing_nodes.json`，因為它會被 pipeline 覆寫。

## 開發注意事項

- 所有指令請在 repo 根目錄執行。
- `data/source/` 和 `data/metadata/` 是主要維護來源。
- `data/generated/` 是輸出結果，應由 pipeline 產生。
- 修改前端後重新整理頁面即可。
- 修改 backend 或 generated data 後，需重啟後端，或使用 `--reload`。
- 不要把 Academic Community beta 的 edge 寫進 routing edge。
- 不要用推論方式自動建立跨系、合作或語意關係。
