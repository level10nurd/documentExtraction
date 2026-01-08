"""ABox invoice extractor.

This extractor handles ABox invoices, which are scanned images converted via OCR.

Key Challenges:
- 5 of 6 sample invoices have complete OCR failure (only image placeholders)
- 1 of 6 invoices has successful OCR with table-based format
- Expected confidence: ~0.20 overall (0.90 for successful OCR, 0.20 for failures)

Extraction Strategy:
- Table-based parsing for invoice header (| Number | Date |)
- 9-column line items table with UOM-based price conversion
- Fallback patterns for legacy formats
"""

import logging
import re
from decimal import Decimal

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class ABoxExtractor(BaseExtractor):
    """Extractor for ABox invoices.

    ABox invoices are scanned images processed with OCR. The extraction quality
    depends heavily on OCR success:

    - Successful OCR: 0.90+ confidence with full data extraction
    - Failed OCR: 0.20 confidence (only basic metadata from filename)

    The extractor uses table-based pattern matching for the actual invoice format
    discovered through diagnostic analysis, with fallback patterns for edge cases.

    Note: Improving OCR preprocessing is out of scope and deferred to a separate task.
    """

    def __init__(self, doc_processor):
        """Initialize with vendor type."""
        super().__init__(doc_processor, vendor_type=VendorType.ABOX)

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from ABox document.

        Actual Invoice Format (from diagnostic analysis):
        ABox invoices are scanned images with OCR text. Format varies by OCR quality:

        **Successful OCR (Bill_201038):**
        - Invoice header table:
          | Number | Date       |
          |--------|------------|
          | 201038 | 06/20/2025 |

        - Line items table with columns:
          Line #, Order No., Shipper #, PO/Rel, Customer Part #, Count, Price, UOM, Amount
          (Note: "Count" not "Qty Shipped", prices per UOM shown in separate column)

        - PO Number appears in line items "PO/Rel" column (e.g., "1039, 1039")

        - Totals as plain text (not "This Amount =>"):
          Sub Total
          $15,366.84
          Tax
          $0.00
          Total
          $15,366.84

        **Failed OCR (Bill_100676):**
        - Only image placeholders, no text extracted
        - OCR failure due to poor scan quality

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
        # Pattern: Invoice header table with | Number | Date | format
        # Example:
        # | Number | Date       |
        # |--------|------------|
        # | 201038 | 06/20/2025 |

        # Try table-based extraction (actual format)
        inv_match = re.search(
            r"\|\s*Number\s*\|[^\|]*\|\s*\n\s*\|[-\s|]+\|\s*\n\s*\|\s*(\d+)\s*\|",
            markdown,
            re.IGNORECASE | re.MULTILINE
        )

        if inv_match:
            invoice.invoice_number = inv_match.group(1).strip()
            logger.debug(f"Extracted invoice number: {invoice.invoice_number}")
            return

        # Fallback: Try legacy "Invoice No:" pattern
        inv_match = re.search(
            r"Invoice\s+No[.:]?\s*(\d+)", markdown, re.IGNORECASE | re.MULTILINE
        )

        if inv_match:
            invoice.invoice_number = inv_match.group(1).strip()
            logger.debug(f"Extracted invoice number (fallback): {invoice.invoice_number}")
        else:
            invoice.add_error("Invoice number not found")

    def _extract_invoice_date(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice date from markdown."""
        # Pattern: Invoice header table with | Number | Date | format
        # Example:
        # | Number | Date       |
        # |--------|------------|
        # | 201038 | 06/20/2025 |

        # Try table-based extraction (actual format) - date is in second column
        date_match = re.search(
            r"\|\s*Number\s*\|\s*Date\s*\|\s*\n\s*\|[-\s|]+\|\s*\n\s*\|\s*\d+\s*\|\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*\|",
            markdown,
            re.IGNORECASE | re.MULTILINE,
        )

        if date_match:
            date_str = date_match.group(1)
            try:
                from dateutil.parser import parse

                invoice.invoice_date = parse(date_str).date()
                logger.debug(f"Extracted invoice date: {invoice.invoice_date}")
                return
            except Exception as e:
                invoice.add_error(f"Failed to parse date: {e}")
                return

        # Fallback: Try legacy "Invoice Date:" pattern
        date_match = re.search(
            r"Invoice\s+Date[.:]?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
            markdown,
            re.IGNORECASE | re.MULTILINE,
        )

        if date_match:
            date_str = date_match.group(1)
            try:
                from dateutil.parser import parse

                invoice.invoice_date = parse(date_str).date()
                logger.debug(f"Extracted invoice date (fallback): {invoice.invoice_date}")
            except Exception as e:
                invoice.add_error(f"Failed to parse date: {e}")
        else:
            invoice.add_error("Invoice date not found")

    def _extract_po_number(self, markdown: str, invoice: Invoice) -> None:
        """Extract PO number from markdown."""
        # Pattern: PO number appears in line items table "PO/Rel" column
        # Example: | 1039, 1039 | or | 1039 |
        # Extract first PO number from the PO/Rel column

        # Try to find PO/Rel column in line items table
        po_match = re.search(
            r"\|\s*PO/Rel\s*\|.*?\n\s*\|[-\s|]+\|\s*\n\s*(?:\|[^\|]*\|){3}\s*\|\s*(\d+)",
            markdown,
            re.IGNORECASE | re.MULTILINE,
        )

        if po_match:
            invoice.po_number = po_match.group(1).strip()
            logger.debug(f"Extracted PO number from table: {invoice.po_number}")
            return

        # Fallback: Try legacy "Customer P.O. No." pattern
        po_match = re.search(
            r"Customer\s+P\.?O\.?\s+No\.?\s*[:\|]?\s*(\d+)",
            markdown,
            re.IGNORECASE | re.MULTILINE,
        )

        if po_match:
            invoice.po_number = po_match.group(1).strip()
            logger.debug(f"Extracted PO number (fallback): {invoice.po_number}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from table in markdown."""
        # Actual table format (from diagnostic analysis):
        # Line # | Order No. | Shipper # | PO/Rel | Customer Part # | Count | Price | UOM | Amount
        #      1 |   1235060 |     60995 |   1039 |                 | 5,250 | $1394.72 | 1000 | $7322.28
        #
        # Key details:
        # - "Count" (with commas), not "Qty Shipped"
        # - "Price" (with $), not "Price/Per"
        # - "UOM" column separate (1000 = per 1000 units, empty = per unit)
        # - Customer Part # can be empty

        # Pattern to match the table structure (9 columns total)
        # Flexible whitespace between columns
        # Handle prices and amounts with or without decimals ($1394.72 or $360)
        # Handle empty UOM column
        table_pattern = r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([\d,]+)\s*\|\s*\$?([\d,]+(?:\.\d{1,2})?)\s*\|\s*(\d*)\s*\|\s*\$?([\d,]+(?:\.\d{2})?)\s*\|"

        matches = re.finditer(table_pattern, markdown, re.MULTILINE)

        for match in matches:
            try:
                line_num = match.group(1).strip()
                order_no = match.group(2).strip()
                shipper_no = match.group(3).strip()
                po_rel = match.group(4).strip()
                customer_part = match.group(5).strip()
                count_str = match.group(6).replace(",", "").strip()
                price_str = match.group(7).replace(",", "").strip()
                uom_str = match.group(8).strip()
                amount_str = match.group(9).replace(",", "").strip()

                # Use customer part # as description if available, otherwise use order number
                description = customer_part if customer_part else f"Order {order_no}"
                description = " ".join(description.split())  # Clean whitespace

                # Parse quantity (Count column)
                quantity = Decimal(count_str)

                # Parse price - check UOM to determine if per unit or per 1000
                price = Decimal(price_str)
                if uom_str and int(uom_str) == 1000:
                    # Price is per 1000 units, convert to per unit
                    price_each = price / Decimal("1000")
                else:
                    # Price is per unit
                    price_each = price

                # Parse amount
                amount = Decimal(amount_str)

                line_item = LineItem(
                    quantity=quantity,
                    item_code=order_no,
                    description=description,
                    price_each=price_each,
                    amount=amount,
                )

                invoice.line_items.append(line_item)
                logger.debug(f"Extracted line item: {order_no} - {description}")

            except (ValueError, IndexError, Exception) as e:
                logger.warning(f"Failed to parse line item: {e}")
                continue

        if not invoice.line_items:
            invoice.add_error("No line items found")

    def _extract_total(self, markdown: str, invoice: Invoice) -> None:
        """Extract total amount from markdown."""
        # Actual format (from diagnostic analysis):
        # Total
        # $15,366.84
        #
        # Look for "Total" followed by dollar amount on next line or same line

        total_patterns = [
            # Pattern 1: "Total" with amount on next line (actual format)
            r"Total\s*\n\s*\$?([\d,]+\.\d{2})",
            # Pattern 2: "Total" with amount on same line
            r"Total\s*\$?([\d,]+\.\d{2})",
            # Pattern 3: Legacy "This Amount =>" pattern (fallback)
            r"This\s+Amount\s*=>?\s*\$?([\d,]+\.\d{2})",
            # Pattern 4: "Please Pay" pattern (fallback)
            r"Please\s+Pay.*?\$?([\d,]+\.\d{2})",
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
