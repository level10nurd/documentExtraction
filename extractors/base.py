"""Base extractor class for vendor-specific invoice extraction."""

import logging
import re
from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Optional

from models.invoice import Invoice
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Abstract base class for vendor-specific extractors."""

    def __init__(self, doc_processor, vendor_type: VendorType = None):
        """
        Initialize the extractor.

        Args:
            doc_processor: DocumentProcessor instance for MCP interactions
            vendor_type: VendorType for this extractor (optional)
        """
        self.doc_processor = doc_processor
        self.vendor_type = vendor_type

    def get_vendor_directory(self) -> Path:
        """
        Get the directory path for this extractor's vendor.

        Returns:
            Path to vendor's invoice directory

        Raises:
            ValueError: If vendor_type is not set or has no directory mapping
        """
        if not self.vendor_type:
            raise ValueError("vendor_type not set for this extractor")

        from config import Config

        return Config.get_vendor_directory(self.vendor_type)

    def list_vendor_invoices(self, pattern: str = "*.pdf") -> list[Path]:
        """
        List all invoice files for this vendor.

        Args:
            pattern: Glob pattern for matching files (default: "*.pdf")

        Returns:
            List of Path objects for matching invoice files
        """
        vendor_dir = self.get_vendor_directory()
        if not vendor_dir.exists():
            logger.warning(f"Vendor directory does not exist: {vendor_dir}")
            return []

        return sorted(vendor_dir.glob(pattern))

    @abstractmethod
    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from Docling document.

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        pass

    def _create_base_invoice(self, vendor: VendorType, filename: str) -> Invoice:
        """
        Create a base Invoice object with default values.

        Args:
            vendor: Vendor type
            filename: Source filename

        Returns:
            Invoice object with defaults
        """
        return Invoice(
            vendor=vendor,
            invoice_number="",  # Must be filled by extractor
            total=Decimal("0"),  # Must be filled by extractor
            source_file=Path(filename).name,
        )

    def _extract_regex(self, text: str, pattern: str, group: int = 1) -> Optional[str]:
        """
        Extract text using regex pattern.

        Args:
            text: Text to search
            pattern: Regex pattern
            group: Capture group to return (default: 1)

        Returns:
            Matched text or None
        """
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match and len(match.groups()) >= group:
            return match.group(group).strip()
        return None

    def _parse_decimal(self, value: str | None) -> Optional[Decimal]:
        """
        Parse a string to Decimal, handling currency formatting.

        Args:
            value: String value to parse

        Returns:
            Decimal value or None if parsing fails
        """
        if not value:
            return None

        try:
            # Remove currency symbols and commas
            cleaned = value.replace("$", "").replace(",", "").strip()
            if not cleaned:
                return None
            return Decimal(cleaned)
        except Exception as e:
            logger.warning(f"Failed to parse decimal '{value}': {e}")
            return None

    def _search_and_extract(
        self, doc_key: str, search_term: str, pattern: str | None = None
    ) -> Optional[str]:
        """
        Search for text in document and optionally extract with regex.

        Args:
            doc_key: Document key
            search_term: Term to search for
            pattern: Optional regex pattern to extract from results

        Returns:
            Extracted text or None
        """
        try:
            results = self.doc_processor.search_text(doc_key, search_term)

            if not results:
                return None

            if pattern:
                return self._extract_regex(results, pattern)

            return results

        except Exception as e:
            logger.warning(f"Search failed for '{search_term}': {e}")
            return None

    def _extract_table_data(self, markdown: str, table_marker: str) -> list[dict]:
        """
        Extract table data from markdown.

        Args:
            markdown: Markdown content containing tables
            table_marker: Text that identifies the relevant table

        Returns:
            List of dictionaries representing table rows
        """
        # Simple table extraction from markdown
        # Look for tables after the marker
        lines = markdown.split("\n")
        table_data = []

        in_target_table = False
        headers = []

        for i, line in enumerate(lines):
            # Check if we've found our table marker
            if table_marker.lower() in line.lower():
                in_target_table = True
                continue

            if in_target_table:
                # Check for table header (line with | separators)
                if "|" in line and not headers:
                    # Parse headers
                    headers = [h.strip() for h in line.split("|") if h.strip()]
                    continue

                # Skip separator line (|---|---|)
                if re.match(r"^[\s\|:\-]+$", line):
                    continue

                # Parse data rows
                if "|" in line and headers:
                    values = [v.strip() for v in line.split("|") if v.strip()]
                    if len(values) == len(headers):
                        row = dict(zip(headers, values))
                        table_data.append(row)
                elif table_data:
                    # End of table reached
                    break

        return table_data

    def _clean_invoice_number(self, value: str | None) -> str:
        """
        Clean and normalize invoice number.

        Args:
            value: Raw invoice number string

        Returns:
            Cleaned invoice number
        """
        if not value:
            return ""

        # Remove common prefixes and clean
        cleaned = value.replace("Invoice #:", "").replace("#", "").strip()
        return cleaned

    def _clean_po_number(self, value: str | None) -> Optional[str]:
        """
        Clean and normalize PO number.

        Args:
            value: Raw PO number string

        Returns:
            Cleaned PO number or None
        """
        if not value:
            return None

        # Remove common prefixes
        cleaned = (
            value.replace("PO #:", "")
            .replace("P.O. Number:", "")
            .replace("PO:", "")
            .strip()
        )

        if not cleaned or cleaned.lower() in ["n/a", "none", ""]:
            return None

        return cleaned
