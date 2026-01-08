"""Test script for ABox extraction improvements."""

from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

# Import directly to avoid circular import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import models directly using importlib to avoid circular imports
import importlib.util

# Load the abox extractor module directly to avoid circular imports
spec = importlib.util.spec_from_file_location(
    "abox_extractor",
    Path(__file__).parent.parent / "extractors" / "abox.py"
)
abox_module = importlib.util.module_from_spec(spec)

# Load base extractor first
base_spec = importlib.util.spec_from_file_location(
    "base_extractor",
    Path(__file__).parent.parent / "extractors" / "base.py"
)
base_module = importlib.util.module_from_spec(base_spec)
sys.modules['extractors.base'] = base_module
base_spec.loader.exec_module(base_module)

# Now load abox
sys.modules['extractors.abox'] = abox_module
spec.loader.exec_module(abox_module)
ABoxExtractor = abox_module.ABoxExtractor


class SimpleProcessor:
    """Simple processor for testing."""

    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        self.converter = DocumentConverter(
            format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
        )
        self.document_cache = {}

    def convert_document(self, pdf_path: str) -> str:
        pdf_path_str = str(Path(pdf_path).resolve())
        if pdf_path_str in self.document_cache:
            return pdf_path_str

        result = self.converter.convert(pdf_path_str)
        self.document_cache[pdf_path_str] = result.document
        return pdf_path_str

    def get_document_markdown(self, doc_key: str, max_size: int | None = None) -> str:
        doc = self.document_cache[doc_key]
        markdown = doc.export_to_markdown()
        if max_size and len(markdown) > max_size:
            return markdown[:max_size]
        return markdown


def main():
    """Test ABox extraction on all 6 invoices."""
    processor = SimpleProcessor()
    extractor = ABoxExtractor(processor)

    # Test all 6 ABox invoices
    test_files = [
        "Bill_100654_doc02531620241018085046.pdf",
        "Bill_100676_doc02542020241023083923.pdf",
        "Bill_201038_201038_VOCHILL.pdf",
        "Bill_202052_doc03384120251007105152.pdf",
        "Bill_202192_doc03439820251022094839.pdf",
        "Bill_202377_doc03542420251120111021.pdf",
    ]

    base_path = Path(
        "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/ABox"
    )

    print("Testing ABox extraction improvements:\n")
    print(f"{'File':<50} {'Conf':<6} {'Items':<6} {'Total':<12} {'Errors'}")
    print("-" * 120)

    success_count = 0
    total_confidence = 0.0
    results = []

    for filename in test_files:
        pdf_path = base_path / filename
        if not pdf_path.exists():
            print(f"{filename:<50} {'SKIP':<6} File not found")
            continue

        try:
            doc_key = processor.convert_document(str(pdf_path))
            markdown = processor.get_document_markdown(doc_key)
            invoice = extractor.extract(doc_key, markdown, filename)

            confidence = invoice.extraction_confidence
            total_confidence += confidence

            status = "OK" if confidence >= 0.80 else "LOW"
            if confidence >= 0.80:
                success_count += 1

            items = len(invoice.line_items)
            total = f"${invoice.total:>10.2f}" if invoice.total else "N/A"
            errors = ", ".join(invoice.extraction_errors) if invoice.extraction_errors else ""

            results.append({
                'file': filename,
                'confidence': confidence,
                'status': status,
                'items': items,
                'total': invoice.total,
                'errors': errors
            })

            print(f"{filename:<50} {confidence:.2f}  {items:<6} {total:<12} {errors[:40]}")

        except Exception as e:
            print(f"{filename:<50} {'FAIL':<6} Exception: {str(e)[:60]}")
            results.append({
                'file': filename,
                'confidence': 0.0,
                'status': 'FAIL',
                'items': 0,
                'total': None,
                'errors': str(e)
            })

    print("-" * 120)
    avg_confidence = total_confidence / len(test_files) if test_files else 0
    print(f"\nResults:")
    print(f"  Successfully extracted (≥0.80 confidence): {success_count}/{len(test_files)}")
    print(f"  Average confidence: {avg_confidence:.2f}")
    print(f"  Target: ≥0.80 confidence on at least 5/6 invoices")
    print(f"  Status: {'PASS ✓' if success_count >= 5 and avg_confidence >= 0.85 else 'NEEDS IMPROVEMENT'}")


if __name__ == "__main__":
    main()
