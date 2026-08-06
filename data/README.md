# Data Layout

`source/` is the hand-maintained source of truth. Edit these files when SVG maps,
manual edges, or POI connection overrides change.

```text
source/
|-- svg/
|   |-- floors/A*_map.svg
|   `-- campus/L01_CampusLayout.svg
|-- edges/
|   |-- indoor_edges.json
|   `-- campus_edges.json
`-- overrides/connection_overrides.json
```

`generated/` is written by `python run_pipeline.py`. Do not edit these files
directly; regenerate them after changing files under `source/` or `metadata/`.

```text
generated/
|-- routing_nodes.json
|-- pois.json
|-- pois_enriched.json
|-- slabs.json
|-- draft_connection.json
|-- final_connections.json
`-- campus_features.json
```

`metadata/` contains CSV and JSON metadata maintained by hand.

`legacy/` contains older auxiliary data that is not part of the current pipeline.

## Rebuild Campus Edges

If the campus graph is wrong and you want to redraw it in Developer Edge Editor:

1. Change `source/edges/campus_edges.json` to an empty draft:

   ```json
   {
     "校園動線 Draft": []
   }
   ```

2. Run `python run_pipeline.py`.
3. Start the backend and open the app in campus mode.
4. Draw the new campus edges in Developer Edge Editor.
5. Export `campus_edges.json`.
6. Replace or merge the exported edges into `source/edges/campus_edges.json`.
7. Run `python run_pipeline.py` again.

You do not need to delete files under `generated/`; the pipeline overwrites them.
