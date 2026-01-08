"""AMANDA-ANDREWS PERSONNEL CORP invoice extractor."""

import logging
import re
from decimal import Decimal

from extractors.base import BaseExtractor
from models.invoice import Invoice
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class AmandaAndrewsExtractor(BaseExtractor):
    """Extractor for AMANDA-ANDREWS PERSONNEL CORP (dba VIP STAFFING) invoices."""

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from Amanda Andrews document.

        Amanda Andrews invoices are staffing/personnel invoices with:
        - Simple format with invoice number, date, and total
        - Account number included
        - No detailed line items (staffing hours summary only)
        - Single total amount without subtotal/tax breakdown

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.AMANDA_ANDREWS, filename)

        try:
            # Extract invoice number and date
            self._extract_invoice_header(markdown, invoice)

            # Extract total amount
            self._extract_total(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted Amanda Andrews invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting Amanda Andrews invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_header(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number and date from header section."""
        # Pattern for invoice number
        # Format: "73018 INVOICE #" or just the number near "INVOICE #"
        inv_match = re.search(
            r"(\d{5,})\s+INVOICE\s+#", markdown, re.IGNORECASE | re.MULTILINE
        )

        if inv_match:
            invoice.invoice_number = inv_match.group(1).strip()
        else:
            invoice.add_error("Could not extract invoice number")
            logger.warning(f"Invoice number not found in {invoice.source_file}")

        # Pattern for invoice date
        # Format: "08/30/2024 INVOICE DATE"
        date_match = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4})\s+INVOICE\s+DATE",
            markdown,
            re.IGNORECASE | re.MULTILINE,
        )

        if date_match:
            try:
                from dateutil.parser import parse

                invoice.invoice_date = parse(date_match.group(1)).date()
            except Exception as e:
                invoice.add_error(f"Failed to parse date: {e}")
                logger.warning(f"Could not parse date in {invoice.source_file}")
        else:
            invoice.add_error("Could not extract invoice date")
            logger.warning(f"Invoice date not found in {invoice.source_file}")

    def _extract_total(self, markdown: str, invoice: Invoice) -> None:
        """Extract total amount from invoice."""
        # Pattern for amount due
        # Format: "$915.98 AMOUNT DUE" or "AMOUNT DUE" followed by amount
        amount_match = re.search(
            r"\$\s*([\d,]+\.?\d*)\s+AMOUNT\s+DUE",
            markdown,
            re.IGNORECASE | re.MULTILINE,
        )

        if not amount_match:
            # Try alternative pattern: "AMOUNT DUE" on one line, amount on another
            amount_match = re.search(
                r"AMOUNT\s+DUE\s+\$\s*([\d,]+\.?\d*)",
                markdown,
                re.IGNORECASE | re.MULTILINE,
            )

        if not amount_match:
            # Try finding it in the payment stub table
            amount_match = re.search(
                r"AMOUNTGLYPH.*DUE.*?\$\s*([\d,]+\.?\d*)",
                markdown,
                re.IGNORECASE | re.DOTALL,
            )

        if amount_match:
            invoice.total = self._parse_decimal(amount_match.group(1))
            # For Amanda Andrews, there's no separate subtotal/tax breakdown
            invoice.subtotal = invoice.total
            invoice.sales_tax = Decimal("0.00")
        else:
            invoice.add_error("Could not extract total amount")
            logger.warning(f"Total amount not found in {invoice.source_file}")

        # Try to get Invoice Total if available
        total_match = re.search(
            r"Invoice\s+Total:\s*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if total_match and not amount_match:
            invoice.total = self._parse_decimal(total_match.group(1))
            invoice.subtotal = invoice.total
            invoice.sales_tax = Decimal("0.00")
