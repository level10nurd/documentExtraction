"""Live test script using real MCP tools."""

import sys
from pathlib import Path


def test_live_extraction():
    """Test extraction with real MCP tools and REFLEX MEDICAL invoice."""
    print("=" * 70)
    print("LIVE INVOICE EXTRACTION TEST")
    print("=" * 70)
    print()

    # Sample invoice path
    pdf_path = "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Bill_62935_Inv_62935_from_REFLEX_MEDICAL_CORP_1280567_199.pdf"

    if not Path(pdf_path).exists():
        print("❌ Error: Sample invoice not found")
        sys.exit(1)

    print(f"📄 Processing: {Path(pdf_path).name}")
    print()

    # Import the extractor
    from extractors.reflex_medical import ReflexMedicalExtractor

    # Document key from earlier conversion
    doc_key = "590057c4a2f5b8b0f2ca9ec72c379340"

    # Get the actual markdown from MCP
    print("🔍 Step 1: Exporting document to markdown...")
    from mcp__docling__export_docling_document_to_markdown import (
        mcp__docling__export_docling_document_to_markdown as export_md,
    )

    result = export_md(doc_key, max_size=10000)
    markdown = result.get("markdown", "")

    print(f"   Markdown length: {len(markdown)} characters")
    print()

    # Create a simple processor that uses the doc_key
    class SimpleProcessor:
        def search_text(self, key, term):
            # We'll implement this if needed
            return ""

    # Initialize extractor
    processor = SimpleProcessor()
    extractor = ReflexMedicalExtractor(processor)

    # Extract
    print("🔍 Step 2: Extracting invoice data...")
    invoice = extractor.extract(doc_key, markdown, Path(pdf_path).name)

    # Display results
    print()
    print("=" * 70)
    print("EXTRACTION RESULTS")
    print("=" * 70)
    print()

    print(f"✓ Vendor: {invoice.vendor.value}")
    print(f"✓ Invoice Number: {invoice.invoice_number}")
    print(f"✓ Invoice Date: {invoice.invoice_date}")
    print(f"✓ PO Number: {invoice.po_number or 'Not found'}")
    print(f"✓ Total: ${invoice.total}")
    print(f"✓ Subtotal: ${invoice.subtotal or 'N/A'}")
    print(f"✓ Sales Tax: ${invoice.sales_tax or '0.00'}")
    print(f"✓ Confidence: {invoice.extraction_confidence:.1%}")
    print()

    print(f"Line Items ({len(invoice.line_items)}):")
    print("-" * 70)
    for i, item in enumerate(invoice.line_items, 1):
        print(f"  {i}. [{item.item_code or 'N/A'}] {item.description[:50]}")
        print(
            f"     Qty: {item.quantity}, "
            f"Price: ${item.price_each}, "
            f"Amount: ${item.amount}"
        )
    print()

    # Show full JSON
    print("=" * 70)
    print("FULL JSON OUTPUT")
    print("=" * 70)
    print()
    print(invoice.model_dump_json(indent=2))
    print()

    # Check for errors
    if invoice.extraction_errors:
        print("⚠️  Extraction Issues:")
        for error in invoice.extraction_errors:
            print(f"  • {error}")
        print()

    # Success
    if invoice.extraction_confidence >= 0.8:
        print("✅ Extraction successful with high confidence!")
    else:
        print("⚠️  Extraction completed but with lower confidence")

    return invoice


if __name__ == "__main__":
    try:
        invoice = test_live_extraction()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
