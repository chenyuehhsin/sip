# SIP: Smart Indoor and Campus Navigation

SIP is a prototype navigation system for complex indoor and campus environments. It converts SVG floor plans, campus maps, manually maintained edge files, and POI metadata CSV files into runtime JSON data. A FastAPI backend serves map data and routing APIs, while a single-page Canvas frontend provides interactive 2D / 2.5D visualization.

The current demo focuses on the NTUST campus and buildings such as RB, T1, T4, and AU. It supports indoor routing, multi-floor routing, cross-building connections, campus routing, POI search, department-based visualization, and several route preferences.

Traditional Chinese documentation is available in [README.zh-TW.md](README.zh-TW.md).

## Features

- Integrated indoor and campus routing graph.
- POI endpoints for classrooms, laboratories, offices, water fountains, and service spaces.
- Start and destination search by `id`, `name_zh`, `name_en`, `aliases`, `faculty_leads`, and `occupants`.
- Route modes:
  - Shortest distance
  - Elevator preferred
  - Rainy route, which prefers `CoveredPath-*` / `covered_walkway` edges
- View groups:
  - Indoor Building: building space, indoor service, horizontal circulation, vertical circulation, massing view
  - Campus Layout: campus mode
  - Department Attributes: department classification, nodes only, design, architecture, computer science, applied foreign languages, and other
- Campus labels for buildings and campus POIs.
- Department-based node and floor coloring from POI `department` metadata.
- Hover capsules for POIs, including location and department metadata.
- Developer Edge Editor support for maintaining indoor and campus edge sources.
- Experimental Academic Community View is kept in the codebase but hidden from the production view menu unless beta/debug mode is enabled.

## Tech Stack

- Backend: FastAPI, Uvicorn, Python 3.12
- Data pipeline: Python, BeautifulSoup, lxml
- Frontend: single-file HTML/CSS/JavaScript with HTML5 Canvas
- Environment: Conda

## Quick Start

Create the Conda environment:

```bash
conda env create -f environment.yml
conda activate indoor
```

Start the backend from the repository root:

```bash
conda run --no-capture-output -n indoor python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open the app:

```text
http://127.0.0.1:8000
```

If `--reload` fails because file watching is unavailable in the current environment, run without reload:

```bash
conda run --no-capture-output -n indoor python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Public vs Private Data

The public repository intentionally does not include the licensed indoor floor-plan SVG files named `A*_map.svg`. Those files contain building drawings that are only available for local academic research use.

Public data:

- `data/source/public/svg/campus/L01_CampusLayout.svg`
- source edge files
- metadata CSV files
- generated JSON files, for now

Private local data:

- `data/source/private/svg/floors/A*_map.svg`

The pipeline reads private floor SVGs from `data/source/private/svg/floors/` by default. This directory is ignored by Git. If your private files live elsewhere, set:

```bash
SIP_FLOOR_SVG_DIR=/path/to/private/floors conda run --no-capture-output -n indoor python run_pipeline.py
```

## Common Commands

Rebuild all generated map and metadata files:

```bash
conda run --no-capture-output -n indoor python run_pipeline.py
```

Validate `poi_master.csv` and print fixable CSV errors with line numbers:

```bash
conda run --no-capture-output -n indoor python scripts/check_poi_master.py
```

Only merge POI metadata into generated POIs:

```bash
conda run --no-capture-output -n indoor python scripts/enrich_pois.py
```

Check backend Python syntax:

```bash
python -m py_compile backend/main.py
```

## Data Update Workflow

### Updating `poi_master.csv`

Use this flow when editing POI names, departments, teachers, aliases, categories, or other metadata:

1. Edit `data/metadata/poi_master.csv`.
2. Validate the CSV:

   ```bash
   conda run --no-capture-output -n indoor python scripts/check_poi_master.py
   ```

3. Rebuild enriched POIs:

   ```bash
   conda run --no-capture-output -n indoor python scripts/enrich_pois.py
   ```

4. Restart the backend if it is already running, unless it is running with `--reload`.

If SVG files, edge files, or connection overrides changed, run the full pipeline instead:

