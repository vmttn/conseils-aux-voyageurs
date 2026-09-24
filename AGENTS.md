# AGENTS guidelines

This is a data hoarding project, archiving maps created by the french minister of foreign affairs.

This is a python project, with self-contained `uv` based python script. No tests.

Images are stored in `./monde/`.

- Run `./scrape.py` to fetch the current world warning map and is scheduled to run in a github ci workflow.
- Run `./backfill.py` to fetch old maps from the web archive.

Focus on the request. Do not suggest unrelated change.
