---
title: 'Fix ABox Extractor - Improve Confidence from 0.20 to 0.80+'
slug: 'fix-abox-extractor-improve-confidence'
created: '2026-01-08'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.11+', 'docling (DocumentConverter, PdfPipelineOptions)', 'pydantic (BaseModel, validators)', 're (regex)', 'dateutil.parser', 'decimal.Decimal']
files_to_modify: ['extractors/abox.py']
files_to_create: ['scripts/diagnose_abox.py', 'tests/test_abox_extraction.py']
code_patterns: ['BaseExtractor ABC pattern', 'Pydantic models with field validators', 'Regex extraction with re.IGNORECASE | re.MULTILINE', 'Error tracking via invoice.add_error()', 'Confidence calculation via invoice.calculate_confidence()']
test_patterns: ['Standalone test scripts with SimpleProcessor', 'Direct module import to avoid circular dependencies', 'Test against specific invoice files', 'Print summary: File | Status | Items | Total | Errors']
---

# Tech-Spec: Fix ABox Extractor - Improve Confidence from 0.20 to 0.80+

**Created:** 2026-01-08

## Overview

### Problem Statement

The ABox extractor is failing on all 6 invoices with a catastrophic 0.20 confidence score, resulting in $55,763.31 of invoice value at risk (highest financial impact in Phase 1). The root cause is currently unknown and could be:
- Pattern mismatch between expected format and actual OCR markdown output
- Poor OCR quality from scanned images
- Combination of both issues

Current state: 100% failure rate across all ABox invoices makes this the highest priority fix in the improvement plan.

### Solution

Implement a three-phase diagnostic and fix approach:

1. **Phase 1 - Diagnostic Investigation:** Extract and analyze markdown from 2-3 sample ABox invoices to identify root cause (pattern mismatch vs OCR quality issues)
2. **Phase 2 - Pattern Implementation:** Fix regex patterns and table parsing logic in `extractors/abox.py` based on diagnostic findings
3. **Phase 3 - Testing & Validation:** Test fixes against all 6 ABox invoices and validate ≥0.80 confidence target is achieved

### Scope

**In Scope:**
- Markdown extraction and structural analysis from sample ABox invoices
- Root cause identification (pattern mismatch vs OCR quality)
- Regex pattern fixes in `extractors/abox.py`
- Table parsing logic adjustments for actual markdown structure
- Fallback patterns for common OCR variations (e.g., "O" vs "0", spacing issues)
- Field extraction method updates as needed
- Testing and validation against all 6 ABox invoices
- Documentation of findings, fixes, and any remaining edge cases

**Out of Scope:**
- OCR preprocessing or enhancement at document conversion level (defer to separate task if OCR is fundamentally broken)
- Document quality improvements in `processors/document_processor.py`
- Batch processor changes
- Other vendor extractors (separate phases: Amanda-Andrews, Pride Printing)
- CSV export or reporting changes
- Confidence calculation algorithm changes (use existing from BaseExtractor)

## Context for Development

### Codebase Architecture

**Extraction Pipeline:**
```
PDF → DocumentProcessor (Docling) → Markdown → VendorExtractor → Invoice (Pydantic)
```

**Key Components:**
- `processors/document_processor.py` - Handles Docling conversion, caches documents
- `extractors/base.py` - BaseExtractor with helper methods for pattern matching
- `extractors/abox.py` - ABox-specific extraction logic (TARGET FILE)
- `models/invoice.py` - Invoice and LineItem Pydantic models with validation
- `models/vendor.py` - VendorType enum and confidence calculation

**BaseExtractor Helper Methods Available:**
- `_extract_regex(text, pattern, group=1)` - Extract text using regex with IGNORECASE | MULTILINE flags
- `_parse_decimal(value)` - Parse string to Decimal, handles currency symbols and commas
- `_extract_table_data(markdown, table_marker)` - Extract table data from markdown
- `_clean_invoice_number(value)` - Remove common prefixes from invoice numbers
- `_clean_po_number(value)` - Remove common prefixes from PO numbers
- `list_vendor_invoices(pattern)` - List all invoice files for vendor

