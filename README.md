# SIP: AI-Powered Spatial Intelligence Platform for Complex Multi-Building Environments

SIP (Spatial Intelligence Platform) 是一個專為複雜、錯層、多建築物室內環境設計的空間智慧與垂直尋路平台。本專案以大型迷宮建築（如台北車站、台科大校園）為實驗場域，擺脫傳統 2D 地圖無法處理垂直動線與空間錯位的限制，建構出具備高度擴充性的「三維拓撲路網」與「語意化導航引擎」。


## 環境建置與操作說明 (Quick Start)
```
# 根據設定檔建立名為 indoor 的虛擬環境
conda env create -f environment.yml
# 啟動虛擬環境
conda activate indoor
```
## 啟動 FastAPI 後端伺服器
```
uvicorn backend.main:app --reload
```

---

## 平台核心技術亮點 (Technical Wow Factors)

- **3D 錯層拓撲網路 (3D Topological Topology)**：完美封裝實體世界中的「空間錯位連通」邏輯（例如：A棟 3F 透過天橋連通至 B棟 4F），解決傳統 GIS 系統在垂直動線失靈的痛點。
- **動線語意化分類 (Semantic Graph Profiling)**：將路網分為 `backbone` (核心主幹道) 與 `walkway` (次要分支)，在圖論計算中引入環境權重。
- **自動化圖資生產管線 (Automated Spatial Data Pipeline)**：自繪向量圖資 (SVG) 後，透過 Python 正規表達式 (RegEx) 引擎，全自動解析語意化節點代號（如 `RB-WCM3`, `T1-SA-4F`）並輸出多樓層關聯資料綱要 (Schema)。
- **多維度路徑權重優化**：基於 Dijkstra 演算法，未來可動態擴充「時間懲罰權重」（如等待電梯時間成本、走樓梯體力消耗），實作更符合人類智慧的尋路。

---

## 系統架構 (Architecture)

本平台採用「高內聚、低耦合」的微服務平台架構設計：

- **資料層 (Data Layer)**：由向量圖資動態解析而來的 `map_data.json`，將 Routing Graph（導航骨架）與 POI Layer（教室、設施）完全分離，確保圖資擴充時演算法的 $O(V \log V + E)$ 效能不受影響。
- **後端引擎 (Backend Engine)**：基於 **FastAPI** 構建高性能非同步 API，實作拓撲圖論路徑計算。
- **前端畫布 (Frontend Canvas)**：採用原生 HTML5 Canvas 實作高性能輕量化渲染，支援動態樓層過濾器 (Floor Filter) 與連動式二級空間搜尋選單。

---

## 📂 專案檔案結構 (Repository Structure)

```text
sip/ (專案根目錄)
│
├── data/                    # 集中管理所有圖資與原始數據
│   ├── raw_edges.json       # 分棟模組化管理的原始連線數據
│   ├── map_data.json        # 經過 Python 腳本清洗、解析、吸附後的結構化核心圖資
│   └── A03_map.svg          # 你的多建築錯層拼接原始 SVG 向量圖資
│
├── backend/                 # 後端引擎模組 (高內聚設計)
│   ├── main.py              # FastAPI 路由、Dijkstra 尋路引擎與語意導航指引生成
│   └── utils/
│       └── validator.py     # 未來要擴充的 Graph Validator (圖資自動驗證腳本)
│
├── frontend/                # 前端視覺化與互動面板 (高內聚設計)
│   ├── index.html           # HTML5 Canvas 輕量化渲染、Floor Filter 與連動下拉選單
│   └── assets/              # 前端網頁專用的靜態資源 (如 CSS、小圖示)
│
├── scripts/                 # 自動化工具/腳本資料夾
│   └── tool_svg2json.py     # 你的資料清洗與 Regex 自動化 Parsing 數據管線
│
├── .gitignore               # Git 忽略清單 (防止暫存檔與 Mac 隱藏檔污染遠端倉庫)
├── environment.yml          # Anaconda 虛擬環境設定檔 (供開源與面試官一鍵復原環境)
└── README.md                # 你的頂級專案技術架構與戰略定位文件

