# Invoice Extractor Improvement Plan

**Project:** Document Extraction System
**Created:** 2026-01-08
**Based on Analysis:** `docs/vendor-extraction-issues.md`
**Total Invoices:** 246 across 10 vendors
**At-Risk Value:** $94,948.76 (9.8% of total)

---

## 🎯 Project Goals

**Primary Objectives:**
- Achieve >90% of invoices at ≥0.8 confidence
- Eliminate all invoices below 0.50 confidence
- Fix all critical vendor failures (ABox, Amanda-Andrews, Pride Printing)
- Establish consistent extraction patterns across all vendors

**Success Metrics:**
- **Before:** 84.6% at ≥0.7 confidence, 38 invoices below 0.7
- **Target:** 95%+ at ≥0.8 confidence, <5 invoices below 0.7
- **Timeline:** 3 phases over 2-3 weeks

---

## 📋 Phase 1: Critical Fixes (Week 1)

**Duration:** 3-5 days
**Focus:** Vendors with catastrophic failures
**Impact:** Fix $86,541.56 in at-risk invoice value (91% of low-confidence total)

### 1.1 ABox Extractor Fix
**Priority:** 🔥 HIGHEST
**Current State:** 0.20 confidence (6 invoices, 100% failure)
**At Risk:** $55,763.31

**Diagnostic Steps:**
1. Pull sample ABox invoice for manual inspection
2. Extract markdown from sample invoice using DocumentProcessor
3. Compare markdown output with expected invoice format
4. Identify OCR quality issues or format mismatches

**Implementation Tasks:**
```
[ ] Review `extractors/abox.py` current implementation
[ ] Extract markdown from 2-3 sample ABox invoices
[ ] Document actual invoice structure vs. expected patterns
[ ] Identify missing regex patterns or field extraction logic
[ ] Check for OCR issues (poor scan quality, image-based PDFs)
[ ] Implement corrected extraction patterns
[ ] Add specific field extraction for ABox format
[ ] Test against all 6 ABox invoices
[ ] Validate confidence scores improve to ≥0.8
[ ] Document ABox-specific quirks in extractor comments
```

**Expected Confidence Improvement:** 0.20 → 0.85+

**Testing Validation:**
- All 6 invoices should achieve ≥0.80 confidence
- Key fields extracted: vendor, invoice_date, invoice_number, total
- Line items extracted with quantity, description, amount
- Subtotal, tax, and total properly parsed

---

### 1.2 Amanda-Andrews Personnel Corp Fix
**Priority:** 🔴 HIGH
**Current State:** 0.50 confidence (18 invoices, 100% at 0.50)
**At Risk:** $30,372.00

**Root Cause Analysis:**
- Staffing/personnel invoices have different structure than product invoices
- May not have traditional line items (summary format instead)
- Likely missing specific fields consistently (causing 50% score)

**Diagnostic Steps:**
1. Pull 2-3 sample Amanda-Andrews invoices
2. Compare format with product-based vendor invoices
3. Identify what fields ARE being extracted vs. MISSING
4. Determine if line items exist or if summary-only format

**Implementation Tasks:**
```
[ ] Review `extractors/amanda_andrews.py` implementation
[ ] Extract markdown from sample invoices
[ ] Map actual invoice structure (staffing vs. product format)
[ ] Identify which fields extract successfully vs. fail
[ ] Adjust extraction patterns for staffing invoice format
[ ] Handle cases where line items may not exist (summary only)
[ ] Update confidence calculation for staffing format
[ ] Add fallback patterns for missing fields
[ ] Test against all 18 invoices
[ ] Validate confidence ≥0.70 (realistic for staffing format)
[ ] Document staffing invoice characteristics
```

**Expected Confidence Improvement:** 0.50 → 0.75+

**Special Considerations:**
- Staffing invoices may legitimately not have line-item detail
- Confidence scoring may need adjustment for summary-only format
- Focus on core fields: date, invoice number, total amount

---

### 1.3 Pride Printing LLC Fix
**Priority:** 🔴 HIGH
**Current State:** 0.30 confidence (2 invoices, stub implementation)
**At Risk:** $406.25

