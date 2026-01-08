# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an invoice data extraction project designed to process hundreds of PDF invoices from multiple vendors (4-5 different formats) and extract structured data for analytics. The project uses Docling for document processing and extraction.

**Key extraction fields:**
- Vendor, invoice date, invoice number, PO number
- Line items: quantity, item, description, price each, amount
- Subtotal, sales tax, total

**Source data location:** Configured per-environment in `environments.json` (see Configuration section below)

**Vendor Organization:** Invoices are organized by vendor in subdirectories under `Bills/`:
```
Bills/
├── Reflex/          # REFLEX MEDICAL CORP invoices
├── Sunset/          # Sunset Press invoices
├── Wolverine/       # Wolverine Printing invoices
├── Omico/           # OMICO, Inc. invoices
├── YesSolutions/    # YES Solutions LLC invoices
├── Stolzle/         # Stölzle Glassware invoices
├── PridePrinting/   # Pride Printing LLC invoices
├── DiMax/           # Dimax Corporation invoices
├── AmandaAndrews/   # Amanda-Andrews Personnel Corp invoices
└── ABox/            # ABox invoices
```

## Development Environment

**Package Manager:** UV (not pip)
- Install dependencies: `uv sync`
- Run Python scripts: `uv run python main.py`
- Add packages: `uv add <package-name>`
- Run with uvx: `uvx <command>`

**Python version:** 3.11+

**Key dependencies:**
- docling (>=2.66.0) - Document processing and extraction
- ruff (>=0.14.10) - Linting and formatting
- pydantic - Data validation and models
- python-dateutil - Flexible date parsing
- tqdm - Progress bars for batch processing

## Environment Configuration

The project supports multiple environments to handle different source locations across computers. This is configured via `environments.json`.

### Setup

1. **Create/edit `environments.json`** in the project root:

```json
{
  "environments": {
    "work_mac": {
      "description": "Work MacBook Pro",
      "source_dir": "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills",
      "output_dir": "output",
      "max_workers": 4
    },
    "home_laptop": {
      "description": "Home Laptop",
      "source_dir": "/home/dalton/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills",
      "output_dir": "output",
      "max_workers": 8
    }
  },
  "default": "work_mac"
}
```

2. **Check your environment** before running scripts:

```bash
uv run python scripts/check_environment.py
```

3. **List all environments**:

```bash
uv run python scripts/check_environment.py --list
```

### Usage in Code

**Method 1: Use default environment** (recommended):

```python
from config import Config

# Load default environment from environments.json
Config.load_environment()

# Now Config.SOURCE_DIR points to correct location
print(Config.SOURCE_DIR)
```

**Method 2: Specify environment explicitly**:

```python
from config import Config

# Load specific environment
Config.load_environment("home_laptop")

# Access configured paths
reflex_dir = Config.SOURCE_DIR / "Reflex"
```

**Method 3: Use environment variable** (overrides default):

```bash
# Set environment variable
export INVOICE_ENV=home_laptop

# Run script (will use home_laptop config)
uv run python tests/test_reflex_batch.py
```

**Method 4: Override with environment variables** (highest priority):

```bash
# Override source directory completely
export INVOICE_SOURCE_DIR="/custom/path/to/Bills"
uv run python tests/test_reflex_batch.py
```

### Priority Order

Configuration values are determined in this order (highest to lowest priority):

1. Environment variables (`INVOICE_SOURCE_DIR`, `OUTPUT_DIR`, etc.)
2. Specified environment in `Config.load_environment("env_name")`
3. `INVOICE_ENV` environment variable
4. Default environment from `environments.json`
5. Hardcoded defaults in `config.py`

### Adding New Computers

To use the project on a new computer:

1. Edit `environments.json` and add your computer's configuration
2. Set appropriate `source_dir` for that computer
3. Optionally set it as the default
4. Run `check_environment.py` to verify

## Document Processing

