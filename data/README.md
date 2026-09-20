# Data

Local data artifacts for development live here.

- `downloads/` holds DFP PDFs downloaded manually from CVM's filing-search system, grouped by year, plus a hand-maintained `manifest.json`.
- `markdown/` holds Docling-converted Markdown exports with the same year layout and manifest.
- Downloaded and converted payloads are gitignored because the corpus can get large.
- CVM has no scriptable per-filing API like SEC EDGAR's, and its filing-search endpoint is reCAPTCHA-gated (v3, escalating to an interactive v2 challenge), so there's no `download.py` —  download each DFP PDF by hand and record it in `data/downloads/manifest.json`. See the root [README.md](../README.md#sample-cvm-data) for the manual steps and the manifest schema.
- Convert downloaded PDFs to Markdown with `uv run data/convert_to_markdown.py`
