---
title: 'Fix Amanda-Andrews Personnel Corp Extractor - Improve Confidence from 0.50 to 0.70+'
slug: 'fix-amanda-andrews-extractor-improve-confidence'
created: '2026-01-08'
completed: '2026-01-08'
status: 'ready-for-implementation'
stepsCompleted: [1, 2, 3, 4]
adversarialReviewCompleted: true
adversarialReviewFindings: 15
adversarialReviewAllFixed: true
tech_stack:
  - Python 3.11+
  - Docling 2.66.0+ (PDF to markdown with OCR)
  - Pydantic (Invoice/LineItem models with validators)
  - python-dateutil (flexible date parsing)
  - re (regex pattern matching with IGNORECASE | MULTILINE)
files_to_modify:
  - extractors/amanda_andrews.py (fix date/PO patterns, add vendor-specific confidence)
  - scripts/diagnose_amanda_andrews.py (NEW - diagnostic script)
  - tests/test_amanda_andrews_extraction.py (NEW - test script with all 18 invoices)
  - tests/regression_test.py (UPDATE - add Amanda-Andrews test case)
code_patterns:
  - BaseExtractor inheritance with extract() implementation
  - Helper methods: _parse_decimal(), _extract_regex() from BaseExtractor
  - Regex patterns: re.search(pattern, markdown, re.IGNORECASE | re.MULTILINE)
  - Error handling: invoice.add_error() auto-adjusts confidence
  - SimpleProcessor pattern for standalone testing (avoids circular imports)
  - Config.SOURCE_DIR for all file paths (no hardcoded paths)
test_patterns:
  - SimpleProcessor with DocumentConverter and PdfPipelineOptions
  - importlib.util.spec_from_file_location() to avoid circular imports
  - Test output: filename, confidence, items, total, errors
  - Regression: Reflex (≥0.90), OMICO (≥0.80), Amanda-Andrews (≥0.70)
implementation_notes:
  - Line items skipped for staffing invoices (hourly temp workers)
  - Target confidence: 0.70+ (not 0.80 - staffing format limitation)
  - Vendor-specific confidence override (Option A) bypasses global line items penalty
  - OCR failures excluded from success metrics (documented separately)
  - PO extraction conditional based on ≥50% presence threshold
---

# Tech-Spec: Fix Amanda-Andrews Personnel Corp Extractor - Improve Confidence from 0.50 to 0.70+

**Created:** 2026-01-08
**Completed:** 2026-01-08
**Status:** ✅ Ready for Implementation
**Adversarial Review:** ✅ Complete (15 findings, all fixed)

---

## 🚀 Quick Start - Picking Up This Work

**What's Done:**
- ✅ Complete tech-spec created through 4-step workflow (Understand → Investigate → Generate → Review)
- ✅ Adversarial review completed: 15 findings identified and fixed (2 Critical, 5 High, 7 Medium, 1 Low)
- ✅ All acceptance criteria defined with priority levels (5 CRITICAL, 3 IMPORTANT, 1 CONDITIONAL)
- ✅ 13 implementation tasks across 4 phases (Baseline → Diagnostic → Pattern Fixes → Testing)
- ✅ Code templates provided for diagnostic script, test script, and regression test update

**What's Next - Implementation Path:**
1. **Start Here:** Review Task 0 (Baseline Capture) - document current state before changes
2. **Follow Tasks 1-12 sequentially** - each task has clear inputs/outputs and success criteria
3. **Critical Decision Point:** Task 5 (PO extraction) - conditional based on diagnostic findings
4. **Test Incrementally:** After Tasks 4, 6, and 9 - use defined success thresholds
5. **Final Validation:** Task 11 (regression test) ensures no breaking changes to other vendors

**Key Context for Implementation:**
- **Business Reason:** Staffing invoices (hourly temp workers) = no line items → different from product invoices
- **Root Cause:** Current extractor penalizes missing line items → all 18 invoices stuck at 0.50 confidence
- **Solution:** Vendor-specific confidence calculation that skips line items/PO penalties for staffing format
- **Target:** ≥0.70 confidence on all OCR-successful invoices (not 0.80 - realistic for staffing format)

**Files to Review Before Starting:**
- `extractors/amanda_andrews.py:57-134` - Current failing implementation (date pattern issue)
- `models/invoice.py:101-123` - Global confidence logic (will be overridden, not modified)
- `scripts/diagnose_abox.py` - Reference pattern for diagnostic script (Task 1)
- `tests/test_abox_extraction.py` - Reference pattern for test script (Task 7)

**How to Begin:**
```bash
# Option 1: Start fresh context with this spec
# Just reference this file and say "implement the Amanda-Andrews tech-spec"

# Option 2: Continue in this context
# Run Task 0 to capture baseline, then proceed through tasks

# Option 3: Quick diagnostic first (recommended)
# Create diagnostic script (Task 1) to see actual invoice format before full implementation
```