**Root Cause Analysis:**
- Extractor is stub/placeholder, not fully implemented
- Format likely not analyzed during initial development
- Small vendor but critical quality issue

**Diagnostic Steps:**
1. Pull both Pride Printing invoices for manual review
2. Document complete invoice format and structure
3. Identify unique patterns and layout characteristics
4. Map fields to extraction requirements

**Implementation Tasks:**
```
[ ] Review `extractors/pride_printing.py` stub code
[ ] Extract markdown from both Pride Printing invoices
[ ] Document invoice format structure completely
[ ] Identify vendor name patterns in document
[ ] Implement invoice number extraction
[ ] Implement date extraction
[ ] Implement line item parsing
[ ] Implement total, subtotal, tax extraction
[ ] Add Pride Printing specific regex patterns
[ ] Test against both invoices
[ ] Validate confidence ≥0.80
[ ] Add comprehensive docstring with format notes
```

**Expected Confidence Improvement:** 0.30 → 0.85+

**Implementation Priority:**
- Full extractor implementation from scratch
- Learn from well-performing extractors (YES Solutions, OMICO)
- Follow established patterns in `extractors/base.py`

---

## 📋 Phase 2: Medium Priority Fixes (Week 2)

**Duration:** 5-7 days
**Focus:** Inconsistent or format-variation issues
**Impact:** Fix $81,388.01 in invoice value

### 2.1 Dimax Corporation - Handle Format Variations
**Priority:** 🟡 MEDIUM
**Current State:** Mix of 0.20 (3 invoices) and 1.00 (2 invoices)
**At Risk:** $7,382.20

**Root Cause Analysis:**
- 60% failure rate suggests multiple invoice templates
- Some invoices extract perfectly, others completely fail
- Format detection or conditional logic needed

**Diagnostic Steps:**
1. Pull 1 successful (1.00) and 1 failed (0.20) invoice
2. Compare markdown structure between successful and failed
3. Identify format differences (layout, table structure, field positions)
4. Document format variations

**Implementation Tasks:**
```
[ ] Review `extractors/dimax.py` current implementation
[ ] Extract markdown from successful invoice (1.00 confidence)
[ ] Extract markdown from failed invoice (0.20 confidence)
[ ] Compare and contrast format differences
[ ] Identify format detection indicators (headers, layout, structure)
[ ] Implement format detection logic
[ ] Create extraction patterns for Format A (successful)
[ ] Create extraction patterns for Format B (failing)
[ ] Add conditional extraction based on detected format
[ ] Test against all 5 invoices
[ ] Validate all achieve ≥0.80 confidence
[ ] Document format variations in extractor
```

**Expected Confidence Improvement:** 0.53 avg → 0.85+ for all invoices

**Strategy:**
- Use format detection at start of extraction
- Route to appropriate extraction logic per format
- Consider using BaseExtractor helper methods more extensively

---

### 2.2 Wolverine Printing - Fix Consistent Missing Fields
**Priority:** 🟡 MEDIUM
**Current State:** 0.50 confidence (4 invoices, all exactly 0.50)
**At Risk:** $1,025.00

**Root Cause Analysis:**
- All invoices scoring exactly 50% indicates consistent missing fields
- Similar pattern to Amanda-Andrews (likely specific field type failing)
- May be line items or subtotal/tax breakdown not extracting

**Diagnostic Steps:**
1. Pull 2 sample Wolverine invoices
2. Compare extracted data with actual invoice content
3. Identify which fields extract successfully (50%) vs. fail (50%)
4. Determine if issue is line items, dates, or totals breakdown

**Implementation Tasks:**
```
[ ] Review `extractors/wolverine_printing.py` implementation
[ ] Extract markdown from 2 sample invoices
[ ] Map successfully extracted fields vs. missing fields
[ ] Identify why specific fields consistently fail
[ ] Review line item extraction patterns
[ ] Check subtotal/tax/total parsing logic
[ ] Implement fixes for missing field patterns
[ ] Add more robust parsing for failing field types
[ ] Test against all 4 invoices
[ ] Validate confidence ≥0.75
[ ] Document extraction improvements
```