The project uses the Docling library directly for PDF document processing:
- Configured in `processors/document_processor.py`
- Uses `DocumentConverter` from `docling.document_converter`
- No MCP dependency required for standalone operation
- Documents cached in memory for efficient reprocessing

## Code Linting

Use ruff for code quality:
```bash
uv run ruff check .
uv run ruff format .
```

## Project Structure

```
documentextraction/
├── main.py                       # CLI entry point (to be implemented)
├── config.py                     # Configuration settings
├── models/                       # Data models
│   ├── invoice.py               # Invoice and LineItem Pydantic models
│   └── vendor.py                # VendorType enum and detection patterns
├── extractors/                   # Vendor-specific extractors
│   ├── base.py                  # Abstract base extractor ✅
│   ├── factory.py               # Extractor factory ✅
│   ├── reflex_medical.py        # REFLEX MEDICAL CORP extractor ✅
│   ├── sunset_press.py          # Sunset Press extractor ✅
│   ├── wolverine_printing.py    # Wolverine Printing extractor ✅
│   ├── omico.py                 # OMICO extractor ✅
│   ├── yes_solutions.py         # YES Solutions extractor ✅
│   ├── stolzle_lausitz.py       # Stölzle Glassware extractor ✅
│   ├── pride_printing.py        # Pride Printing extractor ✅
│   ├── dimax.py                 # Dimax Corporation extractor ✅
│   ├── amanda_andrews.py        # Amanda-Andrews extractor ✅
│   └── abox.py                  # ABox extractor ✅
├── processors/                   # Document and batch processing
│   ├── document_processor.py    # Docling direct integration ✅
│   └── batch_processor.py       # Parallel batch processing ✅
├── exporters/                    # Data export
│   └── csv_exporter.py          # CSV generation (todo)
└── utils/                        # Utilities
    ├── logging_config.py        # Logging setup ✅
    ├── validators.py            # Data validation (todo)
    └── duplicate_detector.py    # Duplicate detection (todo)
```

## Architecture Overview

**Extraction Pipeline:**
```
PDF (in Bills/<vendor>/) → Path-Based Vendor Detection → DocumentProcessor →
Extractor Selection → Data Extraction → Validation → CSV Export
```

**Vendor Detection Strategy:**
1. **Primary**: Directory structure (`Bills/Reflex/` → `VendorType.REFLEX_MEDICAL`)
2. **Fallback**: Content pattern matching (regex patterns in markdown)
3. **Tertiary**: Filename patterns (lowest confidence)

**Key Design Patterns:**
- **Directory-Based Organization**: Each vendor has dedicated folder under `Bills/`
- **Factory Pattern**: Routes documents to vendor-specific extractors via `ExtractorFactory`
- **Pydantic Models**: Type-safe data validation with automatic currency/date parsing
- **Direct Docling Integration**: Document processing via `DocumentConverter` library
- **Modular Extractors**: Each vendor has dedicated extraction logic with vendor_type set
- **Parallel Processing**: ThreadPoolExecutor for concurrent invoice processing

**Vendor Directory Mapping:**
The mapping between vendor types and directories is defined in `models/vendor.py`:
- `VENDOR_DIRECTORIES`: Maps `VendorType` enum to directory name
- `DIRECTORY_TO_VENDOR`: Reverse lookup for path-based detection
- `detect_vendor_from_path()`: Extracts vendor from file path

**Supported Vendors:**
1. REFLEX MEDICAL CORP (`Bills/Reflex/`) - ✅ Fully implemented
2. Sunset Press (`Bills/Sunset/`) - ✅ Extractor created
3. Wolverine Printing (`Bills/Wolverine/`) - ✅ Extractor created
4. OMICO, Inc. (`Bills/Omico/`) - ✅ Extractor created
5. YES Solutions LLC (`Bills/YesSolutions/`) - ✅ Extractor created
6. Stölzle Glassware (`Bills/Stolzle/`) - ✅ Extractor created
7. Pride Printing LLC (`Bills/PridePrinting/`) - ✅ Extractor created
8. Dimax Corporation (`Bills/DiMax/`) - ✅ Extractor created
9. Amanda-Andrews Personnel Corp (`Bills/AmandaAndrews/`) - ✅ Extractor created
10. ABox (`Bills/ABox/`) - ✅ Extractor stub created