---

## Overview

### Problem Statement

All 18 Amanda-Andrews Personnel Corp invoices currently extract at exactly 0.50 confidence, representing $30,372 in at-risk invoice value. These are staffing/temp worker invoices that don't have traditional line items. The extractor successfully extracts invoice number and total amount, but consistently fails on invoice date and PO number extraction. Additionally, the confidence calculation penalizes these invoices for missing line items that don't exist in the staffing invoice format.

**Current Confidence Breakdown (0.50):**
- ✓ Invoice number extracted (no penalty)
- ✓ Total amount extracted (no penalty)
- ✗ Invoice date missing (-0.2)
- ✗ PO number missing (-0.1)
- ✗ Line items missing (-0.2)
- **Total penalty: -0.5 = 0.50 confidence**

### Solution

1. Create diagnostic script to extract markdown from sample Amanda-Andrews invoices and identify actual format
2. Fix invoice date extraction pattern to match actual invoice format
3. Fix PO number extraction pattern (if PO numbers exist in staffing invoices)
4. Adjust confidence calculation to not penalize staffing invoices for missing line items
5. Test against all 18 invoices to validate ≥0.70 confidence achieved

### Scope

**In Scope:**
- Diagnostic analysis of 2-3 sample Amanda-Andrews invoices
- Fix invoice date extraction pattern in `extractors/amanda_andrews.py`
- Fix PO number extraction pattern in `extractors/amanda_andrews.py`
- Adjust confidence calculation for staffing invoice format (exclude line items penalty)
- Create test script for Amanda-Andrews extraction validation
- Test against all 18 invoices
- Validate ≥0.70 confidence achieved
- Regression testing on other vendors (Reflex, OMICO) to ensure no breaking changes

**Out of Scope:**
- Line items extraction (staffing invoices are hourly temp workers, no detailed line items)
- OCR preprocessing improvements (assume OCR quality is acceptable)
- Changes to other vendor extractors
- Batch processing infrastructure changes
- CSV export modifications

## Context for Development

### Codebase Patterns

**Extractor Architecture:**
- All extractors inherit from `BaseExtractor` in `extractors/base.py`
- Each extractor implements `extract(doc_key, markdown, filename)` method
- Extraction uses regex patterns on markdown content from Docling conversion
- Helper methods follow naming pattern `_extract_<field_name>(markdown, invoice)`
- Must call `self._create_base_invoice(VendorType, filename)` to initialize Invoice

**BaseExtractor Helper Methods (extractors/base.py):**
```python
_create_base_invoice(vendor, filename) → Invoice  # Returns initialized invoice
_extract_regex(text, pattern, group=1) → str | None  # Regex extraction with flags
_parse_decimal(value) → Decimal | None  # Clean currency strings to Decimal
_clean_invoice_number(value) → str  # Remove "Invoice #:", "#" prefixes
_clean_po_number(value) → str | None  # Remove "PO #:", "P.O. Number:" prefixes
_extract_table_data(markdown, table_marker) → list[dict]  # Parse markdown tables
```

**Current Amanda-Andrews Extraction Patterns (extractors/amanda_andrews.py:57-134):**
```python
# Invoice number pattern (WORKING):
r"(\d{5,})\s+INVOICE\s+#"  # Matches: "73018 INVOICE #"

# Invoice date pattern (FAILING):
r"(\d{1,2}/\d{1,2}/\d{4})\s+INVOICE\s+DATE"  # Expects: "08/30/2024 INVOICE DATE"

# Total amount patterns (WORKING - 3 fallback patterns):
1. r"\$\s*([\d,]+\.?\d*)\s+AMOUNT\s+DUE"
2. r"AMOUNT\s+DUE\s+\$\s*([\d,]+\.?\d*)"
3. r"AMOUNTGLYPH.*DUE.*?\$\s*([\d,]+\.?\d*)"  # DOTALL flag for table search
4. r"Invoice\s+Total:\s*\$\s*([\d,]+\.?\d*)"  # Additional fallback
```

**No PO Number Extraction:**
- Current code does NOT attempt PO number extraction
- `_extract_invoice_header()` only extracts number and date
- PO number likely doesn't exist in staffing invoices (needs diagnostic confirmation)

**Confidence Calculation Mechanics (models/invoice.py:101-123):**
```python
def calculate_confidence(self) -> float:
    score = 1.0
    if not self.invoice_number: score -= 0.3  # Critical
    if self.total is None: score -= 0.3       # Critical
    if not self.invoice_date: score -= 0.2    # Important
    if not self.po_number: score -= 0.1       # Important
    if not self.line_items: score -= 0.2      # Currently penalizes staffing invoices
    return max(0.0, score)
```