**Invoice Confidence Calculation (from models/invoice.py):**
- Base score: 1.0
- Missing invoice_number: -0.3
- Missing total: -0.3
- Missing invoice_date: -0.2
- Missing po_number: -0.1
- Missing line_items: -0.2
- **Current ABox score (0.20) suggests 4 major fields failing (invoice_number, total, invoice_date, line_items)**

**Existing ABox Extractor Structure:**
The extractor is already fully implemented with methods for:
- `_extract_invoice_number()` - Pattern: "Invoice No: 100676"
- `_extract_invoice_date()` - Pattern: "Invoice Date: 10/23/24"
- `_extract_po_number()` - Pattern: "Customer P.O. No. 1027"
- `_extract_line_items()` - Complex table parsing with 8-column structure
- `_extract_total()` - Pattern: "This Amount => $8,284.32"

**Current Pattern Assumptions (from code comments):**
- Scanned images with OCR text
- Table format: Qty Ord. | Order # | Description | Customer P.O. No. | Qty Shipped | P/C | Price/Per | Amount
- Prices are "per M" (per thousand units)
- Multiple variations in spacing and column merging expected

**Reference Patterns from High-Performing Extractors:**

*REFLEX MEDICAL (91% avg confidence):*
- Uses `re.search(r"\|\s*(\d{1,2}/\d{1,2}/\d{4})\s*\|\s*(\d+)\s*\|", markdown)` for table extraction
- Extracts date and invoice number from same table row
- Flexible whitespace handling with `\s*` and `\s+`

*YES Solutions (99% avg confidence):*
- Pattern: `r"\|\s*INVOICE\s*#\s*\|\s*(\d+)\s*\|"` with re.IGNORECASE
- Clear table structure matching
- Separate methods for each field extraction with error handling

**Sample ABox Invoice Files (All 6 Available):**
```
/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/ABox/
- Bill_100654_doc02531620241018085046.pdf
- Bill_100676_doc02542020241023083923.pdf
- Bill_201038_201038_VOCHILL.pdf
- Bill_202052_doc03384120251007105152.pdf
- Bill_202192_doc03439820251022094839.pdf
- Bill_202377_doc03542420251120111021.pdf
```

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `extractors/abox.py` | **PRIMARY TARGET** - Contains all ABox extraction logic to be fixed |
| `extractors/base.py` | Parent class with helper methods (_extract_regex, _parse_decimal, etc.) |
| `extractors/reflex_medical.py` | **REFERENCE** - High-performing extractor (91% confidence) with table parsing patterns |
| `extractors/yes_solutions.py` | **REFERENCE** - Excellent extractor (99% confidence) with clean field extraction |
| `models/invoice.py` | Invoice and LineItem Pydantic models, calculate_confidence() method |
| `processors/document_processor.py` | Document conversion and markdown extraction (read-only) |
| `tests/test_omico_extraction.py` | **REFERENCE** - Test pattern template with SimpleProcessor |
| `docs/vendor-extraction-issues.md` | Analysis showing 0.20 confidence across all 6 ABox invoices |
| `docs/extractor-improvement-plan.md` | Phase 1.1 detailed implementation plan and diagnostic steps |

**Files to Create:**
| File | Purpose |
| ---- | ------- |
| `scripts/diagnose_abox.py` | Diagnostic script to extract and analyze markdown from sample ABox invoices |
| `tests/test_abox_extraction.py` | Test script for validating ABox extraction improvements |

### Technical Decisions

**Investigation Approach:**
- Create `scripts/diagnose_abox.py` using SimpleProcessor pattern from test_omico_extraction.py
- Extract markdown from 2-3 sample ABox invoices (prioritize Bill_100676 and Bill_201038)
- Save markdown output to files for manual inspection
- Document actual structure vs expected patterns (table format, field labels, spacing)
- Identify root cause: pattern mismatch, OCR quality, or both

