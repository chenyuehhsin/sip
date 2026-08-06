# SIP: Spatial Intelligence Platform

SIP is a prototype indoor navigation platform for complex, multi-floor, multi-building environments. It builds a lightweight 3D topological routing graph from SVG floor maps, exposes routing and map data through a FastAPI backend, and renders an interactive campus navigation dashboard with HTML5 Canvas.

The current demo focuses on NTUST campus buildings such as RB, T1, T4, and AU. It supports cross-building links, vertical circulation, floor filtering, route alternatives, 2D/2.5D visualization, and a Chinese/English UI toggle. The default UI language is Chinese.

## Features

- Multi-building indoor routing across floors and connected buildings.
- Dijkstra-based shortest path search with a simple alternative route pass.
- Semantic edge types for walkways, bridges, stairs, and elevators.
- SVG-to-JSON data pipeline for routing nodes, POIs, floor slabs, and POI connections.
- Campus footprint and outdoor-area overlays parsed from the L01 campus layout SVG.
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
- `campus_features`: aligned campus building footprints and outdoor areas

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
   - Reads `data/source/svg/floors/A*_map.svg` and `data/source/svg/campus/L01_CampusLayout.svg`.
   - Extracts indoor routing nodes, POIs, floor metadata, slab geometry, and campus-scale routing nodes.
   - Aligns L01 campus nodes into the A01 coordinate space using shared `Building-*` anchors.
   - Reads indoor edges from `data/source/edges/indoor_edges.json`.
   - Reads campus edges from `data/source/edges/campus_edges.json`.
   - Writes `data/generated/routing_nodes.json`, `data/generated/pois.json`, and `data/generated/slabs.json`.

2. `scripts/enrich_pois.py`
   - Merges generated POI geometry with CSV-maintained metadata.
   - Writes `data/generated/pois_enriched.json`.

3. `scripts/2_knn_recommender.py`
   - Connects each POI to nearby valid routing nodes on the same building and floor.
   - Writes `data/generated/draft_connection.json`.

4. `scripts/3_merge_connections.py`
   - Applies manual add/remove overrides from `data/source/overrides/connection_overrides.json`.
   - Writes `data/generated/final_connections.json`.

5. `scripts/4_campus_features_parser.py`
   - Reads `data/source/svg/campus/L01_CampusLayout.svg` and `data/source/svg/floors/A01_map.svg`.
   - Uses shared `Building-*` anchors to align campus-scale features into the A01 coordinate space.
   - Writes `data/generated/campus_features.json`.

## Repository Structure

```text
sip/
|-- backend/
|   |-- main.py                  # FastAPI app, routing engine, API endpoints
|   `-- utils/
|       `-- validator.py         # Placeholder for graph validation utilities
|-- data/
|   |-- source/                  # Hand-maintained source files
|   |   |-- svg/
|   |   |   |-- floors/A*_map.svg
|   |   |   `-- campus/L01_CampusLayout.svg
|   |   |-- edges/
|   |   |   |-- indoor_edges.json
|   |   |   `-- campus_edges.json
|   |   `-- overrides/connection_overrides.json
|   |-- generated/               # Pipeline outputs; regenerate instead of editing
|   |   |-- routing_nodes.json
|   |   |-- pois.json
|   |   |-- pois_enriched.json
|   |   |-- slabs.json
|   |   |-- draft_connection.json
|   |   |-- final_connections.json
|   |   `-- campus_features.json
|   |-- metadata/                # CSV and JSON metadata maintained by hand
|   `-- legacy/map_data.json     # Legacy or auxiliary map data
|-- frontend/
|   `-- index.html               # Canvas dashboard and interaction logic
|-- scripts/
|   |-- 1_svg_parser.py
|   |-- enrich_pois.py
|   |-- 2_knn_recommender.py
|   |-- 3_merge_connections.py
|   `-- 4_campus_features_parser.py
|-- run_pipeline.py              # Runs all data pipeline steps
|-- environment.yml              # Conda environment definition
`-- README.md
```

## SVG Authoring Conventions

The parser depends on naming and color conventions in the SVG files:

- Floor map files should follow the `A*_map.svg` naming pattern under `data/source/svg/floors/`.
- Routing nodes and POIs are read from SVG `circle` elements.
- Node identity comes from `inkscape:label` or `id`.
- Floor slabs are read from `polygon` or `path` elements whose label or id starts with `floor-`.
- Campus-scale routing nodes, footprints, and outdoor areas are read from `data/source/svg/campus/L01_CampusLayout.svg`.
- Shared `Building-*` anchor circles are used for L01-to-A01 alignment. In L01 they are emitted as campus `building_entry` routing nodes; in `A*_map.svg` they are ignored by the indoor parser.
- Orange nodes (`#ff9955`) are treated as POIs.
- Water fountain nodes named like `{building}-{floor}F-WF-{number}` are treated as POIs and connected to the nearest valid navigation node.
- Red, green, blue, and related route colors are mapped to routing-node categories used by the renderer and connection recommender.

## Important Runtime Files

The backend loads these files at startup:

- `data/generated/routing_nodes.json`
- `data/generated/pois_enriched.json`
- `data/generated/slabs.json`
- `data/generated/campus_features.json`
- `data/generated/final_connections.json`

If any of these files are missing, run:

```bash
python run_pipeline.py
```

Then restart Uvicorn.

## Development Notes

- Run commands from the repository root so relative paths such as `data/generated/routing_nodes.json` resolve correctly.
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