## Current Implementation Status

**Phase 1 - Foundation (Complete):**
- ✅ Data models with Pydantic validation
- ✅ Configuration management
- ✅ Logging infrastructure
- ✅ Document processor with Docling direct integration
- ✅ Base extractor with helper methods
- ✅ All 10 vendor extractors implemented

**Phase 2 - Core Processing (Complete):**
- ✅ Extractor factory with automatic vendor routing
- ✅ Batch processor with parallel execution (ThreadPoolExecutor)
- ✅ Batch result tracking and statistics
- ✅ Directory-based vendor detection (1.0 confidence)
- ✅ Test scripts for batch processing

**Phase 3 - Remaining Work:**
- Duplicate detection utility
- CSV exporter (normalized format)
- Main CLI interface
- Data validation utilities

## Testing

To test the current implementation with a sample invoice:
```bash
uv run python -c "
from processors.document_processor import DocumentProcessor
from extractors.reflex_medical import ReflexMedicalExtractor

# Initialize
processor = DocumentProcessor()
extractor = ReflexMedicalExtractor(processor)

# Process invoice from Reflex directory
pdf_path = '/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Reflex/Bill_62935_Inv_62935_from_REFLEX_MEDICAL_CORP_1280567_199.pdf'

# Vendor detection now works from path
vendor, confidence = processor.detect_vendor(file_path=pdf_path)
print(f'Detected: {vendor.value} (confidence: {confidence})')

# Convert and extract
doc_key = processor.convert_document(pdf_path)
markdown = processor.get_document_markdown(doc_key)
invoice = extractor.extract(doc_key, markdown, 'Bill_62935.pdf')

# Display results
print(invoice.model_dump_json(indent=2))
"
```

## Vendor Detection Implementation

**How It Works:**

The system uses a three-tier vendor detection strategy, prioritizing file path over content analysis:

1. **Path-Based Detection (Highest Confidence: 1.0)**
   ```python
   from models.vendor import detect_vendor_from_path

   # Automatically detects from path structure
   vendor = detect_vendor_from_path('/path/to/Bills/Reflex/invoice.pdf')
   # Returns: VendorType.REFLEX_MEDICAL
   ```
   - Looks for `Bills/` directory in path
   - Extracts next subdirectory name (e.g., "Reflex")
   - Maps to vendor using `DIRECTORY_TO_VENDOR` dict
   - Returns `VendorType.UNKNOWN` if no match

2. **Content Pattern Matching (Fallback: 0.5-0.9 confidence)**
   - Uses regex patterns defined in `VENDOR_PATTERNS`
   - Searches markdown content for vendor-specific text
   - Confidence based on number of pattern matches

3. **Filename Patterns (Lowest Confidence: 0.3-0.5)**
   - Legacy support for old file naming
   - Checks for vendor keywords in filename

**Using Vendor Detection:**

```python
from processors.document_processor import DocumentProcessor

processor = DocumentProcessor()

# Method 1: Path-based (recommended)
vendor, conf = processor.detect_vendor(file_path='/path/to/Bills/Reflex/inv.pdf')

# Method 2: Content-based (fallback)
vendor, conf = processor.detect_vendor(markdown=doc_content, filename='invoice.pdf')

# Method 3: Combined (best practice)
vendor, conf = processor.detect_vendor(
    file_path='/path/to/Bills/Reflex/inv.pdf',
    markdown=doc_content,
    filename='invoice.pdf'
)
```

**Adding New Vendors:**

