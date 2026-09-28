# AGENTS guidelines

This is a data hoarding project, archiving maps created by the french minister of foreign affairs.

This is a python project, with self-contained `uv` based python script. No tests.

Images are stored in `./monde/`.

The maps are showcase in a static page publish on github pages, built using `build_site.py`.

`context.yaml` explains map updates (hand-written, not exhaustive, in French); its format is defined by the pydantic models in `build_site.py`, which validates it at build time.

- Run `./scrape.py` to fetch the current world warning map and is scheduled to run in a github ci workflow.
- Run `./backfill.py` to fetch old maps from the web archive.

Focus on the request. Do not suggest unrelated change.
