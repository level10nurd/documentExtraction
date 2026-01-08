"""Sunset Press invoice extractor."""

import logging
import re
from decimal import Decimal

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class SunsetPressExtractor(BaseExtractor):
    """Extractor for Sunset Press invoices."""

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from Sunset Press document.

        Sunset Press invoices have:
        - Header section with company info and Ship To/Bill To
        - Table with P.O. Number and Terms
        - Main items table with Quantity, Item Code, Description, Price Each, Amount
        - Footer with Subtotal, Sales Tax, Total, Payments/Credits, Balance Due
        - Invoice number and date at the bottom

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.SUNSET_PRESS, filename)

        try:
            # Extract invoice number and date
            self._extract_invoice_header(markdown, invoice)

            # Extract PO number
            self._extract_po_number(markdown, invoice)

            # Extract line items
            self._extract_line_items(markdown, invoice)

            # Extract totals
            self._extract_totals(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted Sunset Press invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting Sunset Press invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_header(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number and date from the invoice header."""
        # Try Method 1: Table format
        # Pattern: | Date       |   Invoice # |
        #          |------------|-------------|
        #          | 10/28/2024 |       48417 |
        inv_match = re.search(
            r"\|\s*(\d{1,2}/\d{1,2}/\d{4})\s*\|\s*(\d+)\s*\|", markdown
        )

        if inv_match:
            # Group 1 is date, Group 2 is invoice number
            try:
                from dateutil.parser import parse

                invoice.invoice_date = parse(inv_match.group(1)).date()
            except Exception as e:
                invoice.add_error(f"Failed to parse date: {e}")
                logger.warning(f"Could not parse date in {invoice.source_file}")

            invoice.invoice_number = inv_match.group(2).strip()
            return

        # Try Method 2: Non-table format (plain text)
        # Pattern: Date\n7/31/2024\nInvoice #\n48370
        # or:      Invoice\nDate\n7/31/2024\nInvoice #\n48371
        date_match = re.search(
            r"(?:Invoice\s+)?Date\s*\n\s*(\d{1,2}/\d{1,2}/\d{4})", markdown, re.IGNORECASE
        )
        inv_num_match = re.search(
            r"Invoice\s*#?\s*\n\s*(\d+)", markdown, re.IGNORECASE
        )

        if date_match:
            try:
                from dateutil.parser import parse

                invoice.invoice_date = parse(date_match.group(1)).date()
            except Exception as e:
                invoice.add_error(f"Failed to parse date: {e}")
                logger.warning(f"Could not parse date in {invoice.source_file}")

        if inv_num_match:
            invoice.invoice_number = inv_num_match.group(1).strip()

        if not date_match and not inv_num_match:
            invoice.add_error("Could not extract invoice number or date")
            logger.warning(f"Invoice header not found in {invoice.source_file}")

    def _extract_po_number(self, markdown: str, invoice: Invoice) -> None:
        """Extract PO number from the table."""
        # Look for P.O. Number in the table
        # Pattern: | ... | P.O. Number | Terms Rep | ...
        #          |-----|-------------|-----------|
        #          | ... | 102S        | Due on... | ...

        lines = markdown.split("\n")
        po_found = False

        for i, line in enumerate(lines):
            if "P.O. Number" in line and "|" in line:
                # Found header line, get data from next non-separator line
                for j in range(i + 1, min(i + 3, len(lines))):
                    data_line = lines[j]
                    if "---" in data_line:
                        continue
                    # Parse the data line
                    parts = [p.strip() for p in data_line.split("|")]
                    # Find which column has P.O. Number
                    header_parts = [p.strip() for p in line.split("|")]
                    try:
                        po_idx = header_parts.index("P.O. Number")
                        if po_idx < len(parts):
                            po_value = parts[po_idx]
                            if po_value and po_value not in ["", "P.O. Number"]:
                                invoice.po_number = self._clean_po_number(po_value)
                                po_found = True
                                break
                    except (ValueError, IndexError):
                        pass
                if po_found:
                    break

        if not po_found:
            logger.debug(f"PO number not found in {invoice.source_file}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from the main items table."""
        # Sunset Press has multiple formats:
        # Format 1: Table with pipes
        # | Quantity | Item Code | Description | ... | Price Each | Amount |
        # | 2,700 2,700 1 | 1002-Package 1002-Package 1002-Package | ... | 1.28 87.00 | 6,156.00 4,455.00 87.00 |
        #
        # Format 2: Space-separated values without clear table structure
        # Quantity Item Code Description Price Each Amount
        # 1,980 1,980 1 1002-Package 1002-Package ... 115.00 5,247.00 3,267.00 115.00

        lines = markdown.split("\n")

        # Try to find table-based format first
        for i, line in enumerate(lines):
            # Find the item header row with pipes
            if "Item Code" in line and "Description" in line and "Amount" in line and "|" in line:
                # Skip separator line and get data
                for j in range(i + 1, min(i + 3, len(lines))):
                    data_line = lines[j]
                    if "---" in data_line:
                        continue
                    if "|" in data_line and "APPRECIATE" not in data_line:
                        self._parse_item_line(data_line, invoice)
                        break
                return

        # Try alternative parsing: look for field-based layout
        # Format: Quantity\n1,760\n1\n\nItem Code\n1002-Package 1002-Package\n\nDescription...
        for i, line in enumerate(lines):
            if "Quantity" in line and i + 5 < len(lines):
                # Try to parse structured field layout
                self._parse_field_based_items(lines, i, invoice)
                if invoice.line_items:  # If we found items, we're done
                    return

        # Final fallback: look for single-line item format
        for i, line in enumerate(lines):
            if "Quantity" in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if re.search(r"\d+-\w+", next_line) or "Package" in next_line:
                    # Found potential item data in next_line
                    for j in range(i + 1, min(i + 4, len(lines))):
                        if "APPRECIATE" not in lines[j] and (
                            re.search(r"\d+-\w+", lines[j]) or "Package" in lines[j]
                        ):
                            self._parse_non_table_items(lines[j], invoice)
                            break
                    return

    def _parse_field_based_items(
        self, lines: list[str], start_idx: int, invoice: Invoice
    ) -> None:
        """
        Parse line items from field-based layout.

        Format:
            Quantity
            1,760
            1

            Item Code
            1002-Package 1002-Package

            Description
            Refill Box - Stemmed Delivery-1 Pallet

            Price Each
            1.98
            128.00

            Amount
            3,484.80 128.00

        Args:
            lines: All markdown lines
            start_idx: Index where "Quantity" was found
            invoice: Invoice object to add items to
        """
        # Find the sections by looking for keywords
        sections = {}
        keywords = ["Quantity", "Item Code", "Description", "Price Each", "Amount"]

        # Scan forward from start_idx to find all sections
        for i in range(start_idx, min(start_idx + 50, len(lines))):
            line = lines[i].strip()
            if "APPRECIATE" in line or "PAYMENT TERMS" in line:
                break

            for keyword in keywords:
                if keyword in line and keyword not in sections:
                    # Found keyword, capture data on following lines
                    data_lines = []
                    for j in range(i + 1, min(i + 10, len(lines))):
                        next_line = lines[j].strip()
                        # Stop at next keyword or empty section
                        if any(kw in next_line for kw in keywords):
                            break
                        if next_line and not next_line.startswith("#"):
                            data_lines.append(next_line)
                    sections[keyword] = data_lines

        # Must have at least Item Code and Amount
        if "Item Code" not in sections or "Amount" not in sections:
            logger.debug("Field-based parsing: missing required sections")
            return

        # Parse item codes
        item_codes = []
        for line in sections.get("Item Code", []):
            codes = re.findall(r"\b\d+-\w+\b", line)
            item_codes.extend(codes)

        if not item_codes:
            logger.debug("Field-based parsing: no item codes found")
            return

        # Parse quantities
        quantities = []
        for line in sections.get("Quantity", []):
            qtys = re.findall(r"\b[\d,]+\b", line)
            quantities.extend([q.replace(",", "") for q in qtys])

        # Parse amounts
        amounts = []
        for line in sections.get("Amount", []):
            amts = re.findall(r"[\d,]+\.\d{2}", line)
            amounts.extend(amts)

        # Parse prices
        prices = []
        for line in sections.get("Price Each", []):
            prs = re.findall(r"[\d,]+\.\d{2}", line)
            prices.extend(prs)

        # Get description (combine all description lines)
        description = " ".join(sections.get("Description", [])).strip()

        # Create line items (one per item code)
        num_items = len(item_codes)
        for i in range(num_items):
            try:
                quantity = None
                if i < len(quantities) and quantities[i].isdigit():
                    quantity = Decimal(quantities[i])

                item_code = item_codes[i]

                price_each = None
                if i < len(prices):
                    price_each = self._parse_decimal(prices[i])

                amount = None
                if i < len(amounts):
                    amount = self._parse_decimal(amounts[i])
                else:
                    amount = Decimal("0")

                item = LineItem(
                    item_code=item_code,
                    description=description,
                    quantity=quantity,
                    price_each=price_each,
                    amount=amount,
                )
                invoice.line_items.append(item)

            except Exception as e:
                logger.warning(f"Failed to create field-based line item {i}: {e}")

    def _parse_item_line(self, line: str, invoice: Invoice) -> None:
        """
        Parse a line with multiple items.

        Line format: | 2,700 2,700 1 | 1002-Package 1002-Package 1002-Package | Description... | ... | ... | 1.28 87.00 | 6,156.00 4,455.00 87.00 |

        Args:
            line: Line containing item data
            invoice: Invoice object to add items to
        """
        # Split by | and get all parts
        parts = [p.strip() for p in line.split("|")]

        # Remove empty parts
        parts = [p for p in parts if p]

        if len(parts) < 3:
            logger.warning(f"Item line has too few parts: {len(parts)}")
            return

        # Column 0: Quantities (e.g., "2,700 2,700 1")
        quantities_str = parts[0]
        quantities = re.findall(r"[\d,]+", quantities_str)
        quantities = [q.replace(",", "") for q in quantities]

        # Column 1: Item codes (e.g., "1002-Package 1002-Package 1002-Package")
        item_codes_str = parts[1]
        # Item codes may be like "1002-Package" or other patterns
        item_codes = item_codes_str.split()

        if not item_codes:
            logger.warning("No item codes found")
            return

        # Descriptions are in columns 2-4
        # Combine them as they may be split across columns
        description_parts = parts[2:5] if len(parts) >= 5 else parts[2:3]
        descriptions_str = " ".join(description_parts)

        # For simplicity, we'll use the combined description for all items
        # In reality, descriptions might be split by item, but the markdown may have rendering issues
        descriptions = [descriptions_str.strip()] * len(item_codes)

        # Find Price Each column (second-to-last or near the end)
        # Prices are like "1.28 87.00"
        prices = []
        amounts = []

        # Last column should be amounts
        if len(parts) >= 2:
            amounts_str = parts[-1]
            amounts = re.findall(r"[\d,]+\.\d{2}", amounts_str)

        # Second-to-last should be prices
        if len(parts) >= 2:
            prices_str = parts[-2]
            prices = re.findall(r"[\d,]+\.\d{2}", prices_str)

        # Ensure we have the same number of items
        num_items = max(len(quantities), len(item_codes), len(prices), len(amounts))

        # Create line items
        for i in range(num_items):
            try:
                quantity = (
                    Decimal(quantities[i].replace(",", ""))
                    if i < len(quantities)
                    else None
                )
                item_code = item_codes[i] if i < len(item_codes) else "Unknown"
                description = descriptions[i] if i < len(descriptions) else ""
                price_each = self._parse_decimal(prices[i]) if i < len(prices) else None
                amount = (
                    self._parse_decimal(amounts[i])
                    if i < len(amounts)
                    else Decimal("0")
                )

                item = LineItem(
                    item_code=item_code,
                    description=description,
                    quantity=quantity,
                    price_each=price_each,
                    amount=amount,
                )
                invoice.line_items.append(item)
            except Exception as e:
                logger.warning(f"Failed to create line item {i}: {e}")
                invoice.add_error(f"Failed to parse line item {i}")

    def _parse_non_table_items(self, line: str, invoice: Invoice) -> None:
        """
        Parse line items from non-table format.

        Format: 1,980 1,980 1 1002-Package 1002-Package 1002-Package Description... 115.00 5,247.00 3,267.00 115.00

        Args:
            line: Line containing item data (space-separated)
            invoice: Invoice object to add items to
        """
        # Extract quantities (numbers with optional commas)
        quantities = re.findall(r"\b[\d,]+\b", line)

        # Extract item codes (pattern like "1002-Package")
        item_codes = re.findall(r"\b\d+-\w+\b", line)

        if not item_codes:
            logger.warning(f"No item codes found in line: {line[:100]}")
            return

        # Extract monetary amounts (numbers with decimal points)
        amounts = re.findall(r"[\d,]+\.\d{2}", line)

        # Build description by removing known patterns
        desc_line = line
        for qty in quantities[:len(item_codes)]:
            desc_line = desc_line.replace(qty, "", 1)
        for code in item_codes:
            desc_line = desc_line.replace(code, "", 1)
        for amt in amounts:
            desc_line = desc_line.replace(amt, "", 1)

        description = " ".join(desc_line.split()).strip()

        # Match quantities to item codes
        # If we have more amounts than item codes, last amounts are prices/totals
        num_items = len(item_codes)

        # Typical pattern: N quantities, N item codes, description, M prices/amounts
        # Try to pair them up
        for i in range(num_items):
            try:
                quantity = None
                if i < len(quantities):
                    qty_str = quantities[i].replace(",", "")
                    # Filter out likely amounts (too large to be quantity)
                    if "." not in quantities[i] and len(qty_str) < 6:
                        quantity = Decimal(qty_str)

                item_code = item_codes[i]

                # For price/amount: if we have 2*N amounts, first N are prices, second N are totals
                price_each = None
                amount = None

                if len(amounts) >= 2 * num_items:
                    # Pattern: N prices followed by N amounts
                    if i < len(amounts) // 2:
                        price_each = self._parse_decimal(amounts[i])
                    if (len(amounts) // 2 + i) < len(amounts):
                        amount = self._parse_decimal(amounts[len(amounts) // 2 + i])
                elif len(amounts) > 0:
                    # Just use available amounts
                    if i < len(amounts):
                        amount = self._parse_decimal(amounts[i])

                item = LineItem(
                    item_code=item_code,
                    description=description,
                    quantity=quantity,
                    price_each=price_each,
                    amount=amount if amount else Decimal("0"),
                )
                invoice.line_items.append(item)

            except Exception as e:
                logger.warning(f"Failed to create non-table line item {i}: {e}")
                invoice.add_error(f"Failed to parse non-table line item {i}")

    def _extract_totals(self, markdown: str, invoice: Invoice) -> None:
        """Extract subtotal, sales tax, total, and balance due."""
        # Look for Subtotal
        subtotal_match = re.search(
            r"Subtotal[^\$]*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if subtotal_match:
            invoice.subtotal = self._parse_decimal(subtotal_match.group(1))

        # Look for Sales Tax
        tax_match = re.search(
            r"Sales\s+Tax[^\$]*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if tax_match:
            invoice.sales_tax = self._parse_decimal(tax_match.group(1))
        else:
            invoice.sales_tax = Decimal("0.00")

        # Look for Total
        total_match = re.search(
            r"(?<!Balance\s)Total[^\$]*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if total_match:
            invoice.total = self._parse_decimal(total_match.group(1))

        # Look for Balance Due (final amount)
        balance_match = re.search(
            r"Balance\s+Due[^\$]*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if balance_match:
            # Use Balance Due as the authoritative total
            invoice.total = self._parse_decimal(balance_match.group(1))

        if not invoice.total:
            invoice.add_error("Could not extract total amount")
            logger.warning(f"Total not found in {invoice.source_file}")