**Pattern Fix Strategy:**
- Follow REFLEX MEDICAL and YES Solutions patterns for successful extraction
- Use flexible whitespace: `\s*` (0+ spaces) and `\s+` (1+ spaces) instead of exact spacing
- Use `re.IGNORECASE | re.MULTILINE` flags consistently
- Add fallback patterns for each field (multiple regex attempts)
- Consider using BaseExtractor._extract_regex() helper for cleaner code
- Handle common OCR errors: "O" vs "0", "l" vs "1", extra spaces, missing pipe separators
- For line items: Start with flexible pattern, then add specificity based on diagnostic findings

**Testing Strategy:**
- Create `tests/test_abox_extraction.py` following test_omico_extraction.py pattern
- Test incrementally: fix one method at a time (_extract_invoice_number first, then _extract_invoice_date, etc.)
- Run diagnostic script after each method fix to validate improvement
- Final validation: Run test against all 6 ABox invoices
- Success criteria: ≥0.80 confidence (means at least 4/5 core fields extracted: invoice_number, total, invoice_date, line_items, po_number)
- Regression check: Quick smoke test on 1 Reflex and 1 OMICO invoice to ensure no breakage

**Code Organization:**
- Keep existing method structure in abox.py (_extract_invoice_number, _extract_invoice_date, etc.)
- Add inline comments documenting pattern assumptions and OCR quirks discovered
- Update docstring in extract() method with findings about actual ABox format
- Use try/except blocks with invoice.add_error() for graceful degradation

## Implementation Plan

### Tasks

**Phase 1: Diagnostic Investigation**

- [ ] Task 1: Create diagnostic script
  - File: `scripts/diagnose_abox.py`
  - Action: Create new script using SimpleProcessor pattern from `tests/test_omico_extraction.py`
  - Details:
    - Import DocumentConverter, PdfPipelineOptions from docling
    - Create SimpleProcessor class with convert_document() and get_document_markdown() methods
    - Target sample invoices: Bill_100676_doc02542020241023083923.pdf and Bill_201038_201038_VOCHILL.pdf
    - Save markdown output to `output/abox_diagnostic_*.md` files for inspection
    - Print summary: Invoice file, markdown length, first 500 chars preview

- [ ] Task 2: Run diagnostic script and analyze markdown structure
  - File: `scripts/diagnose_abox.py`
  - Action: Execute script via `uv run python scripts/diagnose_abox.py`
  - Details:
    - Manually inspect saved markdown files in `output/` directory
    - Document actual field labels vs expected (e.g., "Invoice No" vs "Invoice Number")
    - Document actual table structure (number of columns, pipe separators, spacing)
    - Identify OCR quality issues (character substitutions, missing text, spacing problems)
    - Document findings in inline comments for Task 3

- [ ] Task 3: Document root cause analysis
  - File: `extractors/abox.py` (docstring only)
  - Action: Update extract() method docstring with diagnostic findings
  - Details:
    - Add section "Actual Invoice Format (from diagnostic analysis):"
    - Document field labels as they actually appear in markdown
    - Document table structure differences from original assumptions
    - Note any OCR quirks discovered (e.g., "Invoice No." vs "Invoice No:")

**Phase 2: Pattern Implementation**

- [ ] Task 4: Fix invoice number extraction
  - File: `extractors/abox.py`
  - Action: Update `_extract_invoice_number()` method with flexible patterns
  - Details:
    - Replace rigid pattern with flexible whitespace: `r"Invoice\s+No[.:]?\s*(\d+)"`
    - Add fallback pattern for variations: `r"Invoice\s+Number[.:]?\s*(\d+)"`
    - Use BaseExtractor._extract_regex() if cleaner than direct re.search()
    - Add inline comment explaining pattern flexibility
    - Keep existing error handling with invoice.add_error()

