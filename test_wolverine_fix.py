#!/usr/bin/env python3
"""Test script to verify Wolverine extractor fixes."""

import json
from pathlib import Path

from processors.document_processor import DocumentProcessor
from extractors.wolverine_printing import WolverinePrintingExtractor
from utils.logging_config import setup_logging

# Setup logging
setup_logging(log_level="INFO")

# Initialize
processor = DocumentProcessor()
extractor = WolverinePrintingExtractor(processor)

# Test files
wolverine_dir = Path("/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Wolverine")
test_files = list(wolverine_dir.glob("*.pdf"))

print(f"\nTesting {len(test_files)} Wolverine invoices:\n")
print("=" * 80)

results = []
for pdf_path in sorted(test_files):
    print(f"\nProcessing: {pdf_path.name}")
    print("-" * 80)

    try:
        # Convert document
        doc_key = processor.convert_document(str(pdf_path))
        markdown = processor.get_document_markdown(doc_key)

        # Extract invoice
        invoice = extractor.extract(doc_key, markdown, pdf_path.name)

        # Display key results
        print(f"Invoice Number: {invoice.invoice_number}")
        print(f"Invoice Date: {invoice.invoice_date}")
        print(f"PO Number: {invoice.po_number}")
        print(f"Total: ${invoice.total}")
        print(f"Subtotal: ${invoice.subtotal}")
        print(f"Sales Tax: ${invoice.sales_tax}")
        print(f"Line Items: {len(invoice.line_items)}")
        print(f"Confidence: {invoice.extraction_confidence:.2f}")

        if invoice.extraction_errors:
            print(f"⚠️  Errors: {', '.join(invoice.extraction_errors)}")
        else:
            print("✅ No errors")

        # Show line items
        if invoice.line_items:
            print("\nLine Items:")
            for i, item in enumerate(invoice.line_items, 1):
                print(f"  {i}. {item.description[:60]}... - ${item.amount}")

        results.append({
            "filename": pdf_path.name,
            "success": not bool(invoice.extraction_errors),
            "invoice_number": invoice.invoice_number,
            "total": str(invoice.total) if invoice.total else None,
            "line_items": len(invoice.line_items),
            "confidence": float(invoice.extraction_confidence),
            "errors": invoice.extraction_errors
        })

    except Exception as e:
        print(f"❌ Failed: {e}")
        results.append({
            "filename": pdf_path.name,
            "success": False,
            "error": str(e)
        })

# Summary
print("\n" + "=" * 80)
print("\nSUMMARY:")
print("=" * 80)
successful = sum(1 for r in results if r.get("success", False))
print(f"✅ Successful: {successful}/{len(results)}")
print(f"❌ Failed: {len(results) - successful}/{len(results)}")

print("\nDetailed Results:")
for r in results:
    status = "✅" if r.get("success", False) else "❌"
    print(f"{status} {r['filename']}: ", end="")
    if r.get("success"):
        print(f"#{r['invoice_number']} - ${r['total']} ({r['line_items']} items)")
    else:
        print(f"{r.get('errors', r.get('error', 'Unknown error'))}")
