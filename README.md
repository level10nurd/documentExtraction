# Invoice Data Extraction System

Automated invoice data extraction system that processes PDF invoices from multiple vendors and extracts structured data for analytics.

## Overview

This system processes hundreds of PDF invoices from 4-5 different vendor formats and extracts:
- **Header fields**: Vendor, invoice date, invoice number, PO number
- **Line items**: Quantity, item code, description, price each, amount
- **Totals**: Subtotal, sales tax, total

**Source invoices**: `/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills`

**Vendor Organization**: Invoices are organized by vendor in subdirectories under `Bills/`:
```
Bills/
├── Reflex/          # REFLEX MEDICAL CORP
├── Sunset/          # Sunset Press
├── Wolverine/       # Wolverine Printing
├── Omico/           # OMICO, Inc.
└── ...              # Other vendors
```

**Output format**: CSV files (normalized format with separate files for headers and line items)

## Features

- ✅ **Path-based vendor detection** - Primary detection using directory structure
- ✅ Content pattern matching fallback - For edge cases and validation
- ✅ Pydantic data models with automatic validation
- ✅ Duplicate invoice detection
- ✅ Sample-first validation workflow
- ✅ Confidence scoring for extractions
- 🚧 Parallel batch processing (in progress)
- 🚧 CSV export with deduplication (in progress)

## Supported Vendors

Each vendor has a dedicated directory under `Bills/` and a corresponding extractor:

| Vendor | Directory | Status |
|--------|-----------|--------|
| REFLEX MEDICAL CORP | `Bills/Reflex/` | ✅ Fully implemented |
| Sunset Press | `Bills/Sunset/` | ✅ Extractor created |
| Wolverine Printing | `Bills/Wolverine/` | ✅ Extractor created |
| OMICO, Inc. | `Bills/Omico/` | ✅ Extractor created |
| YES Solutions LLC | `Bills/YesSolutions/` | ✅ Extractor created |
| Stölzle Glassware | `Bills/Stolzle/` | ✅ Extractor created |
| Pride Printing LLC | `Bills/PridePrinting/` | ✅ Extractor created |
| Dimax Corporation | `Bills/DiMax/` | ✅ Extractor created |
| Amanda-Andrews Personnel | `Bills/AmandaAndrews/` | ✅ Extractor created |
| ABox | `Bills/ABox/` | ✅ Extractor stub |

**Total:** 10 vendors with directory-based organization

## Installation

This project uses UV for package management:

```bash
# Install dependencies
uv sync

# Or add individual packages
uv add pydantic python-dateutil tqdm
```

**Requirements**: Python 3.11+

## Quick Start

### 1. Test Batch Processor

Test with a small sample to verify everything works:

```bash
# Process first 10 invoices as a test
uv run python scripts/test_batch_processor.py
```

This will:
- Convert PDFs using Docling MCP
- Auto-detect vendors from file paths
- Route to appropriate extractors
- Display success rate and statistics
- Save results to `output/batch_test_results.json`

### 2. Full Batch Processing

Process all invoices in your directory:

```bash
# Process all invoices with 4 parallel workers
uv run python -c "
from pathlib import Path
from processors import BatchProcessor
from config import Config

processor = BatchProcessor(num_workers=4)
result = processor.process_directory(Config.SOURCE_DIR)
processor.print_summary(result)

# Get successful invoices
invoices = result.get_successful_invoices()
print(f'\\nExtracted {len(invoices)} invoices successfully!')
"
```

**For programmatic use:**

```python
from processors import BatchProcessor
from pathlib import Path

# Initialize processor
processor = BatchProcessor(num_workers=4)

# Process directory
result = processor.process_directory(
    directory=Path("/path/to/invoices"),
    max_files=None,  # Process all files
    file_pattern="*.pdf"
)

# Access results
successful_invoices = result.get_successful_invoices()
failed_results = result.get_failed_results()
statistics = result.statistics

# Export to CSV (implement CSVExporter)
# from exporters import CSVExporter
# CSVExporter().export(successful_invoices, Path("output/"))
```

### 3. Individual Vendor Testing

Test specific vendor extractors:

```bash
# Run all tests
uv run python -m pytest tests/

# Test specific vendor
uv run python tests/test_omico_extraction.py
```

## Project Structure