**Expected Confidence Improvement:** 0.50 → 0.80+

**Focus Areas:**
- Line item table parsing
- Subtotal/tax breakdown extraction
- Date format handling

---

### 2.3 Sunset Press - Address Format Variations
**Priority:** 🟡 MEDIUM
**Current State:** Range 0.20-0.90 (45% below 0.7)
**At Risk:** $72,980.81

**Root Cause Analysis:**
- 5 low confidence, 6 good confidence = format variations
- Mix of good and poor results indicates multiple templates
- Largest dollar value in Phase 2

**Diagnostic Steps:**
1. Pull 2 high-confidence (0.90) invoices
2. Pull 2 low-confidence (0.20-0.40) invoices
3. Compare format differences
4. Identify template variations

**Implementation Tasks:**
```
[ ] Review `extractors/sunset_press.py` implementation
[ ] Extract markdown from high-confidence invoices
[ ] Extract markdown from low-confidence invoices
[ ] Document format differences between successful/failed
[ ] Identify common patterns in successful extractions
[ ] Identify failure patterns in low-confidence extractions
[ ] Implement format detection for Sunset Press templates
[ ] Add extraction patterns for alternate formats
[ ] Create conditional logic for format routing
[ ] Test against all 11 invoices
[ ] Validate all achieve ≥0.75 confidence
[ ] Document template variations
```

**Expected Confidence Improvement:** 0.61 avg → 0.85+ for all invoices

**High-Value Target:**
- Second-largest dollar value in Phase 2 ($73K)
- Improving this vendor significantly reduces at-risk total
- May require most complex multi-format handling

---

## 📋 Phase 3: Optimization (Ongoing)

**Duration:** Ongoing after Phases 1-2
**Focus:** Fine-tuning high-performing vendors
**Impact:** Optimize remaining 10-15% of invoices

### 3.1 Reflex Medical - Improve Low-Confidence Subset
**Current State:** 85 at 1.00, 10 at 0.90, 27 at 0.70, 9 at 0.80
**Target:** Boost 27 invoices from 0.70 → 0.90+

**Approach:**
```
[ ] Extract all 27 invoices at 0.70 confidence
[ ] Identify common patterns in low-confidence subset
[ ] Determine which fields are borderline or missing
[ ] Review successful 1.00 confidence invoices for comparison
[ ] Implement pattern enhancements for edge cases
[ ] Add more robust fallback patterns
[ ] Test improvements against low-confidence subset
[ ] Validate improvements don't regress high-confidence invoices
[ ] Re-run full Reflex batch (131 invoices)
[ ] Target: 95%+ at ≥0.90 confidence
```

**Expected Impact:** 27 invoices improved, 0.70 → 0.90+

---

### 3.2 OMICO - Boost from 0.80 to 0.90+
**Current State:** 27 at 0.80, 6 at 1.00
**Target:** Improve 0.80 invoices to 0.90+

**Approach:**
```
[ ] Sample 5 invoices at 0.80 confidence
[ ] Compare with 1.00 confidence invoices
[ ] Identify minor differences causing 0.80 vs. 1.00
[ ] Implement pattern refinements
[ ] Test against 0.80 subset
[ ] Validate improvements
```

**Expected Impact:** 27 invoices improved, 0.80 → 0.90+

---

### 3.3 YES Solutions - Marginal Improvement
**Current State:** 22 at 1.00, 3 at 0.80
**Target:** Improve 3 invoices from 0.80 → 1.00

**Approach:**
```
[ ] Review 3 invoices at 0.80 confidence
[ ] Identify minor extraction issues
[ ] Implement small refinements
[ ] Test improvements
```

**Expected Impact:** 3 invoices improved, 0.80 → 1.00

---

## 🛠️ Implementation Strategy

### General Workflow for Each Vendor Fix

