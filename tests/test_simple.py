"""Simple direct test of REFLEX MEDICAL extraction."""

from decimal import Decimal

from extractors.reflex_medical import ReflexMedicalExtractor

# Full markdown from the actual invoice
markdown = """REFLEX MEDICAL CORP

2480 7th Ave E North St Paul, MN 55109

## Invoice

| Date       |   Invoice # |
|------------|-------------|
| 10/22/2024 |       62935 |

| Bill To                                  | Ship To                                                |
|------------------------------------------|--------------------------------------------------------|
| VoChill 4600 Lasso Path Austin, TX 78745 | VoChill 7601 S. Congress Ave Ste #420 Austin, TX 78745 |

|                     | P.O. No.                                                                                 | Terms                                                                                    | Due Date                                                                                 | Due Date         | Ship Date        | Ship Date        | Ship Via         | Ship Via      |
|---------------------|------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|------------------|------------------|------------------|------------------|---------------|
|                     | RF45533                                                                                  | Net 60                                                                                   | 12/21/2024                                                                               | 12/21/2024       | 10/22/2024       | 10/22/2024       | UPS              | UPS           |
| Item                | Description                                                                              | Description                                                                              | Description                                                                              | Qty              | Qty              | Rate             | Rate             | Amount        |
| 21-054-07 21-055-07 | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 224 268          | 224 268          | 1.59 1.59        | 1.59 1.59        | 356.16 426.12 |
|                     |                                                                                          |                                                                                          |                                                                                          | Total            | Total            | Total            | Total            | $782.28       |
|                     |                                                                                          |                                                                                          |                                                                                          | Payments/Credits | Payments/Credits | Payments/Credits | Payments/Credits | $0.00         |
|                     |                                                                                          |                                                                                          |                                                                                          | Balance Due      | Balance Due      | Balance Due      | Balance Due      | $782.28       |

<!-- image -->"""


# Mock processor
class MockProcessor:
    def search_text(self, key, term):
        return ""


# Create extractor
processor = MockProcessor()
extractor = ReflexMedicalExtractor(processor)

# Extract
doc_key = "test_key"
filename = "Bill_62935.pdf"

print("=" * 80)
print("REFLEX MEDICAL INVOICE EXTRACTION TEST")
print("=" * 80)
print()

invoice = extractor.extract(doc_key, markdown, filename)

# Display results
print(f"Vendor:          {invoice.vendor.value}")
print(f"Invoice #:       {invoice.invoice_number}")
print(f"Date:            {invoice.invoice_date}")
print(f"PO#:             {invoice.po_number}")
print(f"Total:           ${invoice.total}")
print(f"Subtotal:        ${invoice.subtotal}")
print(f"Tax:             ${invoice.sales_tax}")
print(f"Confidence:      {invoice.extraction_confidence:.1%}")
print()

print(f"Line Items: {len(invoice.line_items)}")
print("-" * 80)
for i, item in enumerate(invoice.line_items, 1):
    print(f"{i}. Item Code: {item.item_code}")
    print(f"   Description: {item.description}")
    print(f"   Quantity: {item.quantity}")
    print(f"   Price Each: ${item.price_each}")
    print(f"   Amount: ${item.amount}")
    print()

if invoice.extraction_errors:
    print("Errors/Warnings:")
    for error in invoice.extraction_errors:
        print(f"  - {error}")
    print()

# Validation
print("=" * 80)
print("VALIDATION")
print("=" * 80)
expected_invoice_num = "62935"
expected_total = Decimal("782.28")
expected_po = "RF45533"

checks = [
    (
        "Invoice number",
        invoice.invoice_number == expected_invoice_num,
        expected_invoice_num,
        invoice.invoice_number,
    ),
    ("Total amount", invoice.total == expected_total, expected_total, invoice.total),
    ("PO number", invoice.po_number == expected_po, expected_po, invoice.po_number),
    ("Has line items", len(invoice.line_items) > 0, "> 0", len(invoice.line_items)),
    (
        "Date extracted",
        invoice.invoice_date is not None,
        "Not None",
        invoice.invoice_date,
    ),
]

passed = 0
for name, result, expected, actual in checks:
    status = "✅" if result else "❌"
    print(f"{status} {name}: Expected={expected}, Actual={actual}")
    if result:
        passed += 1

print()
print(f"Passed {passed}/{len(checks)} validation checks")
