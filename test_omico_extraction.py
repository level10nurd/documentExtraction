"""Test script for Omico extraction improvements."""

from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

# Import directly to avoid circular import
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Import models directly
import importlib.util

# Load the omico extractor module directly to avoid circular imports
spec = importlib.util.spec_from_file_location(
    "omico_extractor",
    Path(__file__).parent / "extractors" / "omico.py"
)
omico_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(omico_module)
OmicoExtractor = omico_module.OmicoExtractor


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
    """Test Omico extraction on previously failing invoices."""
    processor = SimpleProcessor()
    extractor = OmicoExtractor(processor)

    # Test invoices that were failing
    test_files = [
        "Bill_95781-_95781-.pdf",
        "Bill_95933_95933.pdf",
        "Bill_95954_95954.pdf",
        "Bill_95998_95998.pdf",
        "Bill_96043_96043.pdf",
        "Bill_96386_96386.pdf",
        "Bill_96283_96283.pdf",
    ]

    base_path = Path(
        "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Omico"
    )

    print("Testing Omico extraction improvements:\n")
    print(f"{'File':<35} {'Status':<8} {'Items':<6} {'Total':<12} {'Errors'}")
    print("-" * 100)

    success_count = 0
    for filename in test_files:
        pdf_path = base_path / filename
        if not pdf_path.exists():
            print(f"{filename:<35} {'SKIP':<8} File not found")
            continue

        try:
            doc_key = processor.convert_document(str(pdf_path))
            markdown = processor.get_document_markdown(doc_key)
            invoice = extractor.extract(doc_key, markdown, filename)

            status = "OK" if not invoice.extraction_errors else "ERROR"
            if not invoice.extraction_errors:
                success_count += 1

            items = len(invoice.line_items)
            total = f"${invoice.total:>10.2f}" if invoice.total else "N/A"
            errors = ", ".join(invoice.extraction_errors) if invoice.extraction_errors else ""

            print(f"{filename:<35} {status:<8} {items:<6} {total:<12} {errors}")

        except Exception as e:
            print(f"{filename:<35} {'FAIL':<8} Exception: {str(e)[:40]}")

    print("-" * 100)
    print(f"\nSuccessfully extracted: {success_count}/{len(test_files)}")


if __name__ == "__main__":
    main()