- [ ] Task 5: Fix invoice date extraction
  - File: `extractors/abox.py`
  - Action: Update `_extract_invoice_date()` method with flexible patterns
  - Details:
    - Update pattern to handle flexible spacing: `r"Invoice\s+Date[.:]?\s*(\d{1,2}/\d{1,2}/\d{2,4})"`
    - Add fallback for alternate format: `r"Date[.:]?\s*(\d{1,2}/\d{1,2}/\d{2,4})"` (if "Invoice" prefix missing)
    - Consider table-based extraction if dates appear in tables: `r"\|\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*\|"`
    - Keep existing dateutil.parser.parse() for date parsing
    - Maintain error handling

- [ ] Task 6: Fix PO number extraction
  - File: `extractors/abox.py`
  - Action: Update `_extract_po_number()` method with flexible patterns
  - Details:
    - Update pattern: `r"Customer\s+P\.?O\.?\s+No\.?\s*[:\|]?\s*(\d+)"`
    - Add fallback: `r"P\.?O\.?\s+(?:No\.?|Number)[.:]?\s*(\d+)"`
    - Handle table extraction: look for PO in line item table first
    - Use BaseExtractor._clean_po_number() helper
    - PO is optional (only -0.1 confidence penalty)

- [ ] Task 7: Fix line items extraction
  - File: `extractors/abox.py`
  - Action: Update `_extract_line_items()` method based on actual table structure
  - Details:
    - Review diagnostic markdown for actual table column order and spacing
    - Update table_pattern regex with flexible whitespace (`\s*` between pipes)
    - Make columns optional if OCR sometimes drops them: use `(?: ... )?` for optional groups
    - Handle "EA" or "ea" case-insensitively: `(?:EA|ea|Ea|eA)`
    - Keep price per M (thousand) calculation: `Decimal(price_str) / Decimal("1000")`
    - Maintain LineItem creation with quantity, item_code, description, price_each, amount
    - Keep error handling for parse failures (ValueError, IndexError)

- [ ] Task 8: Fix total extraction
  - File: `extractors/abox.py`
  - Action: Update `_extract_total()` method with flexible patterns
  - Details:
    - Update patterns list with flexible spacing: `r"This\s+Amount\s*=>?\s*\$?([\d,]+\.\d{2})"`
    - Add fallback patterns: `r"Please\s+Pay.*?\$?([\d,]+\.\d{2})"`, `r"Total.*?\$?([\d,]+\.\d{2})"`
    - Keep fallback to sum line items if no total found
    - Use BaseExtractor._parse_decimal() or existing logic
    - Maintain error handling

**Phase 3: Testing & Validation**

- [ ] Task 9: Create test script
  - File: `tests/test_abox_extraction.py`
  - Action: Create new test script following `tests/test_omico_extraction.py` pattern
  - Details:
    - Import ABoxExtractor using importlib to avoid circular imports
    - Create SimpleProcessor class (same as diagnostic script)
    - Test all 6 ABox invoices from Bills/ABox/ directory
    - Print table: File | Status | Confidence | Items | Total | Errors
    - Count success rate (≥0.80 confidence)

- [ ] Task 10: Run incremental tests after each fix
  - File: `tests/test_abox_extraction.py`
  - Action: Execute test after Tasks 4, 5, 6, 7, 8 to validate improvements
  - Details:
    - Run: `uv run python tests/test_abox_extraction.py`
    - Verify confidence improves incrementally (0.20 → 0.50 → 0.70 → 0.80+)
    - If stuck, re-run diagnostic script on failing invoice
    - Iterate on patterns based on test results

- [ ] Task 11: Final validation against all 6 invoices
  - File: `tests/test_abox_extraction.py`
  - Action: Run complete test suite and validate ≥0.80 confidence on all invoices
  - Details:
    - Target: All 6 invoices achieve ≥0.80 confidence
    - Acceptable: 5/6 at ≥0.80, 1/6 at ≥0.70 (if OCR truly broken on one invoice)
    - Document any remaining issues in extractors/abox.py docstring
    - Calculate average confidence (target: 0.85+)

- [ ] Task 12: Regression testing on other vendors
  - File: N/A (run existing tests)
  - Action: Quick smoke test on Reflex Medical and OMICO invoices
  - Details:
    - Test 1 Reflex invoice: Should still achieve ≥0.90 confidence
    - Test 1 OMICO invoice: Should still achieve ≥0.80 confidence
    - Ensures ABox changes didn't break BaseExtractor or shared patterns
    - If regression found, review changes in extractors/abox.py for unintended side effects

