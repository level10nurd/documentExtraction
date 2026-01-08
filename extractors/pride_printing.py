"""Pride Printing LLC invoice extractor."""

import logging
import re
from decimal import Decimal

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class PridePrintingExtractor(BaseExtractor):
    """Extractor for Pride Printing LLC invoices."""

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from Pride Printing document.

        Pride Printing invoices have:
        - Header with company info and "INVOICE" title
        - Bill To / Ship To sections
        - Invoice metadata (INVOICE #, DATE, TERMS, TRACKING#, DUE DATE, P.O. NUMBER)
        - Optional PRODUCT section label
        - Table with columns: PRODUCT, DESCRIPTION, QTY, RATE, AMOUNT
        - Totals section with SUBTOTAL, TAX, TOTAL, BALANCEDUE

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.PRIDE_PRINTING, filename)

        try:
            # Extract invoice metadata
            self._extract_invoice_metadata(markdown, invoice)

            # Extract line items from table
            self._extract_line_items(markdown, invoice)

            # Extract totals
            self._extract_totals(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted Pride Printing invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting Pride Printing invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_metadata(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number, date, and PO number from metadata section."""
        # Extract invoice number
        # Pattern: INVOICE #\n\n12981
        inv_match = re.search(r"INVOICE\s*#\s*\n+\s*(\d+)", markdown, re.IGNORECASE)
        if inv_match:
            invoice.invoice_number = self._clean_invoice_number(inv_match.group(1))
        else:
            invoice.add_error("Could not extract invoice number")
            logger.warning(f"Invoice number not found in {invoice.source_file}")

        # Extract date
        # Pattern: DATE\n\n07/27/2024
        date_match = re.search(r"DATE\s*\n+\s*(\d{2}/\d{2}/\d{4})", markdown)
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

        # Extract PO number
        # Pattern: P.O. NUMBER\n\n06112024
        po_match = re.search(r"P\.O\.\s+NUMBER\s*\n+\s*(\S+)", markdown, re.IGNORECASE)
        if po_match:
            invoice.po_number = self._clean_po_number(po_match.group(1))
        else:
            logger.debug(f"PO number not found in {invoice.source_file}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from the main table."""
        # Pride Printing has a markdown table with columns:
        # PRODUCT | DESCRIPTION | (empty) | QTY | RATE | AMOUNT |
        # Note: There's an empty column between DESCRIPTION and QTY

        lines = markdown.split("\n")
        in_table = False
        headers = []

        for i, line in enumerate(lines):
            # Look for the table header line
            if (
                "PRODUCT" in line
                and "DESCRIPTION" in line
                and "QTY" in line
                and "AMOUNT" in line
            ):
                # Parse headers, keeping empty columns
                parts = line.split("|")
                headers = [
                    h.strip() for h in parts[1:-1]
                ]  # Skip first and last empty parts
                in_table = True
                continue

            if in_table:
                # Skip separator line
                if re.match(r"^[\s\|:\-]+$", line):
                    continue

                # Parse data rows
                if "|" in line:
                    parts = line.split("|")
                    values = [
                        v.strip() for v in parts[1:-1]
                    ]  # Skip first and last empty parts

                    # Make sure we have enough values
                    if len(values) < len(headers):
                        continue

                    # Create a dictionary mapping headers to values
                    row = {}
                    for j, header in enumerate(headers):
                        if j < len(values):
                            row[header] = values[j]

                    # Check if this is a data row (not totals or messages)
                    product = row.get("PRODUCT", "").strip()
                    description = row.get("DESCRIPTION", "").strip()

                    # Skip rows with totals or thank you messages
                    if any(
                        keyword in product.upper() or keyword in description.upper()
                        for keyword in [
                            "SUBTOTAL",
                            "TAX",
                            "TOTAL",
                            "BALANCE",
                            "THANK YOU",
                        ]
                    ):
                        continue

                    # Skip empty rows
                    if not product and not description:
                        continue

                    try:
                        # Parse quantity, rate, and amount
                        qty_str = row.get("QTY", "").strip()
                        rate_str = row.get("RATE", "").strip()
                        amount_str = row.get("AMOUNT", "").strip()

                        quantity = (
                            Decimal(qty_str)
                            if qty_str
                            and qty_str.replace(".", "").replace(",", "").isdigit()
                            else None
                        )
                        price_each = self._parse_decimal(rate_str) if rate_str else None
                        amount = (
                            self._parse_decimal(amount_str)
                            if amount_str
                            else Decimal("0")
                        )

                        # Create line item
                        item = LineItem(
                            item_code=product,
                            description=description,
                            quantity=quantity,
                            price_each=price_each,
                            amount=amount,
                        )
                        invoice.line_items.append(item)

                    except Exception as e:
                        logger.warning(
                            f"Failed to parse line item '{product}' in {invoice.source_file}: {e}"
                        )
                        invoice.add_error(f"Failed to parse line item: {product}")

                elif not line.strip():
                    # Empty line - end of table
                    break

    def _extract_totals(self, markdown: str, invoice: Invoice) -> None:
        """Extract subtotal, tax, and total amounts."""
        # Look for BALANCEDUE (final total)
        # Pattern: | BALANCEDUE | | | $406.25 |
        balance_match = re.search(
            r"BALANCEDUE[^\$]*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if balance_match:
            invoice.total = self._parse_decimal(balance_match.group(1))
        else:
            # Try to find TOTAL in the table
            total_match = re.search(
                r"\|\s*TOTAL\s*\|[^\|]*\|[^\|]*\|[^\$]*\$?\s*([\d,]+\.?\d*)\s*\|",
                markdown,
                re.IGNORECASE,
            )
            if total_match:
                invoice.total = self._parse_decimal(total_match.group(1))
            else:
                invoice.add_error("Could not extract total amount")
                logger.warning(f"Total not found in {invoice.source_file}")

        # Extract subtotal
        # Pattern: | SUBTOTAL | | | 406.25 |
        subtotal_match = re.search(
            r"\|\s*SUBTOTAL\s*\|[^\|]*\|[^\|]*\|\s*([\d,]+\.?\d*)\s*\|",
            markdown,
            re.IGNORECASE,
        )
        if subtotal_match:
            invoice.subtotal = self._parse_decimal(subtotal_match.group(1))

        # Extract sales tax
        # Pattern: | TAX | | | 0.00 |
        tax_match = re.search(
            r"\|\s*TAX\s*\|[^\|]*\|[^\|]*\|\s*([\d,]+\.?\d*)\s*\|",
            markdown,
            re.IGNORECASE,
        )
        if tax_match:
            invoice.sales_tax = self._parse_decimal(tax_match.group(1))
        else:
            # Default to 0 if not found
            invoice.sales_tax = Decimal("0.00")