```bash
conda run --no-capture-output -n indoor python run_pipeline.py
```

### Updating SVG Nodes

Use this flow when adding, deleting, or moving nodes in SVG files:

1. Edit private indoor SVG files under `data/source/private/svg/floors/A*_map.svg`, or edit the public campus SVG at `data/source/public/svg/campus/L01_CampusLayout.svg`.
2. Confirm that important objects have stable `inkscape:label` values.
3. Run the full pipeline:

   ```bash
   conda run --no-capture-output -n indoor python run_pipeline.py
   ```

4. Restart the backend and refresh the browser.

### Updating Edges

The source of truth for edges and connection overrides is:

- `data/source/edges/indoor_edges.json`
- `data/source/edges/campus_edges.json`
- `data/source/overrides/connection_overrides.json`

Do not manually edit files under `data/generated/`. They are pipeline outputs and will be overwritten.

Recommended campus edge editing flow:

1. Back up and edit `data/source/edges/campus_edges.json`.
2. Run the full pipeline.
3. Open the app and inspect or redraw edges with Developer Edge Editor.
4. Export the edited edge file.
5. Merge the exported result back into `data/source/edges/campus_edges.json`.
6. Run the full pipeline again.

You usually do not need to delete files under `data/generated/`; the pipeline overwrites the generated outputs.

## POI Metadata Schema

`data/metadata/poi_master.csv` uses this schema:

```text
id,name_zh,name_en,category,department,faculty_leads,occupants,aliases,description,public_access,source,status
```

Field meanings:

- `id`: must match a POI ID parsed from SVG.
- `name_zh`: Chinese display name.
- `name_en`: English display name.
- `category`: category value, validated against `data/metadata/dictionary.csv`.
- `department`: department or organizational unit. Department views use this field.
- `faculty_leads`: laboratory faculty leads. Search and Academic Community beta use this field.
- `occupants`: office occupants. Search and Academic Community beta use this field.
- `aliases`: aliases, old room numbers, or shorthand values. Search uses this field.
- `description`: optional detail text.
- `public_access`: access status, such as `public` or `restricted`.
- `source`: metadata source.
- `status`: lifecycle status, such as `active`.

Use semicolons for multi-value fields:

```text
faculty_leads: Wang Xiaoming;Lee Xiaohua
occupants: Wang Xiaoming;Lee Xiaohua
aliases: RB308;RB-308-1
```

## SVG Naming Rules

The parser primarily reads `inkscape:label` from SVG elements. Keep IDs stable because edges, metadata, and connection overrides may reference them.

Common naming patterns:

- Indoor routing node: `RB-100-1`, `T4-300-2`
- Stair node: `RB-SA-3F`
- Elevator node: `RB-E1-3F`
- Cross-building connector: `C-T4-2F-to-T1-2F`
- POI: `RB-308-1`, `T4-512`
- Water fountain: `{building}-{floor}F-WF-{number}`, for example `RB-3F-WF-1`
- Campus gate: `Gate-101`
- Campus outdoor path: `Path-101`
- Covered walkway: `CoveredPath-101`
- Building entrance or campus anchor: `Building-RB-1`

Water fountains are parsed as POIs and connected to the nearest valid navigation node by the pipeline. For complete search and display behavior, also add them to `poi_master.csv`.

Stairs and elevators usually do not need rows in `poi_master.csv`. They are routing nodes, not regular POIs. The frontend already displays them as stair/elevator locations in search and hover UI.

