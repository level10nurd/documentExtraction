"""Test Reflex Medical extraction on multiple invoices."""

from processors.document_processor import DocumentProcessor
from extractors.reflex_medical import ReflexMedicalExtractor
from pathlib import Path

# Initialize
processor = DocumentProcessor()
extractor = ReflexMedicalExtractor(processor)

# Test with multiple sample invoices
test_files = [
    "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Reflex/Bill_62964_Inv_62964_from_REFLEX_MEDICAL_CORP_1281866_137.pdf",
    "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Reflex/Bill_63162_Inv_63162_from_REFLEX_MEDICAL_CORP_40892.pdf",
    "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Reflex/Bill_62713_Inv_62713_from_REFLEX_MEDICAL_CORP_1273073_560.pdf",
]

for pdf_path in test_files:
    print(f"\n{'='*80}")
    print(f"Testing: {Path(pdf_path).name}")
    print('='*80)

    try:
        # Convert and extract
        doc_key = processor.convert_document(pdf_path)
        markdown = processor.get_document_markdown(doc_key, max_size=None)
        invoice = extractor.extract(doc_key, markdown, Path(pdf_path).name)

        # Show results
        print(f"Invoice Number: {invoice.invoice_number}")
        print(f"Invoice Date: {invoice.invoice_date}")
        print(f"PO Number: {invoice.po_number}")
        print(f"Total: ${invoice.total}")
        print(f"Confidence: {invoice.extraction_confidence:.2%}")

        print(f"\nLine Items ({len(invoice.line_items)} found):")
        for idx, item in enumerate(invoice.line_items, 1):
            print(f"  {idx}. {item.item_code}: qty={item.quantity}, price=${item.price_each}, amount=${item.amount}")

        # Check for missing data
        missing_qty = sum(1 for item in invoice.line_items if item.quantity is None)
        missing_price = sum(1 for item in invoice.line_items if item.price_each is None)

        if missing_qty > 0:
            print(f"\n⚠️  WARNING: {missing_qty} items missing quantity")
        if missing_price > 0:
            print(f"⚠️  WARNING: {missing_price} items missing price")

    except Exception as e:
        print(f"❌ ERROR: {e}")
