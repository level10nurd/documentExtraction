"""Wolverine Printing invoice extractor."""

import logging
import re
from decimal import Decimal
from typing import Optional

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class WolverinePrintingExtractor(BaseExtractor):
    """Extractor for Wolverine Printing invoices."""

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from Wolverine Printing document.

        Wolverine Printing invoices have:
        - Header with address: 315 GRANDVILLE AVE SW | GRAND RAPIDS, MI
        - Main table with columns: Quantity Ordered, Quantity Shipped,
          Order Number or Job, Description, Unit Price, Unit of Measure, Amount
        - Footer metadata: Invoice Number, Invoice Date, Due Date,
          Salesperson, Purchase Order
        - Totals embedded in table: Sales, Non-Taxable, Freight, Total

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.WOLVERINE_PRINTING, filename)

        try:
            # Extract invoice metadata (number, date, PO)
            self._extract_invoice_metadata(markdown, invoice)

            # Extract line items from main table
            self._extract_line_items(markdown, invoice)

            # Extract totals from table footer
            self._extract_totals(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted Wolverine Printing invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting Wolverine Printing invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_metadata(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number, date, and PO from footer metadata."""
        # Extract invoice number
        # Pattern: Invoice Number: 110458
        inv_match = re.search(r"Invoice\s+Number:\s*(\d+)", markdown, re.IGNORECASE)
        if inv_match:
            invoice.invoice_number = self._clean_invoice_number(inv_match.group(1))
        else:
            invoice.add_error("Could not extract invoice number")
            logger.warning(f"Invoice number not found in {invoice.source_file}")

        # Extract invoice date
        # Pattern: Invoice Date: 08/01/24
        date_match = re.search(
            r"Invoice\s+Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", markdown, re.IGNORECASE
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

        # Extract PO number
        # Pattern: Purchase Order: 1017
        po_match = re.search(r"Purchase\s+Order:\s*(\S+)", markdown, re.IGNORECASE)
        if po_match:
            invoice.po_number = self._clean_po_number(po_match.group(1))
        else:
            logger.debug(f"PO number not found in {invoice.source_file}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from the main table."""
        # Find the table with line items
        # Headers: Quantity Ordered | Quantity Shipped | Order Number or Job | Description | Unit Price | Unit of Measure | Amount

        lines = markdown.split("\n")
        in_items_table = False
        headers = []

        for i, line in enumerate(lines):
            # Look for table header
            if "Quantity Ordered" in line and "Description" in line and "|" in line:
                in_items_table = True
                # Parse headers
                headers = [h.strip() for h in line.split("|") if h.strip()]
                continue

            if in_items_table:
                # Skip separator line
                if re.match(r"^[\s\|:\-]+$", line):
                    continue

                # Check if we've hit the totals section (Sales:, Non-Taxable:, etc.)
                if "Sales:" in line or "Non-Taxable:" in line or "Total:" in line:
                    break

                # Check for end of table (Terms:, Invoice, etc.)
                if "Terms:" in line or "Invoice Number:" in line:
                    break

                # Parse data row
                if "|" in line:
                    # Check if this is an actual item row (has quantity and amount)
                    parts = [p.strip() for p in line.split("|") if p.strip()]

                    # Filter out rows that are clearly not items
                    # Skip empty rows or rows with only labels
                    if len(parts) < 3:
                        continue

                    # Skip freight/shipping rows
                    line_text = " ".join(parts).lower()
                    if any(keyword in line_text for keyword in ["ups to", "freight", "shipped =", "net freight"]):
                        logger.debug(f"Skipping freight/shipping row: {line_text[:50]}")
                        continue

                    # Try to parse as an item
                    item = self._parse_item_row(parts, headers)
                    if item and item.amount and item.amount > 0:
                        invoice.line_items.append(item)

    def _parse_item_row(
        self, parts: list[str], headers: list[str]
    ) -> Optional[LineItem]:
        """
        Parse a single item row from the table.

        Args:
            parts: Row data split by |
            headers: Table headers

        Returns:
            LineItem object or None if parsing fails
        """
        try:
            # Map parts to a dictionary based on position
            # Expected columns: Quantity Ordered, Quantity Shipped, Order Number or Job,
            #                   Description, Unit Price, Unit of Measure, Amount

            # Handle variable column counts
            if len(parts) < 4:
                return None

            # Try to identify columns by content patterns
            quantity = None
            description = ""
            price_each = None
            amount = None
            item_code = None

            # First, try to match parts to expected positions if we have headers
            if headers and len(headers) >= 5:
                # Try positional mapping based on header count
                # Typical format: Qty Ordered | Qty Shipped | Order# | Description | Unit Price | Unit of Measure | Amount
                for i, part in enumerate(parts):
                    # First column is usually quantity ordered
                    if i == 0 and quantity is None and re.search(r"^\d[\d,\s]*$", part):
                        quantity_str = re.sub(r"[\s,]", "", part)
                        if quantity_str.isdigit():
                            quantity = Decimal(quantity_str)

                    # Third column (index 2) is usually order/job number
                    if i == 2 and item_code is None and re.match(r"^\d{5,7}$", part):
                        item_code = part

                    # Description is typically 4th column (index 3) or longest text
                    if i == 3 and len(part) > len(description):
                        description = part

                    # Last column is amount
                    if i == len(parts) - 1:
                        amount_match = re.search(r"([\d,]+\.\d+)", part)
                        if amount_match:
                            amount = self._parse_decimal(amount_match.group(1))

            # Fallback: heuristic-based extraction
            # First numeric value (not a 6-digit code) is likely quantity
            if quantity is None:
                for i, part in enumerate(parts):
                    # Skip if it looks like an order number (6 digits)
                    if re.match(r"^\d{6}$", part):
                        continue
                    # Look for quantity patterns: "1,500" or "60 x" or just "1500"
                    if re.search(r"^\d[\d,\s]*$", part):
                        # Quantity pattern
                        quantity_str = re.sub(r"[\s,]", "", part)
                        if quantity_str.isdigit():
                            quantity = Decimal(quantity_str)
                            break

            # Find amount (rightmost numeric value with decimal or large number)
            if amount is None:
                for i in range(len(parts) - 1, -1, -1):
                    part = parts[i]
                    # Look for currency amounts
                    if re.search(r"\d+\.\d+", part):
                        amount_match = re.search(r"([\d,]+\.\d+)", part)
                        if amount_match:
                            amount = self._parse_decimal(amount_match.group(1))
                            break

            # Description is typically the longest text field
            if not description:
                for part in parts:
                    if len(part) > len(description) and not re.match(
                        r"^[\d\.,\s\$x]+$", part
                    ):
                        # Not purely numeric/currency
                        description = part

            # Unit price - look for price pattern (decimal with 2-4 digits)
            for part in parts:
                if price_each is None and re.search(
                    r"\d+\.\d{2,4}\s*(Each|USD)?", part, re.IGNORECASE
                ):
                    price_match = re.search(r"([\d,]+\.\d{2,4})", part)
                    if price_match:
                        price_each = self._parse_decimal(price_match.group(1))

            # Order/Job number - numeric code
            if item_code is None:
                for part in parts:
                    if re.match(r"^\d{5,7}$", part):
                        item_code = part
                        break

            # Only create item if we have essential data
            if not description or amount is None:
                return None

            return LineItem(
                item_code=item_code,
                description=description,
                quantity=quantity,
                price_each=price_each,
                amount=amount,
            )

        except Exception as e:
            logger.warning(f"Failed to parse item row: {e}")
            return None

    def _extract_totals(self, markdown: str, invoice: Invoice) -> None:
        """Extract total, subtotal, and sales tax from table footer."""
        # Pattern variations in table:
        # Format 1: | ... | Total: | 404.99 |
        # Format 2: | ... | Invoice Total: | 563.39 |
        # Format 3: | ... | Freight - Invoice Total: | Non-Taxable: | 21.56 ---------------- |
        #           | ... |                           |              | 1,125.56               |

        # Extract Total (required) - try multiple patterns
        total_match = None

        # Try 1: "Invoice Total:" or "Total:" with amount (handle multiple pipes/spaces)
        # Pattern handles: "Total: 404.99", "Invoice Total: | ... | 563.39", etc.
        total_match = re.search(
            r"(?:Invoice\s+)?Total:\s*[|\s]*([\d,]+\.\d+)", markdown, re.IGNORECASE
        )

        if not total_match:
            # Try 2: "Freight - Invoice Total:" with amount on next line or in cell
            # This format has the total on a separate table row after the label
            freight_total_pos = re.search(
                r"Freight\s*-\s*Invoice\s+Total:", markdown, re.IGNORECASE
            )
            if freight_total_pos:
                # Search for amount after this position (need larger window for multi-line tables)
                remaining = markdown[freight_total_pos.end():]
                # Look for amounts in the next 600 characters (covers next table row with padding)
                amounts = re.findall(r"[\d,]+\.\d+", remaining[:600])
                if amounts:
                    # Take the last amount found (usually the total on the next row)
                    total_match = re.search(r"([\d,]+\.\d+)", amounts[-1])

        if total_match:
            invoice.total = self._parse_decimal(total_match.group(1))
        else:
            invoice.add_error("Could not extract total amount")
            logger.warning(f"Total not found in {invoice.source_file}")

        # Extract Sales amount (this is the subtotal before freight, not tax)
        # Pattern: "Sales: 1,104.00" or "Sales: | 554.40"
        sales_match = re.search(r"Sales:\s*\|?\s*([\d,]+\.\d+)", markdown, re.IGNORECASE)
        if sales_match:
            invoice.subtotal = self._parse_decimal(sales_match.group(1))
        else:
            # Fallback: try to find in Non-Taxable field
            non_taxable_match = re.search(
                r"Non-Taxable:\s*\|?\s*([\d,]+\.\d+)", markdown, re.IGNORECASE
            )
            if non_taxable_match:
                invoice.subtotal = self._parse_decimal(non_taxable_match.group(1))
            else:
                # Last resort: use total if no breakdown found
                invoice.subtotal = invoice.total

        # Wolverine Printing invoices typically show "Total Tax 0.00 USD"
        # Extract sales tax (usually 0)
        tax_match = re.search(
            r"(?:Total\s+)?Tax[:\s]*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if tax_match:
            invoice.sales_tax = self._parse_decimal(tax_match.group(1))
        else:
            # Default to 0 if not found (Wolverine typically has no tax)
            invoice.sales_tax = Decimal("0.00")