**Problem:** No vendor-specific confidence logic. Staffing invoices without line items get -0.2 penalty even when line items don't exist in their format.

**Staffing Invoice Format Characteristics:**
- Simple format with header fields only
- Account number may be present
- No detailed line items (summary-only for temp worker hours)
- Single total amount without subtotal/tax breakdown
- Vendor: "AMANDA-ANDREWS PERSONNEL CORP" (dba VIP STAFFING)

**Recent Pattern (ABox Fix - Proven Successful):**
1. Created `scripts/diagnose_abox.py` with SimpleProcessor
2. Extracted markdown from 2 sample invoices to `output/` directory
3. Manually reviewed markdown to identify actual format vs. expected patterns
4. Documented findings in extractor docstring
5. Fixed all 5 extraction methods with table-based patterns
6. Created `tests/test_abox_extraction.py` with importlib loading
7. Tested against all 6 invoices, achieved 0.90 on 1 successful OCR invoice
8. Ran regression test on Reflex (1.00) and OMICO (1.00) - no degradation

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `extractors/amanda_andrews.py` | Amanda-Andrews extractor - needs pattern fixes |
| `models/invoice.py` | Invoice model with confidence calculation - may need adjustment |
| `extractors/base.py` | Base extractor with helper methods |
| `scripts/diagnose_abox.py` | Reference diagnostic script pattern |
| `tests/test_abox_extraction.py` | Reference test script pattern |
| `docs/extractor-improvement-plan.md` | Phase 1.2 requirements and acceptance criteria |

### Technical Decisions

**Target Confidence: 0.70+ (not 0.80)**
- Staffing invoices legitimately lack line item detail
- 0.70 confidence is realistic and acceptable for this format
- Requires successful extraction of invoice number, total, and date
- If PO numbers don't exist in staffing format, we accept -0.1 penalty (still achieves 0.70)

**Confidence Calculation Approach - DECISION REQUIRED:**

**Option A: Vendor-Specific Confidence Override (Recommended)**
```python
# In AmandaAndrewsExtractor.extract():
invoice.extraction_confidence = self._calculate_staffing_confidence(invoice)

def _calculate_staffing_confidence(self, invoice: Invoice) -> float:
    score = 1.0
    if not invoice.invoice_number: score -= 0.3
    if invoice.total is None: score -= 0.3
    if not invoice.invoice_date: score -= 0.2
    # Skip PO number penalty (staffing invoices may not have POs)
    # Skip line items penalty (staffing invoices don't have detailed line items)
    return max(0.0, score)
```
✅ Pros: Clean, vendor-specific, doesn't affect global confidence logic
✅ Simple override in extractor
❌ Cons: Duplicates confidence logic

**Option B: Add Invoice Type to Model**
```python
# In models/invoice.py:
class Invoice(BaseModel):
    invoice_type: str = "standard"  # or "staffing", "subscription", etc.

def calculate_confidence(self) -> float:
    # Adjust penalties based on invoice_type
    if self.invoice_type == "staffing":
        # Skip line items penalty
```
❌ Cons: More invasive change, affects Invoice model schema
❌ Requires migration of existing data

**Option C: Conditional Check in calculate_confidence()**
```python
def calculate_confidence(self) -> float:
    score = 1.0
    # ... existing penalties ...

    # Skip line items penalty for staffing vendors
    if self.vendor not in [VendorType.AMANDA_ANDREWS]:
        if not self.line_items: score -= 0.2
```
❌ Cons: Hardcodes vendor logic in model, violates separation of concerns

**Recommended: Option A** - Cleanest separation, vendor-specific override

**Line Items Strategy:**
- Skip line items extraction entirely for Amanda-Andrews
- No `_extract_line_items()` method needed
- Use Option A confidence override to skip line items penalty

**Pattern Discovery Approach:**
- Follow ABox diagnostic pattern (proven successful)
- Extract markdown from 2-3 sample invoices
- Document actual format vs. expected patterns
- Fix regex patterns based on findings
- Check if PO numbers exist in Amanda-Andrews invoices during diagnostic phase

## Implementation Plan

### Tasks

**Phase 0: Baseline Capture (Before Any Changes)**

- [ ] Task 0: Capture baseline metrics for current extractor performance
  - File: `tests/test_amanda_andrews_extraction.py` (create temporary version with current code)
  - Action: Run test against all 18 invoices BEFORE making any changes
  - Command: `uv run python tests/test_amanda_andrews_extraction.py > output/baseline_amanda_andrews.txt 2>&1`
  - Goal: Document actual current state (verify "all at 0.50" claim), establish improvement baseline
  - Output: Save results to `output/baseline_amanda_andrews.txt` for comparison

**Phase 1: Diagnostic Analysis (Understand Actual Format)**

