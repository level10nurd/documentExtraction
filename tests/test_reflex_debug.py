"""Debug script to test Reflex Medical extraction."""

from processors.document_processor import DocumentProcessor
from extractors.reflex_medical import ReflexMedicalExtractor

# Initialize
processor = DocumentProcessor()
extractor = ReflexMedicalExtractor(processor)

# Test with a sample invoice
pdf_path = "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Reflex/Bill_62964_Inv_62964_from_REFLEX_MEDICAL_CORP_1281866_137.pdf"

# Convert document
print("Converting document...")
doc_key = processor.convert_document(pdf_path)

# Get markdown
markdown = processor.get_document_markdown(doc_key, max_size=None)

# Show the table section
print("\n=== RAW MARKDOWN (Line Items Section) ===")
lines = markdown.split("\n")
for i, line in enumerate(lines):
    if "Item" in line and "Description" in line and "Qty" in line:
        # Print header and next 10 lines
        for j in range(i, min(i + 10, len(lines))):
            print(f"Line {j}: {lines[j]}")
        break

# Extract invoice
print("\n\n=== EXTRACTING INVOICE ===")
invoice = extractor.extract(doc_key, markdown, "test.pdf")

# Show results
print(f"\nInvoice Number: {invoice.invoice_number}")
print(f"Invoice Date: {invoice.invoice_date}")
print(f"PO Number: {invoice.po_number}")
print(f"Total: ${invoice.total}")
print(f"\nLine Items ({len(invoice.line_items)} found):")
for idx, item in enumerate(invoice.line_items, 1):
    print(f"  {idx}. {item.item_code}: qty={item.quantity}, price=${item.price_each}, amount=${item.amount}")
    print(f"     Description: {item.description[:60]}...")
