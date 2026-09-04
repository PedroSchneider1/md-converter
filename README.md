# PDF → Markdown Converter

Recursively converts every PDF under a folder to Markdown using [Docling](https://github.com/docling-project/docling). Each `.md` file is written **next to its source PDF** with the same name (e.g. `report.pdf` → `report.md`).

## Requirements

- Python 3.9+
- [Docling](https://pypi.org/project/docling/) (a recent version that includes the threaded PDF pipeline)
<<<<<<< HEAD
- NVIDIA GPU with CUDA (the accelerator device is hardcoded to CUDA — see [Notes](#notes) to run on CPU)

=======
  >A GPU is not mandatory, but is recommended
>>>>>>> dfff627 (fix: auto GPU detection, updated README)
```bash
pip install docling
```

## Usage

```bash
python converter.py <root_folder> [--overwrite] [--keep-images]
```

| Argument | Description |
|---|---|
| `root_folder` | Folder to walk recursively for PDFs (required) |
| `--overwrite` | Reconvert PDFs whose `.md` already exists (default: skip them) |
| `--keep-images` | Keep the `<!-- image -->` placeholders in the output (default: strip them) |

### Examples

```bash
# Convert everything under ./docs, skipping already-converted files
python converter.py ./docs

# Force reconversion of all PDFs
python converter.py ./docs --overwrite

# Keep image placeholders in the Markdown
python converter.py ./docs --keep-images
```

## Behavior

- Finds all `.pdf` files recursively (case-insensitive, deduplicated).
- Skips any PDF that already has a sibling `.md` file, unless `--overwrite` is passed.
- Strips `<!-- image -->` placeholders and collapses extra blank lines by default.
- Logs progress per file with timing, and prints a final summary (converted / failed / skipped).
- A failed file doesn't stop the run — remaining PDFs are still processed.
- `Ctrl+C` stops the run gracefully.

**Exit codes:** `0` = success (or nothing to do), `1` = at least one conversion failed or the root path was invalid.

## Notes

- **OCR is disabled** (`do_ocr=False`), so scanned/image-only PDFs will produce little or no text. Set `do_ocr=True` in `build_converter()` if you need OCR.
- **Table structure recognition is enabled**, so tables are exported as Markdown tables.
- Page and picture images are not generated, keeping conversion fast and output lightweight.