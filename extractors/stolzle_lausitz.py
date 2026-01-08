"""Stölzle Glassware invoice extractor."""

import logging
import re
from decimal import Decimal

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class StolzleLausitzExtractor(BaseExtractor):
    """Extractor for Stölzle Glassware invoices."""

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from Stölzle Glassware document.

        Stölzle invoices have:
        - Header with invoice number, date created, date due
        - Billing and shipping address blocks
        - Table with columns: QTY, NAME, DATE, DISCOUNT, PRICE
        - Footer with Order ID, Updated At, Total Due
        - Shipping as a separate line in the table

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.STOLZLE_LAUSITZ, filename)

        try:
            # Extract invoice number and dates from header
            self._extract_invoice_header(markdown, invoice)

            # Extract order ID (used as PO number)
            self._extract_order_id(markdown, invoice)

            # Extract line items from main table
            self._extract_line_items(markdown, invoice)

            # Extract totals
            self._extract_totals(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted Stölzle Glassware invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting Stölzle Glassware invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_header(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number and dates from header."""
        # Pattern: Invoice No:\n\n#22-2621
        inv_match = re.search(
            r"Invoice\s+No:?\s*[#\s]*(\d{2}-\d{4})", markdown, re.IGNORECASE
        )

        if inv_match:
            invoice.invoice_number = inv_match.group(1).strip()
        else:
            invoice.add_error("Could not extract invoice number")
            logger.warning(f"Invoice number not found in {invoice.source_file}")

        # Pattern: Date created:\n\n12-09-2024
        date_match = re.search(
            r"Date\s+created:?\s*(\d{1,2}-\d{1,2}-\d{4})", markdown, re.IGNORECASE
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

    def _extract_order_id(self, markdown: str, invoice: Invoice) -> None:
        """Extract order ID (used as PO number)."""
        # Pattern: ORDER ID, UPDATED AT, TOTAL DUE are headers
        # Then several lines down: order_id_value, date_value, total_value
        # The values are aligned with the headers
        lines = markdown.split("\n")
        order_id_line_idx = None

        # Find the ORDER ID header line
        for i, line in enumerate(lines):
            if "ORDER ID" in line and "UPDATED" not in line:
                order_id_line_idx = i
                break

        if order_id_line_idx is not None:
            # Look for numeric value in lines after the headers
            # Typically 4-8 lines after the header
            for j in range(
                order_id_line_idx + 4, min(order_id_line_idx + 10, len(lines))
            ):
                stripped = lines[j].strip()
                if stripped and stripped.isdigit() and len(stripped) > 10:
                    invoice.po_number = stripped
                    return

        logger.debug(f"Order ID not found in {invoice.source_file}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from the main table."""
        # Find the table with QTY, NAME, DATE, DISCOUNT, PRICE columns
        lines = markdown.split("\n")
        in_table = False
        shipping_amount = None

        for i, line in enumerate(lines):
            # Find the table header
            if "QTY" in line and "NAME" in line and "PRICE" in line:
                in_table = True
                # Skip separator line
                continue

            if in_table and "|" in line:
                # Check for shipping line
                if "Shipping" in line or "Freight" in line:
                    # Extract shipping amount
                    shipping_match = re.search(r"([\d,]+\.?\d*)\s+USD", line)
                    if shipping_match:
                        shipping_amount = self._parse_decimal(shipping_match.group(1))
                    continue

                # Check for total line (end of items)
                if "Total Tax" in line or "NET" in line or "TOTAL DUE" in line:
                    break

                # Parse product line
                self._parse_item_line(line, invoice)

        # Add shipping as a separate line item if found
        if shipping_amount and shipping_amount > 0:
            shipping_item = LineItem(
                item_code="SHIPPING",
                description="Shipping Freight",
                quantity=Decimal("1"),
                price_each=shipping_amount,
                amount=shipping_amount,
            )
            invoice.line_items.append(shipping_item)

    def _parse_item_line(self, line: str, invoice: Invoice) -> None:
        """
        Parse a product line from the table.

        Line format: | 60 x  | Revolution Double Old-Fashioned Tumbler 16 oz - Set of six. SKU: 3580016-6 | 12-09-2024 | 727.2 USD | 23.88 USD |

        Args:
            line: Line containing item data
            invoice: Invoice object to add items to
        """
        # Split by | and get all parts
        parts = [p.strip() for p in line.split("|")]

        # Remove empty parts
        parts = [p for p in parts if p]

        if len(parts) < 5:
            # Not enough columns for a valid item line
            return

        # Column 0: Quantity (e.g., "60 x")
        qty_str = parts[0].replace("x", "").strip()
        try:
            quantity = Decimal(qty_str)
        except Exception:
            logger.debug(f"Could not parse quantity from '{parts[0]}'")
            return

        # Column 1: Item name and description with SKU
        name_desc = parts[1]

        # Extract SKU if present
        sku_match = re.search(r"SKU:?\s*([\w\-]+)", name_desc)
        item_code = sku_match.group(1) if sku_match else ""

        # Remove SKU from description
        description = re.sub(r"SKU:?\s*[\w\-]+", "", name_desc).strip()

        # Column 2: Date (not used for line item)
        # Column 3: Discount amount (subtotal after discount)
        discount_str = parts[3].replace("USD", "").strip()
        subtotal = self._parse_decimal(discount_str)

        # Column 4: Price each (unit price)
        price_str = parts[4].replace("USD", "").strip()
        price_each = self._parse_decimal(price_str)

        # Create line item
        try:
            item = LineItem(
                item_code=item_code,
                description=description,
                quantity=quantity,
                price_each=price_each,
                amount=subtotal if subtotal else Decimal("0"),
            )
            invoice.line_items.append(item)
        except Exception as e:
            logger.warning(f"Failed to create line item: {e}")
            invoice.add_error(f"Failed to parse line item: {description[:50]}")

    def _extract_totals(self, markdown: str, invoice: Invoice) -> None:
        """Extract total, subtotal, and tax."""
        # Pattern: TOTAL DUE\n\n1752.80 USD
        # The amount may appear several lines after the label, use DOTALL
        total_match = re.search(
            r"TOTAL\s+DUE[\s\S]*?([\d,]+\.?\d*)\s+USD", markdown, re.IGNORECASE
        )
        if total_match:
            invoice.total = self._parse_decimal(total_match.group(1))
        else:
            invoice.add_error("Could not extract total amount")
            logger.warning(f"Total not found in {invoice.source_file}")

        # Pattern: NET\n\n1432.80 USD (subtotal before shipping)
        # The amount may appear several lines after or in a table cell
        subtotal_match = re.search(
            r"NET[\s\S]*?([\d,]+\.?\d*)\s+USD", markdown, re.IGNORECASE
        )
        if subtotal_match:
            invoice.subtotal = self._parse_decimal(subtotal_match.group(1))
        else:
            # If no NET found, use total
            invoice.subtotal = invoice.total

        # Pattern: Total Tax\n\n0.00 USD
        # The amount may appear several lines after or in a table cell
        tax_match = re.search(
            r"Total\s+Tax[\s\S]*?([\d,]+\.?\d*)\s+USD", markdown, re.IGNORECASE
        )
        if tax_match:
            invoice.sales_tax = self._parse_decimal(tax_match.group(1))
        else:
            # Default to 0 if not found
            invoice.sales_tax = Decimal("0.00")
