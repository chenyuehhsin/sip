# Public Floor SVG Placeholder

The real `A*_map.svg` indoor floor-plan files are intentionally not stored in
the public source tree because they contain licensed building drawings.

For local research and pipeline runs, place the private files under:

```text
data/source/private/svg/floors/
```

The pipeline reads that directory by default. You can override it with:

```bash
SIP_FLOOR_SVG_DIR=/path/to/private/floors python run_pipeline.py
```
