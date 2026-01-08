"""Test script to find and extract OMICO invoices."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from extractors.omico import OmicoExtractor  # noqa: E402
from processors.document_processor import DocumentProcessor  # noqa: E402


def find_omico_invoice(bills_dir: str, max_files: int = 50) -> str | None:
    """
    Search through PDF files to find an OMICO invoice.

    Args:
        bills_dir: Directory containing PDF invoices
        max_files: Maximum number of files to search

    Returns:
        Path to OMICO invoice or None if not found
    """
    processor = DocumentProcessor()

    print(f"Searching for OMICO invoice in {bills_dir}...")
    print(f"Will check up to {max_files} files\n")

    files = sorted([f for f in os.listdir(bills_dir) if f.endswith(".pdf")])

    for i, filename in enumerate(files[:max_files]):
        if i > 0 and i % 10 == 0:
            print(f"Checked {i} files...")

        try:
            path = os.path.join(bills_dir, filename)
            doc_key = processor.convert_document(path)
            markdown = processor.get_document_markdown(doc_key, max_size=2000)

            # Check for OMICO identifiers
            if any(
                term in markdown.upper()
                for term in ["OMICO", "2025 RAGU DRIVE", "OWENSBORO"]
            ):
                print(f"\n✓ Found OMICO invoice: {filename}")
                return path

        except Exception as e:
            print(f"✗ Error processing {filename}: {e}")
            continue

    print(f"\n✗ No OMICO invoice found in first {max_files} files")
    return None


def test_omico_extraction(pdf_path: str) -> None:
    """
    Test OMICO extractor with a specific invoice.

    Args:
        pdf_path: Path to OMICO PDF invoice
    """
    print(f"\n{'=' * 60}")
    print("Testing OMICO Extractor")
    print(f"{'=' * 60}\n")
    print(f"File: {Path(pdf_path).name}\n")

    # Initialize
    processor = DocumentProcessor()
    extractor = OmicoExtractor(processor)

    # Process invoice
    print("Converting document...")
    doc_key = processor.convert_document(pdf_path)

    print("Extracting markdown...")
    markdown = processor.get_document_markdown(doc_key)

    print("Extracting invoice data...\n")
    invoice = extractor.extract(doc_key, markdown, Path(pdf_path).name)

    # Display results
    print(f"{'=' * 60}")
    print("EXTRACTION RESULTS")
    print(f"{'=' * 60}\n")

    print(f"Vendor: {invoice.vendor}")
    print(f"Invoice Number: {invoice.invoice_number}")
    print(f"Invoice Date: {invoice.invoice_date}")
    print(f"PO Number: {invoice.po_number}")
    print(f"Subtotal: ${invoice.subtotal}")
    print(f"Sales Tax: ${invoice.sales_tax}")
    print(f"Total: ${invoice.total}")
    print(f"Confidence: {invoice.extraction_confidence:.2%}")

    print(f"\nLine Items ({len(invoice.line_items)}):")
    for i, item in enumerate(invoice.line_items, 1):
        print(f"  {i}. {item.description}")
        print(
            f"     Qty: {item.quantity}, Price: ${item.price_each}, Amount: ${item.amount}"
        )
        if item.item_code:
            print(f"     Code: {item.item_code}")

    if invoice.extraction_errors:
        print(f"\nErrors ({len(invoice.extraction_errors)}):")
        for error in invoice.extraction_errors:
            print(f"  - {error}")

    print(f"\n{'=' * 60}")
    print("JSON OUTPUT")
    print(f"{'=' * 60}\n")
    print(invoice.model_dump_json(indent=2))


def main():
    """Main test function."""
    bills_dir = "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills"

    if not os.path.exists(bills_dir):
        print(f"Error: Directory not found: {bills_dir}")
        return

    # Try to find an OMICO invoice
    omico_path = find_omico_invoice(bills_dir, max_files=100)

    if not omico_path:
        print("\nNo OMICO invoice found. Please provide a sample invoice path.")
        print(
            "Usage: uv run python test_omico_extraction.py [path_to_omico_invoice.pdf]"
        )
        return

    # Test extraction
    test_omico_extraction(omico_path)


if __name__ == "__main__":
    # Allow command-line invoice path override
    if len(sys.argv) > 1:
        invoice_path = sys.argv[1]
        if os.path.exists(invoice_path):
            test_omico_extraction(invoice_path)
        else:
            print(f"Error: File not found: {invoice_path}")
    else:
        main()
