"""
Recursively convert every PDF under a folder to Markdown.

The .md is written next to its source PDF

Usage:
    python converter.py <root_folder> [--overwrite] [--strip-images/--keep-images]
"""

import re
import sys
import time
import logging
import argparse
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat, ConversionStatus
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    ThreadedPdfPipelineOptions,
)
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
_log = logging.getLogger(__name__)
logging.getLogger("docling").setLevel(logging.WARNING)


def build_converter() -> DocumentConverter:
    """Built once and reused for every file."""
    pipeline_options = ThreadedPdfPipelineOptions(
        accelerator_options=AcceleratorOptions(
            device=AcceleratorDevice.AUTO,
            num_threads=8,
        ),
        layout_batch_size=64,
        table_batch_size=4,
        ocr_batch_size=4,
        do_ocr=False,
        do_table_structure=True,
        generate_picture_images=False,
        generate_page_images=False,
    )
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=ThreadedStandardPdfPipeline,
                pipeline_options=pipeline_options,
            )
        }
    )


def find_pdfs(root: Path) -> list[Path]:
    """All PDFs under root, recursively, case-insensitive, deduplicated."""
    found = {p.resolve() for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"}
    return sorted(found)


def clean_markdown(markdown: str) -> str:
    markdown = re.sub(r"[ \t]*<!--\s*image\s*-->[ \t]*\n?", "", markdown)
    return re.sub(r"\n{3,}", "\n\n", markdown)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-convert PDFs to Markdown in place.")
    parser.add_argument("root", type=Path, help="Folder to walk recursively")
    parser.add_argument("--overwrite", action="store_true",
                        help="Reconvert files whose .md already exists (default: skip)")
    parser.add_argument("--keep-images", action="store_true",
                        help="Keep the <!-- image --> placeholders in the output")
    args = parser.parse_args()

    if not args.root:
        _log.error("Missing root folder argument")
        return 1

    if not args.root.exists():
        _log.error(f"Path does not exist: {args.root}")
        return 1

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        _log.error(f"Not a directory: {root}")
        return 1

    pdfs = find_pdfs(root)
    if not pdfs:
        _log.warning(f"No PDFs found under {root}")
        return 0

    todo, skipped = [], []
    for pdf in pdfs:
        if pdf.with_suffix(".md").exists() and not args.overwrite:
            skipped.append(pdf)
        else:
            todo.append(pdf)

    _log.info(f"Found {len(pdfs)} PDF(s) under {root}")
    if skipped:
        _log.info(f"Skipping {len(skipped)} already converted (use --overwrite to force)")
    if not todo:
        return 0

    _log.info("Loading models...")
    converter = build_converter()

    ok = failed = 0
    started = time.perf_counter()

    for i, pdf in enumerate(todo, 1):
        rel = pdf.relative_to(root)
        t0 = time.perf_counter()
        try:
            result = converter.convert(pdf, raises_on_error=False)

            if result.status in (ConversionStatus.FAILURE, ConversionStatus.SKIPPED):
                failed += 1
                _log.error(f"[{i}/{len(todo)}] FAILED {rel} ({result.status})")
                for err in result.errors:
                    _log.error(f"    {err}")
                continue

            markdown = result.document.export_to_markdown()
            if not args.keep_images:
                markdown = clean_markdown(markdown)

            out_path = pdf.with_suffix(".md")
            out_path.write_text(markdown, encoding="utf-8")

            ok += 1
            elapsed = time.perf_counter() - t0
            note = " (partial)" if result.status == ConversionStatus.PARTIAL_SUCCESS else ""
            _log.info(f"[{i}/{len(todo)}] OK{note} {rel} -> {out_path.name} ({elapsed:.1f}s)")

        except KeyboardInterrupt:
            _log.warning("Interrupted by user.")
            break
        except Exception as e:
            failed += 1
            _log.exception(f"[{i}/{len(todo)}] ERROR {rel}: {e}")

    total = time.perf_counter() - started
    print(f"\nDone in {total:.1f}s — {ok} converted, {failed} failed, {len(skipped)} skipped.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())