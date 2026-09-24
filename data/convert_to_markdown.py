"""Convert downloaded CVM DFP PDFs to Markdown + DoclingDocument JSON.

Reads data/downloads/manifest.json, converts each filing's PDF, and writes
both the Markdown export and the DoclingDocument itself (`.docling.json`)
under data/markdown/ with the same <year>/<file> layout, plus a mirrored
manifest.json pointing at the .md files. A filing is only considered done
once both files exist, so re-running only processes new or incomplete ones.

Also writes data/markdown/conversion_log.json — a per-run record (config,
per-filing status/duration/errors, aggregate stats) so a later reader can
see how a given corpus was produced without re-running the conversion.
See data/README.md for why TableFormerMode.FAST is used here.

Run from the backend project, since docling is declared there:
    uv run --project backend data/convert_to_markdown.py
"""

import json
import logging
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

DATA_DIR = Path(__file__).parent
DOWNLOADS_DIR = DATA_DIR / "downloads"
MARKDOWN_DIR = DATA_DIR / "markdown"

TABLE_MODE = TableFormerMode.FAST

# Some failures embed a huge generated source dump in the exception text
# (seen with a CUDA kernel compile error on Colab) -- cap it so one failure
# can't blow the conversion log up to tens of MB.
MAX_ERROR_MESSAGE_LENGTH = 2000

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def build_converter() -> DocumentConverter:
    pipeline_options = PdfPipelineOptions(do_table_structure=True)
    pipeline_options.table_structure_options.mode = TABLE_MODE
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)})


def load_manifest() -> dict:
    return json.loads((DOWNLOADS_DIR / "manifest.json").read_text(encoding="utf-8"))


def markdown_path(local_path: str) -> Path:
    return MARKDOWN_DIR / Path(local_path).with_suffix(".md")


def docling_json_path(local_path: str) -> Path:
    # The DoclingDocument itself, not just its Markdown export -- see
    # data/README.md. backend/ingest/chunking.py reads this, not the .md.
    return MARKDOWN_DIR / Path(local_path).with_suffix(".docling.json")


def is_done(local_path: str) -> bool:
    return markdown_path(local_path).exists() and docling_json_path(local_path).exists()


def main() -> None:
    run_started_at = datetime.now(UTC)
    manifest = load_manifest()

    pending = [filing for filing in manifest["filings"] if not is_done(filing["local_path"])]
    skipped = len(manifest["filings"]) - len(pending)
    if skipped:
        logger.info("Skipping %d already-converted filing(s)", skipped)

    filing_runs = []
    if pending:
        converter = build_converter()
        pdf_paths = [DOWNLOADS_DIR / filing["local_path"] for filing in pending]

        started_at = time.monotonic()
        results = converter.convert_all(pdf_paths, raises_on_error=False)

        # convert_all() is a lazy generator: the blocking work for each item
        # happens during the implicit next() that produces it, so the gap
        # since the previous checkpoint is that filing's conversion time.
        checkpoint = started_at
        for filing, result in zip(pending, results, strict=True):
            now = time.monotonic()
            duration_seconds = now - checkpoint
            checkpoint = now

            out_path = markdown_path(filing["local_path"])
            errors = [error.error_message[:MAX_ERROR_MESSAGE_LENGTH] for error in result.errors]

            if result.status in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(result.document.export_to_markdown(), encoding="utf-8")
                result.document.save_as_json(docling_json_path(filing["local_path"]))
                logger.info(
                    "Converted %s -> %s (%.1fs)", filing["local_path"], out_path.relative_to(DATA_DIR), duration_seconds
                )
                for message in errors:
                    logger.warning("  %s: %s", filing["local_path"], message)
            else:
                logger.error("Failed to convert %s (%.1fs)", filing["local_path"], duration_seconds)
                for message in errors:
                    logger.error("  %s: %s", filing["local_path"], message)

            filing_runs.append(
                {
                    "ticker": filing["ticker"],
                    "fiscal_year": filing["fiscal_year"],
                    "local_path": filing["local_path"],
                    "status": result.status.value,
                    "duration_seconds": round(duration_seconds, 1),
                    "errors": errors,
                }
            )

        logger.info("Converted %d filing(s) in %.1fs total", len(pending), time.monotonic() - started_at)

    write_markdown_manifest(manifest)
    write_conversion_log(run_started_at, filing_runs, total_filings=len(manifest["filings"]), skipped=skipped)


def write_markdown_manifest(manifest: dict) -> None:
    converted_filings = [
        {**filing, "local_path": str(Path(filing["local_path"]).with_suffix(".md"))}
        for filing in manifest["filings"]
        if is_done(filing["local_path"])
    ]
    converted_manifest = {**manifest, "filings": converted_filings}

    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    (MARKDOWN_DIR / "manifest.json").write_text(
        json.dumps(converted_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info(
        "Wrote data/markdown/manifest.json with %d/%d filing(s)",
        len(converted_filings),
        len(manifest["filings"]),
    )


def write_conversion_log(run_started_at: datetime, filing_runs: list[dict], *, total_filings: int, skipped: int) -> None:
    succeeded = sum(1 for run in filing_runs if run["status"] == ConversionStatus.SUCCESS.value)
    partial = sum(1 for run in filing_runs if run["status"] == ConversionStatus.PARTIAL_SUCCESS.value)
    failed = len(filing_runs) - succeeded - partial

    log = {
        "run_started_at": run_started_at.isoformat(),
        "docling_version": version("docling"),
        "pipeline_options": {"do_table_structure": True, "table_structure_mode": TABLE_MODE.value},
        "total_filings": total_filings,
        "skipped_already_converted": skipped,
        "attempted": len(filing_runs),
        "succeeded": succeeded,
        "partial_success": partial,
        "failed": failed,
        "total_duration_seconds": round(sum(run["duration_seconds"] for run in filing_runs), 1),
        "filings": filing_runs,
    }

    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    (MARKDOWN_DIR / "conversion_log.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("Wrote data/markdown/conversion_log.json")


if __name__ == "__main__":
    main()