1. Add directory under `Bills/` (e.g., `Bills/NewVendor/`)
2. Update `models/vendor.py`:
   ```python
   class VendorType(str, Enum):
       NEW_VENDOR = "New Vendor Name"

   VENDOR_DIRECTORIES[VendorType.NEW_VENDOR] = "NewVendor"
   ```
3. Create extractor in `extractors/new_vendor.py`
4. Register in `extractors/factory.py`
5. Pattern matching is now optional (used only for edge cases)

## Development Notes

### Document Processing with Docling

The project uses Docling library directly for PDF processing. The `DocumentProcessor` class provides:

```python
from processors.document_processor import DocumentProcessor

processor = DocumentProcessor()

# Convert PDF to Docling document (cached)
doc_key = processor.convert_document('/path/to/invoice.pdf')

# Export to markdown for extraction
markdown = processor.get_document_markdown(doc_key, max_size=None)

# Get document structure overview
structure = processor.get_document_structure(doc_key)

# Search for text in document
results = processor.search_text(doc_key, 'invoice number')
```

**Key Methods:**
- `convert_document(pdf_path)` - Converts PDF using `DocumentConverter`, returns doc_key (file path)
- `get_document_markdown(doc_key)` - Exports document to markdown format
- `get_document_structure(doc_key)` - Returns page count and element statistics
- `search_text(doc_key, term)` - Searches markdown content for term
- `detect_vendor(file_path=...)` - Detects vendor from directory structure

### Batch Processing

Use `BatchProcessor` for processing multiple invoices in parallel:

```python
from processors.batch_processor import BatchProcessor
from config import Config

processor = BatchProcessor(num_workers=4)

# Process all invoices in a vendor directory
result = processor.process_directory(
    directory=Config.SOURCE_DIR / "Reflex",
    max_files=None  # Process all files
)

# Print summary statistics
processor.print_summary(result)

# Get successful invoices
successful = result.get_successful_invoices()

# Get failed results for review
failed = result.get_failed_results()
```

## File Organization and Maintenance Guidelines

### Directory Structure Standards

**Core Application Code** (checked into git):
- `models/` - Data models only, no business logic
- `extractors/` - Vendor-specific extraction implementations
- `processors/` - Document and batch processing orchestration
- `exporters/` - Data export formatting and output
- `utils/` - Shared utilities (logging, validation, helpers)

**Scripts and Tools** (checked into git):
- `scripts/` - Standalone utility scripts for analysis, migration, etc.
- `tests/` - Test suite organized by module/vendor

**Configuration** (checked into git):
- `config.py` - Application configuration with sensible defaults
- `.mcp.json` - MCP server configuration
- `pyproject.toml` - Python project metadata and dependencies
- `.gitignore` - Git exclusion patterns

**Generated/Output Files** (NOT checked into git):
- `output/` - All generated files (manifests, logs, CSVs)
- `.venv/` - Virtual environment
- `__pycache__/` - Python bytecode cache
- `*.log` - Log files

### Module Organization Rules

1. **Each module must have `__init__.py`** that exports public interface:
   ```python
   """Module description."""

   from module.submodule import PublicClass

   __all__ = ["PublicClass"]
   ```

2. **Import from modules, not submodules** in application code:
   ```python
   # Good
   from models import Invoice, VendorType
   from extractors import ReflexMedicalExtractor

   # Avoid
   from models.invoice import Invoice
   from models.vendor import VendorType
   ```

3. **Organize by feature/vendor, not by type**:
   - Each extractor is self-contained in one file
   - Shared utilities go in `extractors/base.py`
   - Vendor-specific helpers stay in vendor extractor file

### File Naming Conventions

- **Python modules**: `snake_case.py`
- **Classes**: `PascalCase` (one primary class per file)
- **Test files**: `test_<feature>.py` or `test_<vendor>_extraction.py`
- **Scripts**: Descriptive verb phrase: `identify_vendors.py`, `export_to_csv.py`
- **Output files**: Generated with timestamps in `output/` directory

