# Vendor Extraction Issues Analysis

**Generated:** 2026-01-08
**Based on Batch Run:** `output/run_20260108_111854_combined`
**Total Invoices Analyzed:** 246

---

## Executive Summary

Analysis of 246 invoices across 10 vendors reveals significant extraction quality variations. Five vendors show critical issues requiring immediate attention, while others perform well with room for optimization.

**Overall Statistics:**
- High Confidence (≥0.7): 208 invoices (84.6%)
- Low Confidence (<0.7): 38 invoices (15.4%)
- Total Line Items Extracted: 260

---

## 🔴 Critical Issues (Immediate Action Required)

### 1. ABox
**Status:** CRITICAL FAILURE
**Confidence:** 0.20 average
**Invoices:** 6 invoices, ALL failing

**Problem:**
- Only 20% confidence across all invoices
- Likely OCR quality issues or incorrect extraction patterns
- Scanned images may have poor text recognition

**Impact:** $55,763.31 in invoice value potentially miscategorized

**Recommended Actions:**
1. Review sample ABox invoice manually
2. Check OCR output quality in markdown
3. Verify extraction patterns match actual invoice format
4. Consider if document preprocessing needed

**Priority:** 🔥 HIGHEST

---

### 2. AMANDA-ANDREWS PERSONNEL CORP
**Status:** CONSISTENTLY LOW
**Confidence:** 0.50 average
**Invoices:** 18 invoices, ALL at 0.50 confidence

**Problem:**
- 100% of invoices scoring exactly 50%
- Staffing/personnel invoice format differs from product invoices
- Likely missing key fields consistently (date, total, or line items)

**Impact:** $30,372.00 in invoice value with low confidence

**Recommended Actions:**
1. Review what fields are being extracted vs. missed
2. Staffing invoices may not have line items (summary only)
3. Adjust confidence calculation for staffing invoice format
4. Verify date and total extraction patterns

**Priority:** 🔴 HIGH

---

### 3. Pride Printing LLC
**Status:** SEVERE ISSUES
**Confidence:** 0.20-0.40 range
**Invoices:** 2 invoices

**Problem:**
- Both invoices scoring very low (20% and 40%)
- Stub extractor may not be fully implemented
- Format likely not well understood

**Impact:** $406.25 in invoice value (small vendor but critical quality issue)

**Recommended Actions:**
1. Implement full extraction logic (currently stub)
2. Review Pride Printing invoice format
3. Add specific patterns for this vendor

**Priority:** 🔴 HIGH

---

## ⚠️ Medium Priority Issues

### 4. Dimax Corporation
**Status:** INCONSISTENT
**Confidence:** Mix of 0.20 (3 invoices) and 1.00 (2 invoices)
**Invoices:** 5 total (60% failure rate)

**Problem:**
- Highly inconsistent results suggest multiple invoice formats
- Some invoices extract perfectly, others fail completely
- May have different templates or layout variations

**Impact:** $7,382.20 in invoice value

**Recommended Actions:**
1. Compare successful vs. failed invoices
2. Identify format variations
3. Add pattern matching for alternate formats
4. Consider conditional extraction logic

**Priority:** 🟡 MEDIUM

---

### 5. Wolverine Printing
**Status:** CONSISTENT LOW
**Confidence:** 0.50 average
**Invoices:** 4 invoices, ALL at 0.50

**Problem:**
- All invoices scoring exactly 50%
- Similar pattern to Amanda-Andrews (missing specific fields)
- Likely line items or subtotal/tax breakdown not extracting

**Impact:** $1,025.00 in invoice value

**Recommended Actions:**
1. Review what's extracting vs. what's missing
2. Check line item extraction patterns
3. Verify table parsing for this vendor
4. May need format-specific adjustments

**Priority:** 🟡 MEDIUM

---

### 6. Sunset Press
**Status:** VARIABLE
**Confidence:** Range 0.20-0.90
**Invoices:** 11 total (5 low confidence, 6 good confidence)

**Problem:**
- 45% of invoices scoring low (<0.7)
- Mix of good and poor results suggests format variations
- Some invoices work well, others fail

**Impact:** $72,980.81 in invoice value

**Recommended Actions:**
1. Identify pattern differences between high/low confidence invoices
2. May have multiple invoice templates
3. Review failed extractions for common issues

**Priority:** 🟡 MEDIUM

---

## ✅ Well-Performing Vendors

### REFLEX MEDICAL CORP
**Confidence:** 85 at 1.00, 10 at 0.90, 27 at 0.70, 9 at 0.80
**Invoices:** 131 total
**Status:** Good overall, room for improvement

**Performance:**
- 72% of invoices at high confidence (≥0.9)
- 21% at medium-low confidence (0.7)
- Largest vendor by volume

**Optimization Opportunity:**
- 27 invoices at 0.70 could be improved
- Review these cases for pattern enhancements
- Fine-tuning could boost to 90%+ success rate

**Impact:** $425,461.90 in invoice value

---

### YES Solutions LLC
**Confidence:** 22 at 1.00, 3 at 0.80
**Invoices:** 25 total
**Status:** Excellent

