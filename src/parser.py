from pathlib import Path
from typing import Any
import re

from pypdf import PdfReader, PdfWriter

# Matches document reference IDs like INV-2025-00015, PO-2025-00024, FIL-2025-00042
_RE_DOC_REF = re.compile(r"\b[A-Z]{2,5}-\d{4}-\d+\b")


def extract_text_by_page(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Extract text from a PDF page by page.

    Returns a list of dicts like:
    {
        "page_number": 1,
        "text": "....",
        "char_count": 1234
    }
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(path))
    pages: list[dict[str, Any]] = []

    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            text = f"[ERROR EXTRACTING PAGE TEXT: {exc}]"

        pages.append(
            {
                "page_number": index,
                "text": text,
                "char_count": len(text),
            }
        )

    return pages


def parse_documents(pdf_path: str | Path) -> dict[str, Any]:
    """
    Minimal parsing pipeline for now.
    """
    pages = extract_text_by_page(pdf_path)

    return {
        "file_name": Path(pdf_path).name,
        "total_pages": len(pages),
        "pages": pages,
    }


def extract_doc_refs(text: str) -> list[str]:
    """
    Extract deduplicated document reference IDs from a block of text.
    Matches conservative patterns like INV-2025-00015, PO-2025-00024, FIL-2025-00042.
    Returns a sorted list of unique refs.
    """
    return sorted(set(_RE_DOC_REF.findall(text)))


def extract_page_doc_refs(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Return page-level doc ref metadata for pages that contain at least one ref.

    Returns a list of dicts:
    {
        "page_number": int,
        "doc_refs": ["INV-2025-00015", ...]
    }
    """
    result = []
    for page in pages:
        refs = extract_doc_refs(page["text"])
        if refs:
            result.append({"page_number": page["page_number"], "doc_refs": refs})
    return result


def export_page_range(
    pdf_path: str | Path,
    start_page: int,
    end_page: int,
    output_path: str | Path,
) -> Path:
    """
    Export a 1-indexed page range [start_page, end_page] from pdf_path into output_path.
    Both start_page and end_page are inclusive.
    """
    path = Path(pdf_path)
    output = Path(output_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(path))
    total = len(reader.pages)

    if start_page < 1 or end_page > total or start_page > end_page:
        raise ValueError(
            f"Invalid page range [{start_page}, {end_page}] for PDF with {total} pages."
        )

    writer = PdfWriter()
    for i in range(start_page - 1, end_page):  # convert to 0-indexed
        writer.add_page(reader.pages[i])

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as f:
        writer.write(f)

    return output


def split_pdf_into_chunks(
    pdf_path: str | Path,
    chunk_size: int = 10,
) -> list[dict[str, Any]]:
    """
    Split a PDF into chunks of up to chunk_size pages each.
    Saves chunk files under cache/chunks/ relative to the project root.
    Returns a list of dicts:
    {
        "chunk_file": Path,
        "start_page": int,   # 1-indexed
        "end_page": int,     # 1-indexed, inclusive
    }
    """
    path = Path(pdf_path)
    reader = PdfReader(str(path))
    total = len(reader.pages)

    chunks_dir = Path("cache/chunks")
    chunks_dir.mkdir(parents=True, exist_ok=True)

    stem = path.stem
    results: list[dict[str, Any]] = []

    start = 1
    chunk_index = 1
    while start <= total:
        end = min(start + chunk_size - 1, total)
        output_path = chunks_dir / f"{stem}_chunk{chunk_index:03d}_p{start}-{end}.pdf"

        export_page_range(path, start, end, output_path)

        results.append(
            {
                "chunk_file": output_path,
                "start_page": start,
                "end_page": end,
            }
        )

        print(f"  [chunk {chunk_index:03d}] pages {start}–{end} → {output_path}")

        start = end + 1
        chunk_index += 1

    return results
