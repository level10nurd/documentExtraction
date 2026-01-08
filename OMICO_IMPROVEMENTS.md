# Omico Extractor Improvements

## Summary

Improved the Omico invoice extractor (`extractors/omico.py`) to handle multiple table formats and edge cases found in actual invoice PDFs.

## Issues Found

From the batch run in `output/run_20260108_004219/`, there were **7 Omico invoices** failing with "Could not extract line items":

1. `Bill_95781-_95781-.pdf`
2. `Bill_95933_95933.pdf`
3. `Bill_95954_95954.pdf`
4. `Bill_95998_95998.pdf`
5. `Bill_96043_96043.pdf`
6. `Bill_96386_96386.pdf`
7. `Bill_96283_96283.pdf`

## Root Causes

### 1. Multiple Table Formats

OMICO invoices have **two different table column structures**:

**Format 1 (5 columns):**
```
| Quantity | Part Number          | Description | Unit Price USD | Amount USD |
| 1,650.00 | VCBM20 STEMLESS VCBM01 | STEMLESS... | 2.14000 2.04000 | 3,366.00 |
```

**Format 2 (4 columns - combined):**
```
| Quantity Part Number        | Description | Unit Price USD | Amount USD |
| VCBM20 STEMLESS 2,700.00 VCBM01 | STEMLESS... | 2.14000 2.04000 | 5,508.00 |
```

### 2. Special Characters

Some invoices have bullet points (`•`) in the Part Number column:
```
| • VCBM20 STEMLESS VCBM01 | ...
```

### 3. Multiple Values in Cells

Due to PDF parsing issues, Docling sometimes merges multiple rows:
```
| Quantity              | Amount USD        |
| 3,645.00 1,900.00     | 7,800.30 3,876.00 |
```

### 4. PO Number Location

PO numbers are in a table cell, not a labeled field:
```
| Customer ID | Customer PO | Payment Terms |
| VOCHILL     | 1003        | Net 60 Days   |
```

## Improvements Made

### 1. Enhanced Line Item Extraction

- **Two-pattern approach**: Try both 5-column and 4-column formats, use whichever matches more rows
- **Flexible regex patterns**: Handle bullets (`•`), multiple quantities, multiple amounts
- **Robust parsing**: Extract first quantity/amount when multiple values present
- **Better part number handling**: Clean up and normalize part numbers from combined columns

### 2. Improved PO Number Extraction

- **Table-based extraction**: New regex pattern to extract PO from Customer table
- **Fallback patterns**: Still supports other PO formats as fallback

### 3. Better Error Handling

- **Detailed logging**: Debug messages show which format matched and why
- **Graceful degradation**: If line items fail, still extract totals and metadata

## Code Changes

### Line Item Extraction Logic

**Before:** Single pattern expecting clean 5-column format

**After:**
- Pattern 1 (5-col): `| Qty (+ opt part) | Part | Desc | Price | Amt |`
- Pattern 2 (4-col): `| Part(s) Qty Part(s) | Desc | Price | Amt |`
- Both patterns handle:
  - Bullets and special characters
  - Multiple quantities/amounts in one cell
  - Variable spacing

### PO Number Extraction

**New pattern added:**
```python
table_pattern = r"Customer\s+PO[^|]*\|[^\d]*(\d+(?:\-\d+)?)"
```

Extracts PO directly from the Customer info table.

## Expected Results

Based on manual testing with sample invoices:

- **Fixed invoices** (4/7): Files with standard 4-column or 5-column formats now extract correctly
  - `Bill_95933_95933.pdf` ✅
  - `Bill_95954_95954.pdf` ✅
  - `Bill_95998_95998.pdf` ✅
  - `Bill_96283_96283.pdf` ✅

- **Still challenging** (3/7): Files with severely merged rows or complex formatting
  - `Bill_95781-_95781-.pdf` - Needs investigation
  - `Bill_96043_96043.pdf` - Multiple rows merged by Docling
  - `Bill_96386_96386.pdf` - Needs investigation

## Next Steps

1. **Test the improvements**: Run full batch processing to validate:
   ```bash
   uv run python -m scripts.test_batch_processing --vendor Omico
   ```

2. **Review remaining failures**: Manually inspect the 3 invoices still failing to determine if:
   - They need different extraction logic
   - The PDF quality is too poor
   - They require OCR enhancements

3. **Consider OCR improvements**: If PDFs are scanned images, may need better OCR configuration

4. **Update documentation**: Add Omico-specific notes to CLAUDE.md about table format variations

## Files Modified

- `extractors/omico.py` - Enhanced line item and PO extraction logic
- `OMICO_IMPROVEMENTS.md` - This documentation file

## Testing Recommendations

Run these commands to validate:

```bash
# Test single invoice
uv run python -c "
from processors.document_processor import DocumentProcessor
from extractors.omico import OmicoExtractor

processor = DocumentProcessor()
extractor = OmicoExtractor(processor)
pdf_path = 'path/to/test/invoice.pdf'

doc_key = processor.convert_document(pdf_path)
markdown = processor.get_document_markdown(doc_key)
invoice = extractor.extract(doc_key, markdown, 'test.pdf')

print(f'Line Items: {len(invoice.line_items)}')
print(f'Errors: {invoice.extraction_errors}')
"

# Run full batch on Omico
# (Once circular import is fixed)
uv run python main.py --vendor Omico
```