**Performance:**
- 88% at perfect confidence (1.00)
- 12% at good confidence (0.80)
- Very reliable extraction

**Impact:** $16,576.00 in invoice value

---

### OMICO
**Confidence:** 27 at 0.80, 6 at 1.00
**Invoices:** 33 total
**Status:** Good

**Performance:**
- 82% at 0.80 confidence
- 18% at perfect confidence
- Consistent, reliable extraction

**Impact:** $319,279.10 in invoice value (2nd largest vendor)

---

### Stölzle Glassware
**Confidence:** 11 at 0.90
**Invoices:** 11 total
**Status:** Very Good

**Performance:**
- 100% of invoices at 0.90 confidence
- Consistent high-quality extraction
- Well-understood format

**Impact:** $19,646.60 in invoice value

---

## 📊 Confidence Distribution by Vendor

| Vendor | Total | High (≥0.9) | Medium (0.7-0.89) | Low (<0.7) | Avg Confidence |
|--------|-------|-------------|-------------------|------------|----------------|
| ABox | 6 | 0 | 0 | 6 (100%) | 0.20 |
| AMANDA-ANDREWS | 18 | 0 | 0 | 18 (100%) | 0.50 |
| Pride Printing | 2 | 0 | 0 | 2 (100%) | 0.30 |
| Wolverine Printing | 4 | 0 | 0 | 4 (100%) | 0.50 |
| Dimax Corporation | 5 | 2 (40%) | 0 | 3 (60%) | 0.53 |
| Sunset Press | 11 | 2 (18%) | 4 (36%) | 5 (45%) | 0.61 |
| OMICO | 33 | 6 (18%) | 27 (82%) | 0 | 0.83 |
| Stölzle Glassware | 11 | 11 (100%) | 0 | 0 | 0.90 |
| REFLEX MEDICAL | 131 | 95 (73%) | 9 (7%) | 27 (21%) | 0.91 |
| YES Solutions | 25 | 22 (88%) | 3 (12%) | 0 | 0.99 |

---

## 💰 Financial Impact Summary

| Vendor | Invoice Value | Confidence | Risk Level |
|--------|--------------|------------|------------|
| REFLEX MEDICAL CORP | $425,461.90 | Good | Low |
| OMICO | $319,279.10 | Good | Low |
| Sunset Press | $72,980.81 | Variable | Medium |
| ABox | $55,763.31 | Critical | HIGH |
| AMANDA-ANDREWS | $30,372.00 | Low | HIGH |
| Stölzle Glassware | $19,646.60 | Very Good | Low |
| YES Solutions | $16,576.00 | Excellent | Low |
| Dimax Corporation | $7,382.20 | Inconsistent | Medium |
| Wolverine Printing | $1,025.00 | Low | Medium |
| Pride Printing | $406.25 | Critical | HIGH |

**Total at Risk (Low Confidence):** $94,948.76 (9.8% of total invoice value)

---

## 📋 Recommended Action Plan

### Phase 1: Critical Fixes (This Week)
1. **ABox** - Investigate and fix 0.20 confidence issue
   - Pull sample invoice for manual review
   - Check OCR quality and extraction patterns
   - Test fixes with all 6 invoices

2. **Amanda-Andrews** - Fix consistent 0.50 score
   - Identify missing fields
   - Adjust for staffing invoice format
   - Validate with all 18 invoices

3. **Pride Printing** - Implement full extractor
   - Replace stub with complete logic
   - Test with both invoices

### Phase 2: Medium Priority (Next Sprint)
4. **Dimax** - Handle format variations
   - Compare successful vs. failed invoices
   - Add conditional extraction logic

5. **Wolverine** - Improve to 0.70+ confidence
   - Fix consistently missing fields

6. **Sunset Press** - Address format variations
   - Identify and handle multiple templates

### Phase 3: Optimization (Ongoing)
7. **Reflex Medical** - Improve 27 low-confidence invoices
   - Fine-tune patterns to boost 0.70 → 0.90+

8. **Monitoring** - Track improvements over time
   - Re-run batch after each fix
   - Measure confidence improvements

---

## 🎯 Success Metrics

**Target Goals:**
- Overall confidence: >90% at ≥0.8 confidence
- Critical vendors (ABox, Amanda-Andrews, Pride): 0.80+ confidence
- Zero invoices below 0.50 confidence
- Consistent extraction across all vendors

**Current Baseline:**
- Overall confidence: 84.6% at ≥0.7 confidence
- 38 invoices (15.4%) below 0.7 confidence
- 3 vendors critically failing (<0.50 average)

---

## 📝 Next Steps

1. Review this analysis with the team
2. Prioritize vendors based on:
   - Financial impact (dollar value at risk)
   - Volume (number of invoices affected)
   - Confidence severity (how low the scores are)
3. Pull sample invoices for failing vendors
4. Debug and fix extraction patterns
5. Re-run batch processing to validate improvements
6. Update this document with progress

---

*Generated from batch run: `output/run_20260108_111854_combined`*
*Last updated: 2026-01-08*
