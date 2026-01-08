"""Test script for invoice extraction."""

import sys
from pathlib import Path

from extractors.reflex_medical import ReflexMedicalExtractor

# Import models and processors


def test_reflex_medical_extraction():
    """Test extraction with a REFLEX MEDICAL invoice."""
    print("=" * 70)
    print("INVOICE EXTRACTION TEST - REFLEX MEDICAL CORP")
    print("=" * 70)
    print()

    # Sample invoice path
    pdf_path = "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Bill_62935_Inv_62935_from_REFLEX_MEDICAL_CORP_1280567_199.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ Error: Sample invoice not found at {pdf_path}")
        sys.exit(1)

    print(f"📄 Processing: {Path(pdf_path).name}")
    print()

    try:
        # Import MCP function - these are available in Claude Code environment
        from mcp__docling__convert_document_into_docling_document import (
            mcp__docling__convert_document_into_docling_document,  # noqa: F401
        )
        from mcp__docling__export_docling_document_to_markdown import (
            mcp__docling__export_docling_document_to_markdown,  # noqa: F401
        )
    except ImportError:
        # For actual execution, we need to call MCP tools directly
        print("ℹ️  Note: This test needs to be run via Claude Code with MCP tools")
        print()
        print("Manual test using MCP tools:")
        print("1. Convert document")
        print("2. Export to markdown")
        print("3. Extract with ReflexMedicalExtractor")
        print()

        # Simulate with mock data for demonstration
        print("Running with mock document key for demonstration...")
        doc_key = "590057c4a2f5b8b0f2ca9ec72c379340"  # Known test document

        # Mock markdown from earlier analysis
        markdown = """REFLEX MEDICAL CORP
2480 7th Ave E North St Paul, MN 55109

## Invoice

| Date       |   Invoice # |
|------------|-------------|
| 10/22/2024 |       62935 |

| Bill To                                  | Ship To                                                |
|------------------------------------------|--------------------------------------------------------|
| VoChill 4600 Lasso Path Austin, TX 78745 | VoChill 7601 S. Congress Ave Ste #420 Austin, TX 78745 |

|                     | P.O. No.     | Terms   | Due Date   |
|---------------------|--------------|---------|------------|
|                     | RF45533      | Net 60  | 12/21/2024 |
| Item                | Description  | Qty     | Rate       | Amount    |
| 21-054-07 21-055-07 | Stemless Base Assembly - Cyan Blue Stemless Cup Assembly - Cyan Blue | 224 268 | 1.59 1.59 | 356.16 426.12 |
|                     | Total        |         |            | $782.28   |
|                     | Balance Due  |         |            | $782.28   |
"""

        # Create mock processor
        class MockProcessor:
            def convert_document(self, path):
                return doc_key

            def get_document_markdown(self, key, max_size=3000):
                return markdown

            def search_text(self, key, term):
                return ""

        # Initialize extractor with mock processor
        processor = MockProcessor()
        extractor = ReflexMedicalExtractor(processor)

        # Extract invoice data
        print("🔍 Extracting invoice data...")
        invoice = extractor.extract(doc_key, markdown, Path(pdf_path).name)

        # Display results
        print()
        print("=" * 70)
        print("EXTRACTION RESULTS")
        print("=" * 70)
        print()

        print(f"Vendor: {invoice.vendor.value}")
        print(f"Invoice Number: {invoice.invoice_number}")
        print(f"Invoice Date: {invoice.invoice_date}")
        print(f"PO Number: {invoice.po_number or 'N/A'}")
        print(f"Total: ${invoice.total}")
        print(f"Subtotal: ${invoice.subtotal or 'N/A'}")
        print(f"Sales Tax: ${invoice.sales_tax or '0.00'}")
        print(f"Extraction Confidence: {invoice.extraction_confidence:.2%}")
        print()

        print(f"Line Items ({len(invoice.line_items)}):")
        print("-" * 70)
        for i, item in enumerate(invoice.line_items, 1):
            print(f"{i}. {item.item_code or 'N/A'} - {item.description}")
            print(
                f"   Qty: {item.quantity or 'N/A'}, "
                f"Price: ${item.price_each or 'N/A'}, "
                f"Amount: ${item.amount}"
            )

        print()
        print("=" * 70)
        print("JSON OUTPUT")
        print("=" * 70)
        print()
        print(invoice.model_dump_json(indent=2))

        print()
        print("✅ Test completed successfully!")

        if invoice.extraction_errors:
            print()
            print("⚠️  Extraction warnings:")
            for error in invoice.extraction_errors:
                print(f"  - {error}")

    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_reflex_medical_extraction()