**Step 1: Diagnostic Analysis**
1. Pull sample invoices (successful and failed examples)
2. Run DocumentProcessor to extract markdown
3. Manually compare markdown with expected extraction
4. Document findings in extractor comments

**Step 2: Pattern Implementation**
1. Review existing extractor code
2. Identify missing or incorrect patterns
3. Implement corrected regex patterns
4. Add field extraction logic
5. Update confidence calculation if needed

**Step 3: Testing & Validation**
1. Test against sample invoices
2. Validate confidence score improvement
3. Test against full vendor invoice set
4. Ensure no regressions on previously successful invoices
5. Document changes in extractor

**Step 4: Batch Validation**
1. Re-run batch processor for vendor
2. Compare before/after confidence distribution
3. Validate financial totals match expectations
4. Update vendor-extraction-issues.md with results

---

## 🧪 Testing Framework

### Test Scripts to Create

**Phase 1 Testing:**
```bash
# Test individual vendor fixes
uv run python tests/test_abox_extraction.py
uv run python tests/test_amanda_andrews_extraction.py
uv run python tests/test_pride_printing_extraction.py

# Run Phase 1 batch validation
uv run python scripts/validate_phase1_improvements.py
```

**Phase 2 Testing:**
```bash
# Test format variation handling
uv run python tests/test_dimax_extraction.py
uv run python tests/test_wolverine_extraction.py
uv run python tests/test_sunset_extraction.py

# Run Phase 2 batch validation
uv run python scripts/validate_phase2_improvements.py
```

**Phase 3 Testing:**
```bash
# Run optimization validation
uv run python scripts/validate_optimization.py

# Full system validation
uv run python scripts/process_all_invoices.py
```

---

## 📊 Progress Tracking

### Phase 1 Completion Criteria
- [ ] ABox: All 6 invoices ≥0.80 confidence
- [ ] Amanda-Andrews: All 18 invoices ≥0.70 confidence
- [ ] Pride Printing: Both invoices ≥0.80 confidence
- [ ] Phase 1 at-risk value reduced by $86,541.56
- [ ] Phase 1 batch report generated

### Phase 2 Completion Criteria
- [ ] Dimax: All 5 invoices ≥0.80 confidence
- [ ] Wolverine: All 4 invoices ≥0.75 confidence
- [ ] Sunset Press: All 11 invoices ≥0.75 confidence
- [ ] Phase 2 at-risk value reduced by $81,388.01
- [ ] Phase 2 batch report generated

### Phase 3 Completion Criteria
- [ ] Reflex Medical: 95%+ at ≥0.90 confidence
- [ ] OMICO: 90%+ at ≥0.90 confidence
- [ ] YES Solutions: 100% at ≥0.90 confidence
- [ ] Overall system: 95%+ at ≥0.80 confidence
- [ ] Final comprehensive batch report

---

## 🔧 Tools & Utilities

### Create Helper Scripts

**1. Diagnostic Script:**
```bash
# scripts/diagnose_vendor.py
# Usage: uv run python scripts/diagnose_vendor.py --vendor ABox --sample 3
# Outputs: Markdown extraction, field analysis, pattern suggestions
```

**2. Comparison Script:**
```bash
# scripts/compare_extractions.py
# Usage: uv run python scripts/compare_extractions.py --before output/run_20260108 --after output/run_20260110
# Outputs: Confidence improvements, regression detection
```

**3. Pattern Testing Script:**
```bash
# scripts/test_pattern.py
# Usage: uv run python scripts/test_pattern.py --pattern "INVOICE.*?(\d+)" --file sample.pdf
# Outputs: Pattern matches for quick regex testing
```

---

## 📈 Expected Results

### Before Improvements (Current State)
- High Confidence (≥0.7): 208 invoices (84.6%)
- Low Confidence (<0.7): 38 invoices (15.4%)
- At-Risk Value: $94,948.76 (9.8%)

### After Phase 1 (Week 1 Complete)
- High Confidence (≥0.7): 234 invoices (95.1%)
- Low Confidence (<0.7): 12 invoices (4.9%)
- At-Risk Value: ~$8,407.20 (0.9%)