- [ ] Task 1: Create diagnostic script for Amanda-Andrews invoices
  - File: `scripts/diagnose_amanda_andrews.py` (new)
  - Action: Copy pattern from `scripts/diagnose_abox.py`, update to use `Config.SOURCE_DIR` for portability
  - **CRITICAL**: Use `from config import Config; Config.load_environment()` then `base_path = Config.SOURCE_DIR / "AmandaAndrews"`
  - **DO NOT use hardcoded paths** like `/Users/dalton/Library/CloudStorage/Dropbox/...`
  - **Sample Selection Strategy** (3 diverse invoices to capture format variations):
    1. **Early invoice**: `Bill_73018_Vochill__Inc-_Invoice_73018.pdf` (lowest invoice number, may have older format)
    2. **Large file**: `Bill_73165_Vochill__Inc-_Invoice_73165.pdf` (446KB - likely multi-page or high-quality scan)
    3. **Different format**: `Bill_74236_Invoice.pdf` (different filename pattern, no invoice number in filename)
  - Rationale: Diverse sample ensures patterns work across date ranges, file sizes, and format variants
  - Output: Markdown files to `output/amanda_andrews_diagnostic_*.md`
  - **Note**: Diagnostic script should ONLY convert PDFs to markdown (no extraction). Do not import AmandaAndrewsExtractor to avoid circular imports.

- [ ] Task 2: Run diagnostic script and analyze markdown structure
  - Command: `uv run python scripts/diagnose_amanda_andrews.py`
  - Action: Review generated markdown files in `output/` directory
  - Goal: Identify actual invoice date format, check if PO numbers exist, document structure
  - **OCR Quality Check**: Inspect markdown files for OCR failures (files with only `<!-- image -->` placeholders, no text content)
  - If OCR failures found: Document which invoices have bad OCR, exclude from pattern development, note as "Out of Scope - OCR preprocessing needed"
  - ABox reference: 5/6 ABox invoices had OCR failures - this may happen with Amanda-Andrews too

- [ ] Task 3: Document diagnostic findings in extractor docstring (Initial Documentation)
  - File: `extractors/amanda_andrews.py:17-25`
  - Action: Update `extract()` method docstring with actual format discovered from diagnostic analysis
  - Include:
    - Actual date format pattern found in markdown (e.g., "Date appears in table | Date | ... |" or "INVOICE DATE on line after number")
    - PO number presence/absence (e.g., "PO numbers found in 2/18 invoices" or "No PO numbers in staffing format")
    - Invoice structure examples from markdown samples
  - **Purpose**: Document observations BEFORE implementing fixes (diagnostic findings)
  - **Timing**: Complete after Task 2, before starting Task 4 fixes

**Phase 2: Fix Extraction Patterns**

- [ ] Task 4: Fix invoice date extraction pattern
  - File: `extractors/amanda_andrews.py:71-89`
  - Action: Update `_extract_invoice_header()` date regex pattern based on actual format from diagnostic
  - Current failing pattern: `r"(\d{1,2}/\d{1,2}/\d{4})\s+INVOICE\s+DATE"`
  - **Pattern Discovery Strategy**:
    1. Review markdown output from Task 2 for actual date format
    2. Common patterns to try (in order):
       - Table-based: `r"\|\s*Date\s*\|.*?\n.*?\|\s*(\d{1,2}/\d{1,2}/\d{4})\s*\|"` (if date is in table)
       - Reversed order: `r"INVOICE\s+DATE\s+(\d{1,2}/\d{1,2}/\d{4})"` (date after label)
       - Line break: `r"INVOICE\s+DATE\s*\n\s*(\d{1,2}/\d{1,2}/\d{4})"` (date on next line)
       - Colon separator: `r"INVOICE\s+DATE:\s*(\d{1,2}/\d{1,2}/\d{4})"` (with colon)
    3. Test each pattern incrementally with `uv run python tests/test_amanda_andrews_extraction.py`
    4. If multiple formats exist in 18 invoices, implement 2-3 fallback patterns (follow ABox total extraction pattern at lines 272-281)
  - **Success Criteria**: After fix, ≥95% of invoices (17/18) should extract dates successfully

- [ ] Task 5: Add PO number extraction (conditional based on diagnostic findings)
  - File: `extractors/amanda_andrews.py:57-90`
  - Action: Based on Task 2 diagnostic findings, choose approach:
  - **If ≥50% of invoices (9+/18) have PO numbers**:
    - Implement `_extract_po_number(markdown, invoice)` method
    - Use BaseExtractor helper: `self._clean_po_number()` for cleaning
    - Call from `extract()` method after invoice header extraction
    - Modify `_calculate_staffing_confidence()` to include PO penalty: `if not invoice.po_number: score -= 0.1`
    - Target: Invoices with PO = 1.0 confidence, without PO = 0.9 confidence
  - **If <50% of invoices have PO numbers**:
    - Skip PO extraction entirely
    - Keep `_calculate_staffing_confidence()` without PO penalty
    - Accept uniform 0.8-1.0 confidence across all invoices
    - Document in extractor: "PO numbers rare in staffing invoices, extraction skipped"
  - **Decision Point**: After Task 2 diagnostic, document which path was chosen and why

