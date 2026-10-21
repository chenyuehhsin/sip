# SIP: Spatial Intelligence Platform

[線上展示](https://sip-eight-nu.vercel.app) · [英文說明](README.md)

SIP 是一個面向大型複合建築的空間智慧平台原型。它的核心動機是：當一般民眾第一次進入大型醫院、商場、機場、共構車站，或像台北車站這類複雜空間時，往往不容易快速掌握室內空間概念，也不容易判斷自己該往哪裡走。

SIP 希望透過 2D / 2.5D 視圖、個人化搜尋、POI metadata 與路線偏好，協助使用者更快找到目的地。為了快速驗證可行性，第一版 demo 先以台科大 NTUST 校園作為實驗場域，包含 RB、T1、T4、AU、Stack 等建築；但 SIP 的設計目標並不侷限於學校，未來可延伸到不同類型的大型建築與室內外複合場域。

專案會把樓層 SVG、校園 SVG、手動 edge、POI metadata CSV 轉成 runtime JSON，後端用 FastAPI 提供地圖資料與路線 API，前端用單頁 HTML/CSS/JavaScript Canvas 呈現互動式導航介面。

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

## 技術架構

- Backend：FastAPI、Uvicorn、Python 3.12
- Data pipeline：Python、BeautifulSoup、lxml
- Frontend：單一 `frontend/index.html`，使用 HTML/CSS/JavaScript 與 HTML5 Canvas 繪圖
- 部署：Vercel Services，靜態前端 + FastAPI 後端
- 本機開發：Conda

## 線上展示

試用部署於 Vercel 的[公開線上展示](https://sip-eight-nu.vercel.app)：以 2D / 2.5D 視圖探索台科大校園、搜尋目的地，並比較最短距離、電梯優先與雨天路徑。

展示使用靜態 HTML/CSS/JavaScript + Canvas 前端與 FastAPI 後端，`/api/data` 和 `/api/route` 由同一個部署與網域提供。展示使用的 generated runtime 空間資料為公開資料；授權／私有的原始樓層 SVG 圖檔仍排除於 Git 與公開部署之外。

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

## 部署

線上展示使用 Vercel Services，由 `vercel.json` 設定：

- `frontend/` 是靜態前端服務，不需建置步驟，提供 `frontend/index.html`。
- 儲存庫根目錄是 FastAPI 後端服務，entrypoint 為 `backend.main:app`。
- `/api/*` 導向後端並保留原始 API 路徑；其餘路徑導向前端。
- 後端透過由 `__file__` 解析的路徑，讀取儲存庫根目錄 `data/` 下的 runtime 資料。

`requirements.txt` 宣告提供服務所需的相依套件，`.python-version` 指定 Python 3.12。部署使用既有的 generated runtime 資料；空間資料 pipeline 維持為獨立的本機工作流程。

安裝 Vercel CLI 並備妥 Python 3.12 後，在儲存庫根目錄執行本機 Vercel 相容測試：

```bash
vercel dev -L
```

在儲存庫根目錄執行正式部署：

```bash
vercel --prod
```

## 公開與私有資料

公開 repo 不包含 `A*_map.svg` 室內樓層 SVG。這些檔案包含向學校申請的建築圖，僅供本機學術研究使用。

可公開資料：

- `data/source/public/svg/campus/L01_CampusLayout.svg`
- source edge files
- metadata CSV files
- 線上展示使用的 generated runtime JSON files；其中的空間資料透過 `/api/data` 公開提供

本機私有資料：

- `data/source/private/svg/floors/A*_map.svg`

Pipeline 預設會從 `data/source/private/svg/floors/` 讀取室內樓層 SVG。這個資料夾已被 Git 忽略，並由 `.vercelignore` 排除於公開部署之外。排除原始圖檔不代表 generated runtime 空間資料也是私有資料。若私有檔案放在其他位置，可以設定：

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
- `faculty_leads`：實驗室主持人，搜尋會使用。
- `occupants`：辦公室使用者，搜尋會使用。
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

## 儲存庫結構

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
|-- requirements.txt
|-- .python-version
|-- vercel.json
|-- .vercelignore
|-- README.md
`-- README.zh-TW.md
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

## Future Work

目前版本聚焦於完成一個可運作的多樓層、跨建築空間導航原型。未來可持續探索以下方向：

### 1. AI-assisted Map-to-Graph

降低從 2D 平面圖建立導航圖資時所需的人工成本。  
可能的流程如下：

**Floor Plan -> AI / Rule-based Graph Proposal -> Validation -> Human Review -> Navigable Graph**

潛在任務包含節點放置、edge 產生、走廊與門口偵測，以及垂直連通關係推論。

### 2. Event-aware and Task-based Navigation

將平台從單純的點到點導航，延伸到能整合臨時活動、排程與任務資訊的導航服務。

潛在應用包含：

- 研討會與校園活動排程
- 考場導航
- 多站點路線規劃
- 移動時間與行程衝突檢查
- 以自然語言輸入偏好，產生個人化行程

### 3. Campus Space Allocation and Optimization

運用空間 metadata 支援校園尺度的空間規劃與教室分配。

系統可依據以下條件推薦替代的課程與教室配置：

- 教室容量
- 所需設備與設施
- 課程時間
- 時段衝突
- 空間效率與移動距離

### 4. Positioning and Accessibility

整合 Wi-Fi-based 或 visual localization 等室內定位方式，降低使用者手動選擇起點的負擔。

路線規劃也可進一步加入無障礙條件，例如：

- 避開樓梯
- 電梯優先
- 無障礙入口與坡道
- 經確認的無障礙路線

這些方向將 SIP 從單純的**空間建圖與導航**，延伸到更智慧的**空間規劃、管理與決策支援**。