### Code Organization Within Files

1. **Standard import order**:
   ```python
   # Standard library
   import json
   from pathlib import Path

   # Third-party
   from pydantic import BaseModel
   from tqdm import tqdm

   # Local application
   from config import Config
   from models import Invoice
   from utils import get_logger
   ```

2. **Class organization**:
   ```python
   class ExtractorName:
       """Class docstring."""

       # Class constants
       CONSTANT = "value"

       def __init__(self):
           """Initialize."""
           pass

       # Public methods
       def public_method(self):
           pass

       # Private helpers (prefixed with _)
       def _helper_method(self):
           pass
   ```

3. **Module-level functions after classes**, in order of importance

### Adding New Features

#### Adding a New Vendor Extractor

1. **Create the extractor file** (`extractors/vendor_name.py`):
   ```python
   from extractors.base import BaseExtractor
   from models import Invoice

   class VendorNameExtractor(BaseExtractor):
       """Extractor for Vendor Name invoices."""
       pass
   ```

2. **Add vendor patterns** to `models/vendor.py`:
   ```python
   class VendorType(str, Enum):
       VENDOR_NAME = "VendorName"

   VENDOR_PATTERNS = {
       VendorType.VENDOR_NAME: [
           re.compile(r"VENDOR\s+NAME", re.IGNORECASE),
           # More patterns...
       ]
   }
   ```

3. **Register in `extractors/__init__.py`**:
   ```python
   from extractors.vendor_name import VendorNameExtractor

   __all__ = [..., "VendorNameExtractor"]
   ```

4. **Write tests** in `tests/test_vendor_name_extraction.py`

5. **Update documentation** in README.md and CLAUDE.md

#### Adding New Utilities

1. Create focused utility file in `utils/`
2. Add public exports to `utils/__init__.py`
3. Document usage in docstrings
4. Write unit tests if complex logic

### Testing Guidelines

- **Test files mirror source structure**: `tests/test_<module>.py`
- **Test naming**: `test_<feature>_<scenario>()`
- **Use fixtures for common setup** (document processor, sample PDFs)
- **Test both happy path and edge cases**
- **Mock external dependencies** (file I/O, MCP calls)

### Output File Management

**All generated files go in `output/` directory**:
- Vendor manifests: `output/vendor_manifest.json`
- Extraction logs: `output/extraction.log`
- Export CSVs: `output/invoices_YYYYMMDD.csv`
- Test outputs: `output/test_results/`

**Never commit generated files**. Users regenerate them by running scripts.

### Documentation Maintenance

**Keep these files synchronized**:

1. **README.md** - User-facing documentation
   - Installation and quick start
   - Current project status
   - Basic usage examples
   - Troubleshooting common issues

2. **CLAUDE.md** (this file) - Developer guidance for Claude Code
   - Architecture decisions
   - Code organization rules
   - Implementation details
   - Maintenance guidelines

3. **Docstrings** - Inline documentation
   - Module-level: Purpose and exports
   - Class-level: Responsibility and usage
   - Method-level: Parameters, returns, raises

4. **Code Comments** - Explain "why", not "what"
   - Complex algorithms
   - Non-obvious business rules
   - Workarounds for external API quirks

### Version Control Best Practices

**Commit granularity**:
- One logical change per commit
- Separate refactoring from feature work
- Keep test updates with code changes

**Commit messages**:
```
feat: Add Wolverine Printing extractor
fix: Handle missing invoice dates in OMICO parser
refactor: Extract common date parsing to base class
docs: Update vendor list in README
test: Add edge case tests for line item parsing
```

**What to commit**:
- ✅ Source code (`*.py`)
- ✅ Configuration (`config.py`, `.mcp.json`, `pyproject.toml`)
- ✅ Documentation (`*.md`)
- ✅ Tests (`tests/**`)
- ✅ `.gitignore`

