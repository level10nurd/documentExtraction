"""Diagnostic script for ABox invoice extraction analysis."""

from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption


class SimpleProcessor:
    """Simple processor for diagnostic analysis."""

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
    """Extract and analyze markdown from sample ABox invoices."""
    processor = SimpleProcessor()

    # Target sample invoices for diagnostic analysis
    test_files = [
        "Bill_100676_doc02542020241023083923.pdf",
        "Bill_201038_201038_VOCHILL.pdf",
    ]

    base_path = Path(
        "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/ABox"
    )
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    print("ABox Invoice Diagnostic Analysis:\n")
    print(f"{'Invoice File':<45} {'Markdown Length':<15} {'Status'}")
    print("-" * 100)

    for filename in test_files:
        pdf_path = base_path / filename
        if not pdf_path.exists():
            print(f"{filename:<45} {'N/A':<15} File not found")
            continue

        try:
            # Convert document and extract markdown
            doc_key = processor.convert_document(str(pdf_path))
            markdown = processor.get_document_markdown(doc_key)

            # Save markdown to file for manual inspection
            output_filename = f"abox_diagnostic_{filename.replace('.pdf', '.md')}"
            output_path = output_dir / output_filename
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            # Print summary
            markdown_len = len(markdown)
            print(f"{filename:<45} {markdown_len:<15} Saved to {output_filename}")

            # Print first 500 characters preview
            print(f"\n  Preview (first 500 chars):")
            print(f"  {markdown[:500]}")
            print()

        except Exception as e:
            print(f"{filename:<45} {'N/A':<15} Exception: {str(e)}")

    print("-" * 100)
    print(f"\nMarkdown files saved to: {output_dir.resolve()}")
    print("Next steps:")
    print("1. Review markdown files to identify actual invoice structure")
    print("2. Compare with expected patterns in extractors/abox.py")
    print("3. Document findings for pattern fixes")


if __name__ == "__main__":
    main()