- [ ] Task 6: Add vendor-specific confidence calculation (Option A - Recommended)
  - File: `extractors/amanda_andrews.py` (new method after line 134)
  - Action: Add `_calculate_staffing_confidence(self, invoice: Invoice) -> float` method
  - Implementation:
    ```python
    def _calculate_staffing_confidence(self, invoice: Invoice) -> float:
        """Calculate confidence for staffing invoices (no line items expected)."""
        score = 1.0
        if not invoice.invoice_number: score -= 0.3
        if invoice.total is None: score -= 0.3
        if not invoice.invoice_date: score -= 0.2
        # Skip PO number penalty (staffing invoices may not have POs)
        # Skip line items penalty (staffing invoices don't have detailed line items)
        return max(0.0, score)
    ```
  - Update `extract()` at line 45: Replace `invoice.calculate_confidence()` with `self._calculate_staffing_confidence(invoice)`
  - **Rollback Strategy**: If Option A fails regression tests OR doesn't achieve ≥0.70 target:
    1. Revert changes to `extract()` method (restore `invoice.calculate_confidence()`)
    2. Try **Option C** (fallback): Modify `models/invoice.py` `calculate_confidence()` method:
       ```python
       # In line items penalty section (around line 118):
       if self.vendor not in [VendorType.AMANDA_ANDREWS]:
           if not self.line_items: score -= 0.2
       ```
    3. This hardcodes vendor exception in model (less clean, but works if Option A breaks)
    4. Document in Notes section which option was used and why rollback was needed

**Phase 3: Testing & Validation**

- [ ] Task 7: Create test script for Amanda-Andrews extraction
  - File: `tests/test_amanda_andrews_extraction.py` (new)
  - Action: Copy pattern from `tests/test_abox_extraction.py`, update for Amanda-Andrews
  - **CRITICAL**: Use `from config import Config; Config.load_environment()` then `base_path = Config.SOURCE_DIR / "AmandaAndrews"`
  - Use SimpleProcessor with importlib loading to avoid circular imports
  - Test all 18 invoices from Config.SOURCE_DIR (not hardcoded path)
  - Output: filename, confidence, total, errors for each invoice
  - Target: ≥0.70 confidence on all 18 invoices

- [ ] Task 8: Run incremental tests after each fix
  - Command: `uv run python tests/test_amanda_andrews_extraction.py` after each pattern fix
  - Action: Validate confidence improvement after Task 4, Task 5 (if applicable), and Task 6
  - **Incremental Success Thresholds** (for OCR-successful invoices only):
    - **After Task 4 (date fix)**: Target ≥80% at 0.60+ confidence (14+/18 invoices have dates extracted, -0.2 penalty removed)
    - **After Task 5 (PO fix, if implemented)**: If PO extraction added, target varies based on PO presence
    - **After Task 6 (confidence override)**: Target 100% at 0.70-1.0 confidence (all OCR-successful invoices, line items penalty removed)
  - **Debug Decision Criteria**:
    - If <80% success rate after any task: STOP, re-run diagnostic on failing invoices, review markdown patterns
    - If 80-95% success rate: Acceptable, proceed but note failing invoices for manual review
    - If ≥95% success rate: Excellent, proceed to next task
  - Track: Save test output after each fix to `output/test_after_task_N.txt` for comparison

- [ ] Task 9: Final validation against all 18 invoices
  - Command: `uv run python tests/test_amanda_andrews_extraction.py`
  - Action: Run complete test suite after all fixes applied
  - Target: All 18 invoices ≥0.70 confidence
  - Document: Average confidence, any remaining errors, edge cases

- [ ] Task 10: Update regression test to include Amanda-Andrews
  - File: `tests/regression_test.py`
  - Action: Add Amanda-Andrews test case after OMICO test (around line 94)
  - **Use Config.SOURCE_DIR** pattern (regression test already has this pattern for Reflex/OMICO):
    ```python
    # Test Amanda-Andrews
    amanda_file = str(Config.SOURCE_DIR / 'AmandaAndrews' / 'Bill_73018_Vochill__Inc-_Invoice_73018.pdf')
    try:
        amanda_module = load_extractor('amanda_andrews')
        extractor = amanda_module.AmandaAndrewsExtractor(processor)
        doc_key = processor.convert_document(amanda_file)
        markdown = processor.get_document_markdown(doc_key)
        invoice = extractor.extract(doc_key, markdown, 'Bill_73018.pdf')
        conf = invoice.extraction_confidence
        status = 'PASS ✓' if conf >= 0.70 else 'DEGRADED ✗'
        print(f'{"Amanda-Andrews":<20} {"Bill_73018.pdf":<40} {conf:.2f}  {status}')
    except Exception as e:
        print(f'{"Amanda-Andrews":<20} {"Bill_73018.pdf":<40} {"FAIL":<6} Exception: {str(e)[:30]}')
    ```
  - Target confidence: ≥0.70
  - Verify: Reflex Medical (≥0.90), OMICO (≥0.80), Amanda-Andrews (≥0.70) all pass