**What NOT to commit**:
- ❌ Generated files (`output/`, `*.log`, `*.json` manifests)
- ❌ Virtual environments (`.venv/`)
- ❌ IDE settings (`.vscode/`, `.idea/`)
- ❌ System files (`.DS_Store`)
- ❌ Credentials or API keys

### Dependency Management

**Use UV exclusively** for package management:
```bash
# Add new dependency
uv add package-name

# Add dev dependency
uv add --dev pytest

# Update all dependencies
uv sync --upgrade

# Lock dependencies
uv lock
```

**Key dependencies and their purposes**:
- `docling` - PDF document processing and conversion
- `pydantic` - Data validation and models
- `python-dateutil` - Flexible date parsing
- `tqdm` - Progress bars for batch operations
- `ruff` - Linting and formatting
- `pytest` - Testing framework

### Code Quality Standards

**Before committing, always run**:
```bash
# Format code
uv run ruff format .

# Check for issues
uv run ruff check .

# Run tests
uv run pytest

# Check test coverage
uv run pytest --cov=. --cov-report=term-missing
```

**Ruff configuration** in `pyproject.toml`:
- Line length: 88 (Black-compatible)
- Target Python: 3.11+
- Enable: Import sorting, common error checks
- Disable: Docstring rules for short functions

### Refactoring Guidelines

**When to refactor**:
- Code duplication across 3+ places → Extract to utility
- Function longer than ~50 lines → Break into smaller functions
- Complex conditional logic → Extract to named helper
- Module growing beyond ~500 lines → Split into submodules

**How to refactor safely**:
1. Ensure tests exist and pass
2. Make one refactoring change at a time
3. Run tests after each change
4. Commit working state before next refactoring
5. Update documentation if interfaces change

### Performance Considerations

**For batch processing**:
- Use parallel processing for independent operations
- Process documents in chunks, not all at once
- Log progress with `tqdm` for long operations
- Cache expensive operations (document conversion)

**For extraction**:
- Vendor detection uses first ~3000 chars of markdown
- Full markdown extraction only when needed
- Regex patterns compiled once at module load
- Pydantic validation catches errors early

### Debugging Tips

**Enable debug logging**:
```python
from utils import setup_logging
setup_logging(level="DEBUG")
```

**Inspect document structure**:
```python
doc_key = processor.convert_document(pdf_path)
overview = processor.get_document_overview(doc_key)
print(overview)  # See document structure
```

**Test single invoice**:
```python
# In tests/test_debug.py
extractor = VendorExtractor(processor)
invoice = extractor.extract(doc_key, markdown, filename)
print(invoice.model_dump_json(indent=2))
```

**Common issues**:
- Missing imports → Check `__init__.py` exports
- Pydantic validation errors → Check field types and formats
- Regex not matching → Test pattern in isolation
- Docling conversion errors → Check PDF file integrity, try with different PDF
- Vendor detection failing → Verify directory structure matches `VENDOR_DIRECTORIES` mapping
- Batch processing slow → Reduce `num_workers` or check disk I/O bottleneck

### Future Maintenance Notes

**Completed improvements**:
- ✅ Factory pattern for automatic extractor selection
- ✅ Batch processor with configurable parallelism
- ✅ Direct Docling integration (removed MCP dependency)
- ✅ Confidence scoring framework
- ✅ Directory-based vendor detection

**Planned improvements**:
- CSV exporter with normalization
- Duplicate detection algorithm
- Main CLI interface
- Data validation utilities

**Technical debt to address**:
- Standardize date parsing across extractors
- Improve error messages for extraction failures
- Add performance metrics collection
- Enhance line item extraction accuracy across vendors

**When adding new vendors**:
1. Start with filename-based detection script
2. Manually review sample invoices
3. Identify unique patterns and structure
4. Implement extractor with tests
5. Add to vendor manifest scripts
6. Update documentation
