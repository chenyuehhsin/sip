# SIP: Spatial Intelligence Platform

SIP is a prototype indoor navigation platform for complex, multi-floor, multi-building environments. It builds a lightweight 3D topological routing graph from SVG floor maps, exposes routing and map data through a FastAPI backend, and renders an interactive campus navigation dashboard with HTML5 Canvas.

The current demo focuses on NTUST campus buildings such as RB, T1, T4, and AU. It supports cross-building links, vertical circulation, floor filtering, route alternatives, 2D/2.5D visualization, and a Chinese/English UI toggle. The default UI language is Chinese.

## Features

- Multi-building indoor routing across floors and connected buildings.
- Dijkstra-based shortest path search with a simple alternative route pass.
- Semantic edge types for walkways, bridges, stairs, and elevators.
- SVG-to-JSON data pipeline for routing nodes, POIs, floor slabs, and POI connections.
- Interactive Canvas dashboard with zoom, rotation, compass, scale bar, minimap, building filters, and 3D layer controls.
- Route selection between the main route and an available alternative route.
- Bilingual frontend UI toggle, defaulting to Chinese.

## Tech Stack

- Backend: FastAPI, Uvicorn, Python 3.12
- Data processing: Python, BeautifulSoup, lxml
- Frontend: single-file HTML, CSS, JavaScript, HTML5 Canvas
- Environment management: Conda

## Quick Start

Create and activate the Conda environment:

```bash
conda env create -f environment.yml
conda activate indoor
```

Start the FastAPI server from the repository root:

```bash
uvicorn backend.main:app --reload
```

Open the application:

```text
http://127.0.0.1:8000
```

## API Endpoints

### `GET /`

Serves the frontend dashboard from `frontend/index.html`.

### `GET /api/data`

Returns the map data needed by the frontend:

- `nodes`: routing graph nodes
- `edges`: routing graph edges
- `pois`: points of interest
- `slabs`: building slab geometry for 2.5D/3D rendering
- `connections`: final POI-to-routing-node connections

### `GET /api/route?start=<id>&end=<id>`

Returns a route between two node or POI IDs.

Response fields:

- `path`: main route node sequence
- `total_distance`: main route distance in meters
- `directions`: generated turn-by-turn route instructions
- `alt_path`: alternative route node sequence, if available
- `alt_distance`: alternative route distance

Example:

```bash
curl "http://127.0.0.1:8000/api/route?start=RB-308-3F&end=T4-402-4F"
```

## Data Pipeline

The data pipeline converts source SVG maps into runtime JSON files.

Run the complete pipeline:

```bash
python run_pipeline.py
```

Pipeline steps:

1. `scripts/1_svg_parser.py`
   - Reads `data/A*_map.svg`.
   - Extracts routing nodes, POIs, floor metadata, and slab geometry.
   - Reads `data/raw_edges.json`.
   - Writes `data/routing_nodes.json`, `data/pois.json`, and `data/slabs.json`.

2. `scripts/2_knn_recommender.py`
   - Connects each POI to nearby valid routing nodes on the same building and floor.
   - Writes `data/draft_connection.json`.

3. `scripts/3_merge_connections.py`
   - Applies manual add/remove overrides from `data/connection_overrides.json`.
   - Writes `data/final_connections.json`.

## Repository Structure

```text
sip/
|-- backend/
|   |-- main.py                  # FastAPI app, routing engine, API endpoints
|   `-- utils/
|       `-- validator.py         # Placeholder for graph validation utilities
|-- data/
|   |-- A*_map.svg               # Source SVG floor maps
|   |-- raw_edges.json           # Manually defined routing graph edges
|   |-- routing_nodes.json       # Generated routing nodes and edges
|   |-- pois.json                # Generated POI nodes
|   |-- slabs.json               # Generated building slab geometry
|   |-- draft_connection.json    # Generated POI connection candidates
|   |-- connection_overrides.json # Manual POI connection overrides
|   |-- final_connections.json   # Final POI connections used by the backend
|   `-- map_data.json            # Legacy or auxiliary map data
|-- frontend/
|   `-- index.html               # Canvas dashboard and interaction logic
|-- scripts/
|   |-- 1_svg_parser.py
|   |-- 2_knn_recommender.py
|   `-- 3_merge_connections.py
|-- run_pipeline.py              # Runs all data pipeline steps
|-- environment.yml              # Conda environment definition
`-- README.md
```

## SVG Authoring Conventions

The parser depends on naming and color conventions in the SVG files:

- Floor map files should follow the `A*_map.svg` naming pattern.
- Routing nodes and POIs are read from SVG `circle` elements.
- Node identity comes from `inkscape:label` or `id`.
- Floor slabs are read from `polygon` or `path` elements whose label or id starts with `floor-`.
- Orange nodes (`#ff9955`) are treated as POIs.
- Red, green, blue, and related route colors are mapped to routing-node categories used by the renderer and connection recommender.

## Important Runtime Files

The backend loads these files at startup:

- `data/routing_nodes.json`
- `data/pois.json`
- `data/slabs.json`
- `data/final_connections.json`

If any of these files are missing, run:

```bash
python run_pipeline.py
```

Then restart Uvicorn.

## Development Notes

- Run commands from the repository root so relative paths such as `data/routing_nodes.json` resolve correctly.
- The frontend is intentionally dependency-free and is served directly by FastAPI.
- The routing graph is undirected: every edge in `routing_nodes.json` is added in both directions by the backend.
- POIs are injected into a temporary local graph only when they are used as route endpoints.
- Vertical movement distance is currently estimated by floor difference, while same-floor movement uses calibrated map distance.

## Troubleshooting

If the server cannot find data files, regenerate the pipeline outputs:

```bash
python run_pipeline.py
```

If port `8000` is already in use, start Uvicorn on another port:

```bash
uvicorn backend.main:app --reload --port 8001
```

If the frontend does not reflect recent HTML changes, refresh the browser page after Uvicorn reloads.