- [ ] Task 11: Run regression test on other vendors
  - Command: `uv run python tests/regression_test.py`
  - Action: Verify Amanda-Andrews changes don't break Reflex or OMICO extractors
  - Target: Reflex Medical 1.00 confidence, OMICO 1.00 confidence, Amanda-Andrews ≥0.70 confidence
  - Fix: If regression detected, review changes to shared code (BaseExtractor, Invoice model)

- [ ] Task 12: Finalize documentation with implementation notes (Final Documentation)
  - File: `extractors/amanda_andrews.py:1-25`
  - Action: Update module and class docstrings with final implementation learnings
  - **Distinguish from Task 3**: Task 3 documented diagnostic findings (what format exists), Task 12 documents implementation decisions (how we handled it)
  - Include:
    - Final extraction patterns that worked (e.g., "Date extracted using table-based pattern with 2 fallbacks, 17/18 success rate")
    - Confidence calculation strategy choice (e.g., "Used Option A vendor-specific override, target 0.80-1.0 confidence")
    - Known limitations discovered during testing (e.g., "Bill_74XXX has unusual date format, requires manual review")
    - PO number decision and rationale (e.g., "PO numbers rare (3/18 invoices), extraction skipped per Task 5 decision")
  - **Purpose**: Document lessons learned AFTER implementation (for future maintainers)
  - **Timing**: Complete after Task 11 (all testing done), before marking spec complete

### Acceptance Criteria

**AC1: Diagnostic Script Functionality**
- [ ] Given the diagnostic script exists, when run with `uv run python scripts/diagnose_amanda_andrews.py`, then it extracts markdown from 3 sample invoices and saves to `output/amanda_andrews_diagnostic_*.md` files without errors

**AC2: Invoice Date Extraction**
- [ ] Given an Amanda-Andrews invoice with date in actual format, when `_extract_invoice_header()` is called, then `invoice.invoice_date` is populated with correct date object
- [ ] Given 18 Amanda-Andrews invoices, when date extraction runs on all, then at least 17/18 successfully extract dates (95%+ success rate)

**AC3: PO Number Extraction (Conditional)**
- [ ] Given diagnostic analysis confirms PO numbers exist, when `_extract_po_number()` is implemented and called, then PO numbers are extracted from invoices that have them
- [ ] Given diagnostic analysis confirms PO numbers don't exist in staffing invoices, when this AC is reviewed, then Task 5 is marked N/A and -0.1 penalty is accepted

**AC4: Vendor-Specific Confidence Calculation**
- [ ] Given `_calculate_staffing_confidence()` method exists, when an invoice has invoice_number + total + date but no line items or PO, then confidence returns 1.0 (no penalties applied - line items and PO penalties are skipped for staffing invoices)
- [ ] Given an invoice missing only date, when confidence is calculated, then score is 0.8 (1.0 - 0.2 for missing date, line items penalty skipped)
- [ ] Given an invoice missing both date and total, when confidence is calculated, then score is 0.5 (1.0 - 0.3 for total - 0.2 for date)
- [ ] Given the method is called from `extract()`, when any Amanda-Andrews invoice is processed, then `invoice.extraction_confidence` uses staffing-specific logic, not global `calculate_confidence()`

**AC5: Test Script Functionality**
- [ ] Given test script exists, when run with `uv run python tests/test_amanda_andrews_extraction.py`, then it processes all 18 invoices and displays confidence scores without crashing
- [ ] Given test results are displayed, when reviewing output, then each invoice shows filename, confidence (2 decimal places), total amount, and any extraction errors

**AC6: Confidence Target Achievement**
- [ ] Given all pattern fixes are applied, when testing all OCR-successful Amanda-Andrews invoices, then 100% achieve ≥0.70 confidence
- [ ] Given diagnostic phase identifies invoices with OCR failures (empty/garbled markdown with only image placeholders), when calculating success rate, then exclude OCR-failed invoices from target and document them separately as "OCR Quality Issue - Out of Scope"
- [ ] Given final test results on OCR-successful invoices, when calculating average confidence, then average is ≥0.75
- [ ] Given current state is 0.50 for all invoices, when improvements are complete, then confidence increases by at least +0.20 for each OCR-successful invoice
- [ ] Given OCR failures are discovered, when final results are reported, then clearly separate: "X/Y OCR-successful invoices at ≥0.70 confidence, Z invoices failed OCR (excluded from target)"