- [ ] Task 13: Update documentation
  - File: `extractors/abox.py`
  - Action: Final docstring and inline comment cleanup
  - Details:
    - Ensure extract() docstring accurately describes ABox invoice format
    - Add comments explaining any non-obvious regex patterns
    - Document known limitations or edge cases
    - Note any OCR issues that couldn't be fully resolved

### Acceptance Criteria

**Diagnostic Phase:**

- [ ] AC1: Given diagnostic script is created, when executed on 2 sample ABox invoices, then markdown output files are saved to `output/` directory and structure differences are documented
- [ ] AC2: Given markdown files are inspected, when comparing with extractor patterns, then root cause is identified (pattern mismatch, OCR quality, or both) and documented in findings

**Pattern Implementation:**

- [ ] AC3: Given invoice number pattern is updated, when test script runs on ABox invoices, then invoice_number field is extracted successfully (not empty string)
- [ ] AC4: Given invoice date pattern is updated, when test script runs, then invoice_date field is extracted and parsed to valid date object
- [ ] AC5: Given PO number pattern is updated, when test script runs, then po_number field is extracted (or gracefully handled if missing)
- [ ] AC6: Given line items pattern is updated, when test script runs, then at least 1 line item is extracted with quantity, description, and amount fields populated
- [ ] AC7: Given total pattern is updated, when test script runs, then total field is extracted and matches Decimal value (not zero)

**Validation:**

- [ ] AC8: Given all pattern fixes are implemented, when running test on all 6 ABox invoices, then at least 5 invoices achieve ≥0.80 confidence score
- [ ] AC9: Given test results show confidence scores, when calculating average, then average confidence is ≥0.85 across all ABox invoices
- [ ] AC10: Given ABox fixes are complete, when running regression test on 1 Reflex and 1 OMICO invoice, then both maintain original high confidence scores (no degradation)

**Error Handling:**

- [ ] AC11: Given an ABox invoice fails to extract a field, when extraction completes, then invoice.extraction_errors contains descriptive error message and confidence score reflects the failure appropriately
- [ ] AC12: Given an ABox invoice has poor OCR quality, when extraction completes, then no Python exceptions are raised and invoice object is returned with partial data and documented errors

**Documentation:**

- [ ] AC13: Given extraction fixes are complete, when reviewing extractors/abox.py, then docstrings accurately describe actual ABox invoice format and any known limitations are documented

## Additional Context

### Dependencies

- Python 3.11+
- docling (≥2.66.0) - Document processing
- pydantic - Data validation
- python-dateutil - Date parsing
- re (stdlib) - Regex pattern matching

**No new dependencies required** - all fixes can be done with existing stack.

### Testing Strategy

**Sample Selection:**
- Extract all 6 ABox invoice paths from `Bills/ABox/` directory
- Prioritize 2-3 invoices for initial diagnostic analysis
- Use full set (6 invoices) for final validation

**Validation Metrics:**
- Confidence score ≥0.80 for each invoice
- Key fields extracted: vendor, invoice_number, invoice_date, total
- Line items extracted with quantity, description, amount
- No Python exceptions during extraction

**Regression Prevention:**
- Ensure fixes don't break other vendor extractors
- Run quick smoke test on 1-2 invoices from other vendors (e.g., Reflex, OMICO)

### Notes

**Financial Impact:**
- $55,763.31 at risk (59% of total low-confidence invoice value)
- Fixing ABox alone moves system confidence from 84.6% → ~90%

**Pattern Complexity:**
- ABox has most complex table parsing logic among all extractors
- 8-column table with pricing "per M" (thousands) requiring unit conversion
- OCR from scanned images adds variability

**Success Metrics from Improvement Plan:**
- Before: 0.20 confidence (100% failure)
- Target: 0.85+ confidence (≥80% success)
- Impact: Resolves highest-priority critical issue