## Repository Layout

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
|   |   |       `-- floors/         # Public placeholder only; private A*.svg is not committed
|   |   |-- private/                # Ignored by Git; local licensed floor SVGs
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
|-- README.md
`-- README.zh-TW.md
```

### `data/source/`

Hand-maintained source map data. Edit this directory when SVG files, edge files, or connection overrides change.

### `data/metadata/`

Hand-maintained metadata. POI names, departments, faculty names, aliases, and campus POI labels live here.

### `data/generated/`

Pipeline outputs. Do not edit these files directly.

The backend loads these files at startup:

- `data/generated/routing_nodes.json`
- `data/generated/pois_enriched.json`
- `data/generated/slabs.json`
- `data/generated/campus_features.json`
- `data/generated/final_connections.json`
- `data/metadata/poi_campus.csv`

## Pipeline

The full pipeline is orchestrated by `run_pipeline.py`:

1. `scripts/1_svg_parser.py`
   - Parses indoor floor SVG files.
   - Parses the L01 campus SVG.
   - Merges indoor and campus edge source files.
   - Writes routing nodes, POI geometry, and slabs.

2. `scripts/enrich_pois.py`
   - Reads `data/generated/pois.json`.
   - Reads `data/metadata/poi_master.csv`.
   - Validates required fields, duplicate IDs, and categories.
   - Writes `data/generated/pois_enriched.json`.

3. `scripts/2_knn_recommender.py`
   - Recommends nearby routing-node connections for POIs.
   - Writes `data/generated/draft_connection.json`.

4. `scripts/3_merge_connections.py`
   - Applies manual add/remove connection overrides.
   - Writes `data/generated/final_connections.json`.

5. `scripts/4_campus_features_parser.py`
   - Parses campus building footprints and outdoor areas.
   - Writes `data/generated/campus_features.json`.

## API

### `GET /`

Serves `frontend/index.html`.

### `GET /api/data`

Returns frontend rendering data:

- `nodes`
- `edges`
- `pois`
- `slabs`
- `campus_features`
- `campus_pois`
- `connections`

### `GET /api/route`

Query parameters:

- `start`: start node or POI ID
- `end`: destination node or POI ID
- `mode`: `shortest`, `elevator_preferred`, or `rainy_preferred`

Example:

```bash
curl "http://127.0.0.1:8000/api/route?start=T4-512&end=RB-308-1&mode=shortest"
```

## Frontend Notes

The main frontend implementation is in `frontend/index.html`.

Important state variables:

- `currentViewMode`: active view mode.
- `currentDepartmentSubMode`: active department sub-mode.
- `currentRouteMode`: active route preference.
- `selectedSpaceIds`: selected start and destination.
- `currentRoute`: active navigation result.

Search sources:

- `poisData`
- `nodesData`

Searchable fields:

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

Academic Community View is experimental and hidden from the production view menu by default.

Enable it with:

```text
http://127.0.0.1:8000?academic_beta=1
```

or:

```text
http://127.0.0.1:8000?debug=1
```

This feature dynamically builds a test community graph from `pois_enriched.json` in the frontend. It does not modify the routing graph, raw edges, or POI source data.

## Troubleshooting

### The page does not reflect recent `poi_master.csv` changes

Regenerate `pois_enriched.json`:

```bash
conda run --no-capture-output -n indoor python scripts/enrich_pois.py
```

Then restart the backend unless it is running with `--reload`.

### SVG or edge changes do not appear

Run the full pipeline:

```bash
conda run --no-capture-output -n indoor python run_pipeline.py
```

Then restart the backend and refresh the page.

### Should `data/generated/` be deleted?

Usually no. The pipeline overwrites generated outputs.

### Should water fountains be added to `poi_master.csv`?

Recommended. The parser can detect `*-WF-*` nodes as POIs, but CSV metadata makes names, categories, search, and display behavior more complete.

### Should stairs and elevators be added to `poi_master.csv`?

Usually no. Stairs and elevators are routing nodes. The frontend already displays them as readable stair/elevator locations in search and hover UI.

### Developer Edge Editor import does not appear to work

Confirm that the edited data is being written back to the source edge files:

- `data/source/edges/indoor_edges.json`
- `data/source/edges/campus_edges.json`

Then run `run_pipeline.py`. Do not edit `data/generated/routing_nodes.json` directly because it is overwritten by the pipeline.

## Development Notes

- Run commands from the repository root.
- Treat `data/source/` and `data/metadata/` as the maintained source of truth.
- Treat `data/generated/` as build output.
- Refresh the browser after frontend changes.
- Restart the backend after backend or generated-data changes, unless using `--reload`.
- Do not write Academic Community beta edges into the routing graph.
- Do not infer cross-department, collaboration, or semantic relationships without explicit metadata.