### After Phase 2 (Week 2 Complete)
- High Confidence (≥0.8): 238 invoices (96.7%)
- Low Confidence (<0.8): 8 invoices (3.3%)
- At-Risk Value: <$5,000 (<0.5%)

### After Phase 3 (Complete)
- High Confidence (≥0.8): 235+ invoices (95.5%+)
- Excellent Confidence (≥0.9): 200+ invoices (81%+)
- At-Risk Value: <$2,000 (<0.2%)

---

## 🚨 Risk Mitigation

### Regression Prevention
- Test all changes against full vendor invoice set
- Compare before/after confidence distributions
- Validate no degradation of high-performing invoices
- Keep git history for rollback capability

### Version Control Strategy
```bash
# Create feature branch for each phase
git checkout -b phase1-critical-fixes
git checkout -b phase2-medium-priority
git checkout -b phase3-optimization

# Commit after each vendor fix
git commit -m "fix(abox): Implement corrected extraction patterns"
git commit -m "fix(amanda-andrews): Handle staffing invoice format"
```

### Testing Strategy
- Unit tests for each extractor
- Integration tests for batch processing
- Regression tests for high-performing vendors
- Manual spot-checks for critical invoices

---

## 📝 Documentation Updates

### Files to Update After Each Phase

**1. vendor-extraction-issues.md**
- Update confidence scores
- Mark completed fixes
- Adjust priorities

**2. CLAUDE.md**
- Update vendor status in "Supported Vendors" section
- Document any new patterns or techniques
- Update "Current Implementation Status"

**3. README.md**
- Update project status
- Add any new usage examples
- Document improvements

**4. Extractor Files**
- Add comprehensive docstrings
- Document format quirks
- Add inline comments for complex patterns

---

## 🎯 Success Metrics Dashboard

Create `scripts/generate_metrics.py` to track:

```markdown
## Extraction Quality Metrics

| Metric | Before | Phase 1 | Phase 2 | Phase 3 | Target |
|--------|--------|---------|---------|---------|--------|
| Avg Confidence | 0.82 | 0.88 | 0.92 | 0.94 | 0.90+ |
| High Confidence % | 84.6% | 95.1% | 96.7% | 97.5% | 95%+ |
| Failed Vendors | 3 | 0 | 0 | 0 | 0 |
| At-Risk Value | $94,949 | $8,407 | $5,000 | $2,000 | <$5,000 |
| Low Confidence Count | 38 | 12 | 8 | 6 | <10 |
```

---

## 💡 Lessons Learned (To Document)

Track learnings for future extractor development:

1. **Format Variations:**
   - How to detect multiple templates
   - Conditional extraction strategies

2. **OCR Challenges:**
   - Handling poor scan quality
   - Image-based PDF extraction

3. **Invoice Type Differences:**
   - Product vs. service invoices
   - Staffing vs. goods formats

4. **Pattern Optimization:**
   - Regex patterns that work well across vendors
   - Common failure patterns to avoid

---

## 📞 Stakeholder Communication

### Weekly Status Report Template

```markdown
## Week [X] Extractor Improvement Status

**Phase:** [1/2/3]
**Completed:** [X] vendors
**In Progress:** [Y] vendors
**Confidence Improvement:** [before]% → [after]%
**At-Risk Reduction:** $[before] → $[after]

**Key Achievements:**
- [Achievement 1]
- [Achievement 2]

**Challenges:**
- [Challenge 1 and mitigation]

**Next Week:**
- [Priority 1]
- [Priority 2]
```

---

## 🔄 Continuous Improvement

### Post-Implementation Monitoring

**Monthly Reviews:**
- Re-run batch processing
- Track confidence drift over time
- Identify new invoice format variations
- Update extractors as needed

**Quarterly Audits:**
- Sample manual validation of extractions
- Compare extracted data with source PDFs
- Identify systematic issues
- Update extraction patterns

---

*Plan created: 2026-01-08*
*Based on: vendor-extraction-issues.md analysis*
*Next review: After Phase 1 completion*