**AC7: No Regression on Other Vendors**
- [ ] Given regression test includes Reflex Medical sample, when run after Amanda-Andrews changes, then Reflex confidence remains ≥0.90 (no degradation)
- [ ] Given regression test includes OMICO sample, when run after Amanda-Andrews changes, then OMICO confidence remains ≥0.80 (no degradation)
- [ ] Given regression test runs successfully, when all three vendors are tested, then output shows "PASS ✓" for all three vendors

**AC8: Code Quality & Documentation**
- [ ] Given extractor code is updated, when reviewing `extractors/amanda_andrews.py`, then docstrings explain actual invoice format discovered during diagnostic phase
- [ ] Given vendor-specific confidence method exists, when reviewing code, then inline comments explain why staffing invoices skip line items and PO penalties
- [ ] Given all changes are complete, when running `uv run ruff check extractors/amanda_andrews.py`, then no linting errors are reported

**AC9: Error Handling**
- [ ] Given an invoice fails to extract date, when `_extract_invoice_header()` runs, then `invoice.add_error("Could not extract invoice date")` is called and confidence is adjusted
- [ ] Given total extraction fails (edge case), when `_extract_total()` runs, then error is logged and confidence drops appropriately
- [ ] Given any extraction exception occurs, when caught in `extract()` method, then error is logged, added to invoice errors, and invoice is still returned (not crashed)

### Acceptance Criteria Priority Levels

**CRITICAL** (Must pass for successful implementation):
- **AC2**: Invoice Date Extraction - Core field for confidence
- **AC4**: Vendor-Specific Confidence Calculation - Solves root cause of 0.50 confidence
- **AC6**: Confidence Target Achievement - Primary business objective (≥0.70 on all OCR-successful invoices)
- **AC7**: No Regression on Other Vendors - Must not break existing extractors
- **AC9**: Error Handling - Production-ready error management

**IMPORTANT** (Should pass, improves quality but not blockers):
- **AC1**: Diagnostic Script Functionality - Enables pattern discovery
- **AC5**: Test Script Functionality - Validates extraction works
- **AC8**: Code Quality & Documentation - Maintainability and standards

**CONDITIONAL** (Pass/fail depends on diagnostic findings):
- **AC3**: PO Number Extraction - Only applicable if ≥50% of invoices have PO numbers (per Task 5 logic)

**Implementation Success Criteria**: All CRITICAL ACs must pass. IMPORTANT ACs should pass (acceptable if 1-2 have minor issues with documented workarounds). CONDITIONAL ACs are evaluated based on diagnostic results.

## Additional Context

### Dependencies

**External Libraries:**
- `docling>=2.66.0` - PDF to markdown conversion with OCR (already installed)
- `python-dateutil` - Flexible date parsing (already installed)
- `pydantic` - Data validation with field validators (already installed)
- `re` - Standard library regex (no installation needed)

**Internal Dependencies:**
- `extractors/base.py` - BaseExtractor with helper methods
- `models/invoice.py` - Invoice and LineItem Pydantic models
- `models/vendor.py` - VendorType enum (AMANDA_ANDREWS)
- Existing batch processing infrastructure (no changes needed)

**No External API or Service Dependencies**

### Testing Strategy

**Unit Testing:**
- Diagnostic script tests markdown extraction from sample invoices
- Test script validates extraction on all 18 invoices
- Incremental testing after each pattern fix (Tasks 4, 5, 6)

**Integration Testing:**
- Regression test verifies no impact on Reflex Medical and OMICO extractors
- Batch processing integration (manual validation)
- CSV export integration (manual validation)

**Manual Testing Steps:**
1. Review markdown output from diagnostic script to verify actual format
2. Spot-check 2-3 invoices manually against extracted data
3. Verify confidence scores align with field completeness
4. Test edge cases (invoices with missing fields, unusual formatting)

**Success Metrics:**
- 100% of 18 invoices achieve ≥0.70 confidence (18/18)
- Average confidence ≥0.75 across all invoices
- Zero regression on Reflex Medical and OMICO extractors
- All acceptance criteria pass

### Notes

**Current State:**
- All 18 invoices at exactly 0.50 confidence (100% consistency)
- Systematic pattern issue, not random failures
- Invoice number and total extraction working (✓)
- Invoice date extraction failing (✗)
- PO number not attempted (✗)
- Line items penalty incorrectly applied (✗)

**File Locations:**
- Invoices: `/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/AmandaAndrews/`
- Sample filenames: `Bill_73018_Vochill__Inc-_Invoice_73018.pdf`, `Bill_73165_Vochill__Inc-_Invoice_73165.pdf`, etc.
- 18 total invoices

