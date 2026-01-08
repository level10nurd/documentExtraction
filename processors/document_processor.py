"""Document processing and vendor detection using Docling."""

import logging
from pathlib import Path

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from models.vendor import VENDOR_PATTERNS, VendorType

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document conversion and vendor detection using Docling."""

    def __init__(self):
        """Initialize the document processor."""
        self.document_cache = {}

        # Configure pipeline with OCR enabled for scanned images
        # Force full page OCR to handle image-only PDFs like ABox invoices
        from docling.datamodel.pipeline_options import OcrAutoOptions

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = OcrAutoOptions(
            lang=["en"], force_full_page_ocr=True
        )

        self.converter = DocumentConverter(
            format_options={
                "pdf": PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def convert_document(self, pdf_path: str | Path) -> str:
        """
        Convert a PDF document using Docling.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Document key (file path) for accessing the converted document
        """
        pdf_path_str = str(Path(pdf_path).resolve())

        # Check if already converted
        if pdf_path_str in self.document_cache:
            logger.debug(f"Using cached document for {pdf_path_str}")
            return pdf_path_str

        # Convert document using Docling
        logger.info(f"Converting document: {pdf_path_str}")
        try:
            result = self.converter.convert(pdf_path_str)

            # Store the converted document in cache
            self.document_cache[pdf_path_str] = result.document
            logger.debug(f"Document converted successfully: {pdf_path_str}")
            return pdf_path_str

        except Exception as e:
            logger.error(f"Failed to convert document {pdf_path_str}: {e}")
            raise

    def get_document_markdown(self, doc_key: str, max_size: int = 3000) -> str:
        """
        Export document to markdown format for analysis.

        Args:
            doc_key: Document key (file path) from conversion
            max_size: Maximum characters to export (optional, not enforced)

        Returns:
            Markdown representation of document
        """
        try:
            if doc_key not in self.document_cache:
                raise ValueError(f"Document {doc_key} not found in cache")

            document = self.document_cache[doc_key]
            markdown = document.export_to_markdown()

            # Optionally truncate if max_size is specified
            if max_size and len(markdown) > max_size:
                logger.warning(
                    f"Markdown truncated from {len(markdown)} to {max_size} chars"
                )
                markdown = markdown[:max_size]

            return markdown
        except Exception as e:
            logger.error(f"Failed to export document to markdown: {e}")
            raise

    def detect_vendor(
        self, markdown: str = "", filename: str = "", file_path: str = ""
    ) -> tuple[VendorType, float]:
        """
        Detect vendor type from file path, with content patterns as fallback.

        Primary detection uses directory structure (Bills/<vendor>/).
        Falls back to content pattern matching if path detection fails.

        Args:
            markdown: Document content in markdown format (optional)
            filename: Original filename (optional, for logging)
            file_path: Full file path (preferred for vendor detection)

        Returns:
            Tuple of (VendorType, confidence_score)
        """
        from models.vendor import detect_vendor_from_path

        # Primary: detect from file path (highest confidence)
        if file_path:
            vendor = detect_vendor_from_path(file_path)
            if vendor != VendorType.UNKNOWN:
                logger.info(
                    f"Detected vendor from path: {vendor.value} (confidence: 1.0)"
                )
                return vendor, 1.0

        # Fallback: pattern matching in content (lower confidence)
        if markdown:
            vendor_scores = {}

            for vendor_type, patterns in VENDOR_PATTERNS.items():
                matches = 0
                for pattern in patterns:
                    if pattern.search(markdown):
                        matches += 1

                if matches > 0:
                    vendor_scores[vendor_type] = matches

            # Check filename patterns as tertiary signal
            if filename:
                filename_lower = filename.lower()
                if (
                    "vochill" in filename_lower
                    and VendorType.SUNSET_PRESS not in vendor_scores
                ):
                    vendor_scores[VendorType.SUNSET_PRESS] = (
                        vendor_scores.get(VendorType.SUNSET_PRESS, 0) + 0.5
                    )

                if (
                    "reflex" in filename_lower
                    and VendorType.REFLEX_MEDICAL not in vendor_scores
                ):
                    vendor_scores[VendorType.REFLEX_MEDICAL] = (
                        vendor_scores.get(VendorType.REFLEX_MEDICAL, 0) + 0.5
                    )

            # Select vendor with highest score
            if vendor_scores:
                best_vendor = max(vendor_scores, key=vendor_scores.get)
                score = vendor_scores[best_vendor]

                # Calculate confidence (lower than path-based)
                if score >= 3:
                    confidence = 0.9  # High confidence
                elif score >= 2:
                    confidence = 0.7  # Medium confidence
                elif score >= 1:
                    confidence = 0.5  # Low confidence
                else:
                    confidence = 0.3

                logger.info(
                    f"Detected vendor from content: {best_vendor.value} "
                    f"(confidence: {confidence:.2f}, matches: {score})"
                )

                return best_vendor, confidence

        # No detection method succeeded
        logger.warning(
            f"No vendor detection succeeded for {filename or file_path or 'unknown'}"
        )
        return VendorType.UNKNOWN, 0.2

    def get_document_structure(self, doc_key: str) -> str:
        """
        Get document structure overview.

        Args:
            doc_key: Document key (file path) from conversion

        Returns:
            Text representation of document structure
        """
        try:
            if doc_key not in self.document_cache:
                raise ValueError(f"Document {doc_key} not found in cache")

            document = self.document_cache[doc_key]
            # Return basic structure info
            structure_parts = []
            structure_parts.append(f"Document: {doc_key}")
            structure_parts.append(f"Page count: {len(document.pages)}")

            # List main elements
            if hasattr(document, "texts") and document.texts:
                structure_parts.append(f"Text elements: {len(document.texts)}")
            if hasattr(document, "tables") and document.tables:
                structure_parts.append(f"Tables: {len(document.tables)}")

            return "\n".join(structure_parts)
        except Exception as e:
            logger.error(f"Failed to get document structure: {e}")
            raise

    def search_text(self, doc_key: str, search_term: str) -> str:
        """
        Search for text within document.

        Args:
            doc_key: Document key (file path) from conversion
            search_term: Text to search for

        Returns:
            Search results
        """
        try:
            if doc_key not in self.document_cache:
                raise ValueError(f"Document {doc_key} not found in cache")

            # Export to markdown and search within it
            markdown = self.get_document_markdown(doc_key, max_size=None)
            results = []

            for i, line in enumerate(markdown.split("\n"), 1):
                if search_term.lower() in line.lower():
                    results.append(f"Line {i}: {line.strip()}")

            return "\n".join(results) if results else f"No results found for '{search_term}'"
        except Exception as e:
            logger.error(f"Failed to search for text '{search_term}': {e}")
            raise
