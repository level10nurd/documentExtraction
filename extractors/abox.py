"""ABox invoice extractor."""

import logging
import re
from decimal import Decimal

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class ABoxExtractor(BaseExtractor):
    """Extractor for ABox invoices."""

    def __init__(self, doc_processor):
        """Initialize with vendor type."""
        super().__init__(doc_processor, vendor_type=VendorType.ABOX)

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from ABox document.

        ABox invoices are scanned images with OCR text containing:
        - Invoice No: XXXXXX
        - Invoice Date: MM/DD/YY
        - Customer P.O. No: XXXX
        - Line items in a table
        - Total amount

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.ABOX, filename)

        try:
            # Extract invoice number
            self._extract_invoice_number(markdown, invoice)

            # Extract invoice date
            self._extract_invoice_date(markdown, invoice)

            # Extract PO number
            self._extract_po_number(markdown, invoice)

            # Extract line items
            self._extract_line_items(markdown, invoice)

            # Extract total
            self._extract_total(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(f"Successfully extracted ABox invoice {invoice.invoice_number}")

        except Exception as e:
            logger.error(f"Error extracting ABox invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_number(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number from markdown."""
        # Pattern: "Invoice No: 100676" or "Invoice No:\n100676"
        inv_match = re.search(
            r"Invoice\s+No[:\s]+(\d+)", markdown, re.IGNORECASE | re.MULTILINE
        )

        if inv_match:
            invoice.invoice_number = inv_match.group(1).strip()
            logger.debug(f"Extracted invoice number: {invoice.invoice_number}")
        else:
            invoice.add_error("Invoice number not found")

    def _extract_invoice_date(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice date from markdown."""
        # Pattern: "Invoice Date: 10/23/24" or "Invoice Date:\n10/23/24"
        date_match = re.search(
            r"Invoice\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})",
            markdown,
            re.IGNORECASE | re.MULTILINE,
        )

        if date_match:
            date_str = date_match.group(1)
            try:
                from dateutil.parser import parse

                invoice.invoice_date = parse(date_str).date()
                logger.debug(f"Extracted invoice date: {invoice.invoice_date}")
            except Exception as e:
                invoice.add_error(f"Failed to parse date: {e}")
        else:
            invoice.add_error("Invoice date not found")

    def _extract_po_number(self, markdown: str, invoice: Invoice) -> None:
        """Extract PO number from markdown."""
        # Pattern: Look for Customer P.O. No. in table or as standalone field
        # Could be in format "Customer P.O. No. | 1027" or just "1027" in table
        po_match = re.search(
            r"Customer\s+P\.?O\.?\s+No\.?\s*[:\|]?\s*(\d+)",
            markdown,
            re.IGNORECASE | re.MULTILINE,
        )

        if po_match:
            invoice.po_number = po_match.group(1).strip()
            logger.debug(f"Extracted PO number: {invoice.po_number}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from table in markdown."""
        # ABox invoices have a main table with columns:
        # Qty Ord. | Order # | Order No./ Description | Customer P.O. No. | Qty Shipped | P/C | Price/Per | Amount
        # But OCR may merge/split columns, so be flexible

        # Look for a row with: large qty number | item number | description | PO | qty shipped | price | amount
        # Example: | 11000 | 218850 | STEMMED BOX LARGE INSERT... | 1027 | 9600 EA C | $862.95 / M | $8,284.32 |

        # More flexible pattern that handles variations in spacing and column merging
        table_pattern = r"\|\s*(\d{4,})\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s+(?:EA|ea)\s*[A-Z]?\s*\|\s*\$?([\d,]+\.?\d*)\s*/\s*[MmKk]\s*\|\s*\$?([\d,]+\.\d{2})\s*\|"

        matches = re.finditer(table_pattern, markdown, re.MULTILINE)

        for match in matches:
            try:
                qty_ordered = match.group(1).strip()
                item_number = match.group(2).strip()
                description = match.group(3).strip()
                po_number = match.group(4).strip()
                qty_shipped = match.group(5).strip()
                price_str = match.group(6).replace(",", "")
                amount_str = match.group(7).replace(",", "")

                # Clean up description - remove extra whitespace
                description = " ".join(description.split())

                # Use shipped quantity as the line quantity
                quantity = int(qty_shipped)
                price_each = Decimal(price_str) / Decimal("1000")  # Price is per M (thousand)
                amount = Decimal(amount_str)

                line_item = LineItem(
                    quantity=quantity,
                    item_code=item_number,
                    description=description,
                    price_each=price_each,
                    amount=amount,
                )

                invoice.line_items.append(line_item)
                logger.debug(f"Extracted line item: {item_number} - {description}")

                # Also extract PO number from the table if not already found
                if not invoice.po_number and po_number:
                    invoice.po_number = po_number
                    logger.debug(f"Extracted PO number from line item: {po_number}")

            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse line item: {e}")
                continue

        if not invoice.line_items:
            invoice.add_error("No line items found")

    def _extract_total(self, markdown: str, invoice: Invoice) -> None:
        """Extract total amount from markdown."""
        # Pattern: "This Amount => $8,284.32" or final total in table
        # Look for amounts near "This Amount", "Please Pay", or at the end

        total_patterns = [
            r"This\s+Amount\s*=>?\s*\$?([\d,]+\.\d{2})",
            r"Please\s+Pay.*?\$?([\d,]+\.\d{2})",
            r"Total.*?\$?([\d,]+\.\d{2})",
        ]

        for pattern in total_patterns:
            total_match = re.search(pattern, markdown, re.IGNORECASE | re.MULTILINE)
            if total_match:
                total_str = total_match.group(1).replace(",", "")
                invoice.total = Decimal(total_str)
                logger.debug(f"Extracted total: {invoice.total}")
                return

        # If no total found, sum line items
        if invoice.line_items:
            invoice.total = sum(item.amount for item in invoice.line_items)
            logger.debug(f"Calculated total from line items: {invoice.total}")
        else:
            invoice.add_error("Total amount not found")
