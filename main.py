from src.config import DATA_DIR
from src.hyperapi_client import HyperAPIClientWrapper
from src.normalizer import extract_vendor_master
from src.parser import parse_documents, split_pdf_into_chunks
from src.rules.basic_rules import run_basic_rules
from src.rules.vendor_rules import run_vendor_rules


def main() -> None:
    pdf_path = DATA_DIR / "gauntlet.pdf"

    if not pdf_path.exists():
        print(f"PDF not found at: {pdf_path}")
        print("Please place gauntlet.pdf inside the data folder.")
        return

    parsed = parse_documents(pdf_path)

    print("HyperAudit parser test successful.")
    print(f"File: {parsed['file_name']}")
    print(f"Total pages: {parsed['total_pages']}")

    preview_pages = parsed["pages"][:3]
    for page in preview_pages:
        print("-" * 50)
        print(f"Page {page['page_number']} | chars: {page['char_count']}")
        print(page["text"][:500].strip() or "[NO TEXT FOUND]")

    # --- Chunking test ---
    print("\n" + "=" * 50)
    print("Chunking gauntlet.pdf into 10-page chunks...")
    chunks = split_pdf_into_chunks(pdf_path, chunk_size=10)
    print(f"\nCreated {len(chunks)} chunk(s):")
    for chunk in chunks:
        print(f"  {chunk['chunk_file'].name}  (pages {chunk['start_page']}–{chunk['end_page']})")

    # --- HyperAPI smoke test (first chunk only) ---
    print("\n" + "=" * 50)
    print("HyperAPI smoke test on first chunk...")
    first_chunk = chunks[0]
    try:
        wrapper = HyperAPIClientWrapper()
        response = wrapper.parse(first_chunk["chunk_file"])

        print(f"  File   : {first_chunk['chunk_file'].name}")
        print(f"  Status : SUCCESS")
        print(f"  Keys   : {list(response.keys())}")

        # Print OCR text length if present under common key names
        for key in ("text", "ocr_text", "content", "ocr"):
            if key in response and isinstance(response[key], str):
                print(f"  OCR length ({key!r}): {len(response[key])} chars")
                break

    except ValueError as exc:
        print(f"  Config error: {exc}")
    except RuntimeError as exc:
        print(f"  API error: {exc}")

    # --- Vendor Master extraction ---
    print("\n" + "=" * 50)
    print("Extracting Vendor Master from pages 3–4...")
    vendors = extract_vendor_master(parsed)
    print(f"  Total vendors extracted: {len(vendors)}")
    print("\n  First 5 vendors:")
    for v in vendors[:5]:
        print(f"    [{v.vendor_id}] {v.name}")
        print(f"         GSTIN: {v.gstin}  |  State: {v.state}")
        print(f"         Bank:  {v.bank}  |  IFSC: {v.ifsc}")

    # --- Vendor rules ---
    print("\n" + "=" * 50)
    print("Running vendor anomaly rules...")
    findings = run_vendor_rules(parsed["pages"], vendors)

    from collections import Counter
    counts = Counter(f.category for f in findings)
    print(f"  Total candidate findings: {len(findings)}")
    for category, count in sorted(counts.items()):
        print(f"    {category}: {count}")

    # --- Basic rules (invalid_date, arithmetic_error) ---
    print("\n" + "=" * 50)
    print("Running basic rules (invalid_date, arithmetic_error)...")
    basic_findings = run_basic_rules(parsed["pages"])
    basic_counts = Counter(f.category for f in basic_findings)
    print(f"  Total candidate findings: {len(basic_findings)}")
    for category, count in sorted(basic_counts.items()):
        print(f"    {category}: {count}")
    print("\n  Sample findings (up to 3):")
    for f in basic_findings[:3]:
        print(f"    [{f.finding_id}] {f.description}")


if __name__ == "__main__":
    main()