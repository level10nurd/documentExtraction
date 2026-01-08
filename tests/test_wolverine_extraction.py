"""Test script for Wolverine Printing extractor."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from extractors.wolverine_printing import WolverinePrintingExtractor


def test_wolverine_extraction():
    """Test Wolverine Printing extraction with real MCP tools."""
    # Import MCP tools
    try:
        from mcp__plugin_supabase_toolkit_supabase__execute_sql import (
            mcp__docling__convert_document_into_docling_document,
            mcp__docling__export_docling_document_to_markdown,
        )
    except ImportError:
        print(
            "ERROR: MCP tools not available. This test must be run within Claude Code environment."
        )
        return

    # Mock processor that uses real MCP tools
    class MCPProcessor:
        def convert_document(self, pdf_path: str) -> str:
            result = mcp__docling__convert_document_into_docling_document(
                source=pdf_path
            )
            return result["document_key"]

        def get_document_markdown(self, doc_key: str, max_size=None) -> str:
            kwargs = {"document_key": doc_key}
            if max_size:
                kwargs["max_size"] = max_size
            result = mcp__docling__export_docling_document_to_markdown(**kwargs)
            return result["markdown"]

    # Initialize
    processor = MCPProcessor()
    extractor = WolverinePrintingExtractor(processor)

    # Test invoices
    test_files = [
        "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Bill_110458_110458.pdf",
        "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Bill_110640_110640.pdf",
    ]

    for pdf_path in test_files:
        try:
            print(f"\n{'=' * 60}")
            print(f"Processing: {Path(pdf_path).name}")
            print(f"{'=' * 60}")

            # Convert and extract
            doc_key = processor.convert_document(pdf_path)
            markdown = processor.get_document_markdown(doc_key)
            invoice = extractor.extract(doc_key, markdown, Path(pdf_path).name)

            # Display results
            print(f"\nVendor: {invoice.vendor}")
            print(f"Invoice Number: {invoice.invoice_number}")
            print(f"Invoice Date: {invoice.invoice_date}")
            print(f"PO Number: {invoice.po_number}")
            print(f"Total: ${invoice.total}")
            print(f"Subtotal: ${invoice.subtotal}")
            print(f"Sales Tax: ${invoice.sales_tax}")
            print(f"\nLine Items ({len(invoice.line_items)}):")
            for i, item in enumerate(invoice.line_items, 1):
                print(f"  {i}. {item.description[:60]}")
                print(
                    f"     Qty: {item.quantity}, Price: ${item.price_each}, Amount: ${item.amount}"
                )

            print(f"\nExtraction Confidence: {invoice.extraction_confidence:.1%}")
            if invoice.extraction_errors:
                print(f"Errors: {invoice.extraction_errors}")

        except Exception as e:
            print(f"ERROR processing {Path(pdf_path).name}: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_wolverine_extraction()