```
documentextraction/
├── main.py                       # CLI entry point (in development)
├── config.py                     # Configuration settings
│
├── models/                       # Data models
│   ├── __init__.py
│   ├── invoice.py               # Invoice and LineItem Pydantic models
│   └── vendor.py                # VendorType enum and detection patterns
│
├── extractors/                   # Vendor-specific extractors
│   ├── __init__.py
│   ├── base.py                  # Abstract base extractor
│   ├── reflex_medical.py        # REFLEX MEDICAL CORP extractor ✅
│   ├── sunset_press.py          # Sunset Press extractor 🚧
│   ├── wolverine_printing.py    # Wolverine Printing extractor 🚧
│   └── omico.py                 # OMICO extractor 🚧
│
├── processors/                   # Document and batch processing
│   ├── __init__.py
│   └── document_processor.py    # Docling MCP interaction ✅
│
├── exporters/                    # Data export
│   ├── __init__.py
│   └── csv_exporter.py          # CSV generation (todo)
│
├── utils/                        # Utilities
│   ├── __init__.py
│   ├── logging_config.py        # Logging setup ✅
│   └── manifest_loader.py       # Manifest utilities ✅
│
├── scripts/                      # Standalone utility scripts
│   ├── identify_vendors.py      # Full vendor identification
│   └── identify_vendors_by_filename.py  # Quick filename-based scan
│
├── tests/                        # Test suite
│   └── test_*.py                # Various extraction tests
│
└── output/                       # Generated files (gitignored)
    ├── *.json                   # Vendor manifests
    ├── *.log                    # Execution logs
    └── *.csv                    # Exported data
```

## Configuration

Edit `config.py` to customize:
- Source/output directories
- Batch processing workers (default: 4)
- Confidence thresholds
- Duplicate detection strategy
- CSV format options

## Development

### Code Quality

```bash
# Lint and format
uv run ruff check .
uv run ruff format .

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=. --cov-report=html
```

### Adding a New Vendor Extractor

1. **Create vendor directory**: Add `Bills/NewVendor/` and move invoices there
2. **Update vendor mapping** in `models/vendor.py`:
   ```python
   class VendorType(str, Enum):
       NEW_VENDOR = "New Vendor Name"

   VENDOR_DIRECTORIES[VendorType.NEW_VENDOR] = "NewVendor"
   ```
3. **Create extractor**: `extractors/new_vendor.py` extending `BaseExtractor`
   ```python
   def __init__(self, doc_processor):
       super().__init__(doc_processor, vendor_type=VendorType.NEW_VENDOR)
   ```
4. **Register in factory**: Add to `extractors/factory.py`
5. **Write tests**: `tests/test_new_vendor_extraction.py`
6. *Optional*: Add content patterns to `VENDOR_PATTERNS` for fallback detection

See `extractors/reflex_medical.py` for a complete example.

## Architecture

**Extraction Pipeline:**
```
PDF (in Bills/<vendor>/) → Path-Based Vendor Detection →
Document Conversion (Docling) → Extractor Selection →
Data Extraction → Validation → CSV Export
```

**Vendor Detection Strategy:**
1. **Primary**: Directory structure (`Bills/Reflex/` → `REFLEX_MEDICAL`) - Confidence: 1.0
2. **Fallback**: Content pattern matching - Confidence: 0.5-0.9
3. **Tertiary**: Filename patterns - Confidence: 0.3-0.5

**Key Technologies:**
- **Docling MCP**: Document processing and PDF conversion
- **Pydantic**: Data validation and models
- **UV**: Fast Python package management
- **Directory-based organization**: Deterministic vendor routing

## Current Status

**Phase 1 (Complete) - Foundation:**
- ✅ Data models with Pydantic validation
- ✅ Document processor with vendor detection
- ✅ Base extractor framework
- ✅ 9 vendor-specific extractors implemented
- ✅ Extractor factory for automatic routing
- ✅ Project organization and structure

**Phase 2 (Complete) - Batch Processing:**
- ✅ BatchProcessor with parallel execution (ThreadPoolExecutor)
- ✅ Progress tracking with tqdm
- ✅ Comprehensive error handling and retry logic
- ✅ Detailed statistics and reporting
- ✅ Result models (InvoiceResult, BatchStatistics)

**Phase 3 (In Progress) - Export & Production:**
- 🚧 CSV exporter (normalized format)
- 🚧 Main CLI interface
- 🚧 Comprehensive test coverage
- 🚧 Production deployment guide

## Maintenance

See `CLAUDE.md` for:
- Detailed implementation notes
- File maintenance guidelines
- Development best practices
- MCP tool usage examples

## Troubleshooting

**Issue**: Docling MCP server not available
```bash
# Verify MCP configuration
cat .mcp.json

# Test MCP connection
uvx --from=docling-mcp docling-mcp-server
```

**Issue**: Import errors
```bash
# Reinstall dependencies
rm -rf .venv
uv sync
```

**Issue**: Vendor detection fails
- Verify file is in correct vendor directory (`Bills/<vendor>/`)
- Check directory name matches `VENDOR_DIRECTORIES` in `models/vendor.py`
- As fallback, add content patterns to `VENDOR_PATTERNS`

**Issue**: Extractor not found for vendor
- Ensure extractor registered in `extractors/factory.py`
- Verify vendor_type is set in extractor `__init__`