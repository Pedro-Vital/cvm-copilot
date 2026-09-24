# Data

Local data artifacts for development live here.

## Layout

- `downloads/` — DFP PDFs downloaded manually from CVM's filing-search system, grouped by year, plus a hand-maintained `manifest.json`.
- `markdown/` — Docling conversion output, same `<year>/<file>` layout and manifest shape as `downloads/`, two files per filing:
  - `<file>.md` — the Markdown export, for humans / quick inspection.
  - `<file>.docling.json` — the full `DoclingDocument`. **This is what `backend/ingest/chunking.py` actually reads**, not the Markdown — plain Markdown text has no page numbers, and Docling's own document model already knows unambiguously what's a real section versus a repeated running header, which the Markdown-only chunker used to have to reverse-engineer with a heuristic.
- Downloaded and converted payloads are gitignored (manifests stay tracked); the corpus can get large.

## Getting the corpus

CVM has no scriptable per-filing API like SEC EDGAR's, and its filing-search endpoint is reCAPTCHA-gated, so there's no `download.py` — download each DFP PDF by hand and record it in `data/downloads/manifest.json`. See the root [README.md](../README.md#sample-cvm-data) for the manual steps and manifest schema.

## Converting to Markdown (CPU)

```bash
uv run --project backend data/convert_to_markdown.py   # from the repo root
```

(Docling is a backend dev dependency and there's no root `pyproject.toml`, hence `--project backend`.) Already-converted filings are skipped on re-run — safe to interrupt and resume, including across a reboot.

The script uses `TableFormerMode.FAST` rather than `ACCURATE`. On a CPU-only 4-core/~12GB dev box, `ACCURATE` took 8+ minutes and was still running on the *smallest* filing in the corpus — not tractable across all 25. `FAST` still does real table-structure recognition, just with a lighter model, which is a reasonable trade for a RAG corpus (chunked and embedded, not displayed pixel-perfect).

Measured on that box: WEG 2021 (8MB, ~130 pages) took 28.8 min in `FAST` mode; ITAU's DFP (a large bank, much denser tables) didn't finish one filing in 90 min. At that pace the full corpus is a 15–25 hour unattended background job — see the [GPU option](#converting-to-markdown-gpu-via-google-colab) below to go faster.

Each run writes `markdown/conversion_log.json` (timestamp, Docling version, pipeline options, per-filing status/duration/errors) — a record of how the corpus was produced, readable without rerunning anything.

## Converting to Markdown (GPU, via Google Colab)

`cvm_docling_conversion.ipynb` is a Colab-ready version of the same conversion for when CPU conversion is too slow. It reads/writes Google Drive (`MyDrive/cvm-copilot/`), not the Colab VM's local disk, and writes each filing's Markdown — plus an updated `manifest.json`/`conversion_log.json` — immediately after that filing finishes, not batched at the end.

That durability matters because free-tier Colab **will** crash a session with "session crashed after using all available RAM," and did — repeatedly, within minutes each time, well before finishing even one filing. With per-file writes to Drive, a crash costs at most the one filing in flight; re-running the notebook reconnects to Drive and resumes (already-converted filings, and the one-time PDF upload, are both skipped automatically). Three things in the notebook specifically target that RAM ceiling:

- `TABLE_MODE = TableFormerMode.FAST`, not `ACCURATE` — `ACCURATE` is what first crashed a free-tier runtime this way; see the comment above `TABLE_MODE` if you want to try it anyway (e.g. on a High-RAM runtime, or in smaller batches).
- `do_ocr = False` — CVM DFPs are digitally-native PDFs, not scans, but OCR (with its own separate models) was running anyway; disabling it removes a whole memory-hungry pipeline stage for no quality loss.
- `layout_batch_size = table_batch_size = 1` (default `4`) — processing one page/table at a time instead of four trades some speed for a much lower peak.
- Filings are converted smallest-file-first, so a handful of outliers (one bank's DFP ran 4x the typical file size) don't block progress on everything else.

1. From `data/`: `zip -r downloads.zip downloads` (don't commit the zip — it's just an upload artifact).
2. [colab.research.google.com](https://colab.research.google.com) → `File → Upload notebook` → `cvm_docling_conversion.ipynb`.
3. `Runtime → Change runtime type → T4 GPU`. The notebook's second cell confirms CUDA is active before you proceed.
4. Run the cells top to bottom. The *first* run prompts for `downloads.zip`; later runs (including after a crash) skip that since it's already in Drive.
5. Pull the results into the repo either via Drive's own UI/desktop sync on `MyDrive/cvm-copilot/markdown/`, or run the notebook's last cell to zip and download them directly. Either way, copy into `data/markdown/` — same `<year>/<file>.md` layout, so it merges cleanly with (and is treated as already-converted by) the local CPU run.

Colab's own **preinstalled** `torch` can already be a CUDA 13 build (`torch==2.11.0+cu130` as observed), while the image doesn't ship the matching NVRTC runtime library — every conversion then fails with `nvrtc: error: failed to open libnvrtc-builtins.so.13.0`. This isn't docling upgrading `torch` to a broken build (an earlier version of the first cell assumed that and just pinned `torch` to whatever was already installed, which didn't help since that preinstalled build is the broken one). `pip install`ing `nvidia-cuda-nvrtc` (unsuffixed — the old `nvidia-cuda-nvrtc-cu13` name is a deprecated `0.0.1` placeholder, never a real build) pinned to `torch.version.cuda` puts the missing file on disk, but that alone is still not enough — it lands under `nvidia/cu13/lib/`, a path torch's own preload hook doesn't know about, so it's never actually picked up. The first cell now also explicitly targets that exact file, adds its directory to `LD_LIBRARY_PATH`, and preloads it with `ctypes.CDLL(..., mode=ctypes.RTLD_GLOBAL)` before any conversion runs — this part is **confirmed fixed**, live-tested with zero NVRTC errors across multiple runs, versus every prior attempt failing within 10–50 seconds. If you still hit the error after that, `Runtime → Disconnect and delete runtime` for a genuinely clean one.

**Separate, still-unresolved issue:** even past that fix, a live run crashed again with "session crashed after using all available RAM" — genuine system RAM exhaustion, not GPU memory — within ~10-12 minutes on the very first (smallest, converted first per the ordering above) filing, despite `FAST`/`do_ocr=False`/`batch_size=1` already being in place. The likely cause is that Colab's current preinstalled CUDA-13 torch build simply has a larger baseline memory footprint than whatever image this notebook was last verified against, but that's unconfirmed. Not yet resolved; options if you hit it: a Colab Pro / High-RAM runtime, cutting `PdfPipelineOptions.images_scale` or disabling table structure to test, or falling back to the local CPU script above (never hit this failure, just much slower).