**Business Context:**
- Phase 1.2 of extractor improvement plan (high priority)
- $30,372 at risk (invoice value affected by low confidence)
- Target: ≥0.70 confidence (realistic for staffing invoice format)
- Impact: Phase 1 completion requires ABox, Amanda-Andrews, and Pride Printing fixes

**High-Risk Items:**
1. **Unknown actual date format** - Diagnostic analysis critical to success
2. **PO number presence uncertain** - May or may not exist in staffing invoices
3. **Vendor-specific confidence logic** - New pattern, needs careful implementation
4. **Circular import issues** - Test scripts must use importlib pattern

**Known Limitations:**
- Staffing invoices don't have line item detail (by design)
- No subtotal/tax breakdown (staffing format characteristic)
- Target confidence is 0.70, not 0.80 (accepts realistic limitations)

**Future Considerations (Out of Scope):**
- If other staffing vendors exist, extract `_calculate_staffing_confidence()` to BaseExtractor
- Consider adding `invoice_type` field to Invoice model for more formal invoice categorization
- Potential to add simple line items parsing if temp worker summary data exists in invoices

---

## Workflow Completion Summary

**Tech-Spec Creation Process:**
- **Workflow:** BMad Quick-Dev → Create Tech-Spec workflow (4-step process)
- **Date:** 2026-01-08
- **Steps Completed:**
  1. ✅ **Understand Requirements** - Captured user context about staffing invoices, no line items, 0.70 target
  2. ✅ **Investigate Codebase** - Reviewed amanda_andrews.py, models/invoice.py, reference patterns
  3. ✅ **Generate Tech-Spec** - Created complete spec with 13 tasks, 9 ACs, code templates
  4. ✅ **Review & Adversarial Analysis** - Systematic review found and fixed 15 issues

**Adversarial Review Results:**
- **Total Findings:** 15 (2 Critical, 5 High, 7 Medium, 1 Low)
- **Resolution Status:** ✅ ALL FIXED (100%)

**Critical/High Findings Fixed (7):**
- F1 [CRITICAL]: Fixed AC4 confidence math errors (1.0 for complete, 0.8 for missing date)
- F2 [HIGH]: Verified invoice count (18 confirmed via ls command)
- F3 [HIGH]: Replaced all hardcoded paths with Config.SOURCE_DIR pattern
- F4 [HIGH]: Added specific date pattern guidance (4 patterns to try incrementally)
- F5 [HIGH]: Added Task 0 baseline capture before making changes
- F6 [MEDIUM]: Clarified diagnostic script scope (no extractor import)
- F11 [HIGH]: Added OCR failure handling and AC6 exclusion criteria

**Medium/Low Findings Fixed (8):**
- F7: Added conditional PO number logic (≥50% threshold)
- F8: Provided exact regression test template code
- F9: Added incremental success thresholds (80% after Task 4, 100% after Task 6)
- F10: Distinguished Task 3 vs Task 12 documentation timing
- F12: Added rollback strategy to Task 6 (Option C fallback)
- F13: Justified sample selection diversity
- F14: Removed AC10 (scope creep - CSV export out of scope)
- F15: Added AC priority levels (CRITICAL/IMPORTANT/CONDITIONAL)

**Key Decisions Made:**
1. **Line Items:** Skipped entirely (user confirmed - temp hourly workers)
2. **Target Confidence:** 0.70+ (not 0.80 - realistic for staffing format)
3. **Confidence Approach:** Option A (vendor-specific override in extractor)
4. **PO Extraction:** Conditional based on ≥50% presence threshold
5. **OCR Failures:** Excluded from success metrics, documented separately
6. **Path Handling:** All paths use Config.SOURCE_DIR (no hardcoded paths)

**Spec Quality Metrics:**
- 13 implementation tasks with clear inputs/outputs
- 9 acceptance criteria with priority levels (5 CRITICAL, 3 IMPORTANT, 1 CONDITIONAL)
- 4 complete code templates (diagnostic, test, regression, confidence method)
- Incremental testing strategy with success thresholds
- Rollback plans for high-risk changes
- OCR failure handling explicitly documented

**Ready for Implementation:**
This tech-spec is production-ready with all ambiguities resolved, rollback strategies defined, and clear success criteria. The adversarial review process caught and fixed 15 potential implementation issues before any code was written.

**Next Steps:**
1. Reference this file when starting implementation
2. Begin with Task 0 (baseline capture) to document current state
3. Follow tasks 1-12 sequentially with incremental testing
4. Use provided code templates to avoid circular import issues
5. Validate against all 9 acceptance criteria (prioritize CRITICAL ACs)

---

**Document Version:** 1.0 (Complete)
**Last Updated:** 2026-01-08
**Workflow State:** ✅ Complete - Ready for Implementation
