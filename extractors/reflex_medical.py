"""REFLEX MEDICAL CORP invoice extractor."""

import logging
import re
from decimal import Decimal

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class ReflexMedicalExtractor(BaseExtractor):
    """Extractor for REFLEX MEDICAL CORP invoices."""

    def __init__(self, doc_processor):
        """Initialize with vendor type."""
        super().__init__(doc_processor, vendor_type=VendorType.REFLEX_MEDICAL)

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from REFLEX MEDICAL document.

        REFLEX MEDICAL invoices have:
        - Table 0: Invoice header (Date | Invoice #)
        - Table 1: Bill To / Ship To
        - Table 2: Main data table with PO, Terms, Items, and Totals

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.REFLEX_MEDICAL, filename)

        try:
            # Extract invoice number and date from first table
            self._extract_invoice_header(markdown, invoice)

            # Extract PO number from second part of main table
            self._extract_po_number(markdown, invoice)

            # Extract line items from main table
            self._extract_line_items(markdown, invoice)

            # Extract totals
            self._extract_totals(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted REFLEX MEDICAL invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting REFLEX MEDICAL invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_header(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number and date from first table."""
        # Look for the invoice header table
        # Pattern: | Date       |   Invoice # |
        #          |------------|-------------|
        #          | 10/22/2024 |       62935 |
        # The invoice number may have leading spaces

        # Extract invoice number - look for pattern after "Invoice #" header
        # Match the table row with date | invoice_number
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
        else:
            invoice.add_error("Could not extract invoice number or date")
            logger.warning(f"Invoice header not found in {invoice.source_file}")

    def _extract_po_number(self, markdown: str, invoice: Invoice) -> None:
        """Extract PO number from the table."""
        # Look for P.O. No. in the table header, then get value from next row
        # Pattern: |     | P.O. No. | Terms  | Due Date | ...
        #          |-----|----------|--------|----------|
        #          |     | RF45533  | Net 60 | 12/21/24 | ...

        # Find the line with P.O. No. header
        lines = markdown.split("\n")
        po_found = False

        for i, line in enumerate(lines):
            if "P.O. No." in line and "|" in line:
                # Found header line, next non-separator line has the data
                # Skip the separator line (---) and get data line
                for j in range(i + 1, min(i + 3, len(lines))):
                    data_line = lines[j]
                    if "---" in data_line:
                        continue
                    # Parse the data line - PO is in second column
                    parts = [p.strip() for p in data_line.split("|")]
                    if len(parts) >= 3:
                        # Parts: ['', '', 'RF45533', 'Net 60', ...]
                        po_value = parts[2] if len(parts) > 2 else None
                        if po_value and po_value not in ["", "P.O. No."]:
                            invoice.po_number = self._clean_po_number(po_value)
                            po_found = True
                            break
                if po_found:
                    break

        if not po_found:
            logger.debug(f"PO number not found in {invoice.source_file}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from the main table."""
        # REFLEX MEDICAL has TWO different formats:
        #
        # Format 1 (Complex): Multiple items per row with duplicate columns
        #   | Item | Description | ... | Qty | ... | Rate | ... | Amount |
        #   | 21-054-07 21-055-07 | ...Blue ...Blue | ... | 224 268 | ... | 1.59 1.59 | ... | 356.16 426.12 |
        #
        # Format 2 (Simple): Standard table, one item per row
        #   | Item | Description | Qty | Rate | Amount |
        #   |      | STY001-BM9MM | STY001-BM9MM 9MM Cap... | 61,525 | 0.045 | 2,768.63 |

        lines = markdown.split("\n")

        for i, line in enumerate(lines):
            # Find the item header row
            if (
                "Item" in line
                and "Description" in line
                and "Qty" in line
                and "Amount" in line
            ):
                # Check which format by counting columns
                header_parts = [p.strip() for p in line.split("|")]
                header_parts = [p for p in header_parts if p]

                # If 5-6 columns, it's simple format; if more, it's complex format
                is_simple_format = len(header_parts) <= 6

                logger.debug(f"Detected {'simple' if is_simple_format else 'complex'} format ({len(header_parts)} columns)")

                # Process all data lines after header
                j = i + 1
                while j < len(lines):
                    data_line = lines[j]
                    # Skip separator line
                    if "---" in data_line:
                        j += 1
                        continue
                    # Stop at totals or payments
                    if ("Total" in data_line or "Balance Due" in data_line or
                        "Payments" in data_line):
                        break
                    # Check for empty line (end of table)
                    if not data_line.strip():
                        break
                    # Process line if it has data
                    if "|" in data_line:
                        if is_simple_format:
                            self._parse_simple_item_line(data_line, invoice)
                        else:
                            # Check if this line has item codes (not a total/payment line)
                            parts = [p.strip() for p in data_line.split("|")]
                            if len(parts) > 1 and parts[1]:  # First column has data
                                self._parse_item_line(data_line, invoice)
                    j += 1
                break

    def _parse_simple_item_line(self, line: str, invoice: Invoice) -> None:
        """
        Parse a simple item line (standard table format).

        Format: | Item | Description | Qty | Rate | Amount |
                |      | STY001-BM9MM | STY001-BM9MM 9MM Cap... | 61,525 | 0.045 | 2,768.63 |

        Args:
            line: Line containing item data
            invoice: Invoice object to add items to
        """
        # Split by | and get all parts
        parts = [p.strip() for p in line.split("|")]

        # Remove empty parts
        parts = [p for p in parts if p]

        if len(parts) < 4:
            logger.debug(f"Simple format line has too few parts: {len(parts)}")
            return

        # In simple format:
        # parts[0] = Item column (often empty)
        # parts[1] = Description (contains item code + description)
        # parts[2] = Qty
        # parts[3] = Rate
        # parts[4] = Amount (if present)

        # Extract item code from description (first part before space or |)
        description_full = parts[1] if len(parts) > 1 else ""

        # Try to find item code pattern at start of description
        item_code_match = re.match(r"^([A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+|\d{2}-\d{3}-\d{2})", description_full)
        if not item_code_match:
            # Try alternative patterns
            item_code_match = re.match(r"^(\S+-\S+)", description_full)

        if not item_code_match:
            logger.debug(f"No item code found in simple format: {description_full}")
            return

        item_code = item_code_match.group(1)

        # Description is everything after the item code
        description = description_full[len(item_code):].strip()
        # Remove any leading | or similar separators
        description = re.sub(r"^[|\s]+", "", description)

        # Parse quantity (parts[2])
        qty_value = None
        if len(parts) > 2 and parts[2]:
            try:
                qty_value = Decimal(parts[2].replace(',', ''))
            except Exception as e:
                logger.warning(f"Failed to parse quantity '{parts[2]}': {e}")

        # Parse rate (parts[3])
        price_value = None
        if len(parts) > 3 and parts[3]:
            try:
                price_value = Decimal(parts[3].replace(',', ''))
            except Exception as e:
                logger.warning(f"Failed to parse rate '{parts[3]}': {e}")

        # Parse amount (parts[4])
        amount_value = Decimal("0")
        if len(parts) > 4 and parts[4]:
            try:
                amount_value = Decimal(parts[4].replace(',', ''))
            except Exception as e:
                logger.warning(f"Failed to parse amount '{parts[4]}': {e}")

        # Create line item
        try:
            item = LineItem(
                item_code=item_code,
                description=description,
                quantity=qty_value,
                price_each=price_value,
                amount=amount_value,
            )
            invoice.line_items.append(item)
        except Exception as e:
            logger.warning(f"Failed to create simple format line item {item_code}: {e}")
            invoice.add_error(f"Failed to parse line item {item_code}")

    def _parse_item_line(self, line: str, invoice: Invoice) -> None:
        """
        Parse a complex item line with multiple items.

        Line formats:
        - Numeric codes: | 21-054-07 21-055-07 | descriptions | ... | 224 268 | ... | 1.59 1.59 | ... | 356.16 426.12 |
        - Alpha codes: | STY001-SS-06 STY001-SCO-06 | descriptions | ... | 1,257 2,550 | ... | 1.22 1.20 | ... | 1,533.54 3,060.00 |

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

        # Column 0: Item codes (e.g., "21-054-07 21-055-07" or "STY001-SS-06 STY001-SCO-06")
        item_codes_str = parts[0]

        # Try multiple patterns for item codes
        # Pattern 1: Numeric format (21-054-07)
        item_codes = re.findall(r"\d{2}-\d{3}-\d{2}", item_codes_str)

        # Pattern 2: Alphanumeric format (STY001-SS-06, STY001-SCO-06)
        if not item_codes:
            item_codes = re.findall(r"[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+", item_codes_str)

        # Pattern 3: General hyphenated code (fallback)
        if not item_codes:
            item_codes = re.findall(r"\S+-\S+-\S+", item_codes_str)

        if not item_codes:
            logger.warning(f"No item codes found in: {item_codes_str}")
            return

        # Column 1: Descriptions (contains all descriptions with item codes repeated)
        # Format: "21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue"
        descriptions_str = parts[1]

        # Extract descriptions by finding text after each item code
        descriptions = []
        for idx, code in enumerate(item_codes):
            # Find where this code appears in the description
            code_pos = descriptions_str.find(code)
            if code_pos == -1:
                descriptions.append("Unknown")
                continue

            # Get text after the code until the next code or end
            start = code_pos + len(code)
            # Find next code position
            if idx + 1 < len(item_codes):
                next_code = item_codes[idx + 1]
                end = descriptions_str.find(next_code, start)
                if end == -1:
                    end = len(descriptions_str)
            else:
                end = len(descriptions_str)

            desc = descriptions_str[start:end].strip()
            descriptions.append(desc)

        # Find Qty, Rate, and Amount columns
        # The table has duplicate columns due to rendering:
        # Parts: [0:codes, 1-3:descriptions, 4-5:qty, 6-7:rate, 8-9:amount]
        # Last part should be amounts (e.g., "356.16 426.12" or "1,533.54 3,060.00")
        amounts_str = parts[-1] if parts else ""
        # Match amounts with optional commas: 1,533.54 or 356.16
        amounts = re.findall(r"[\d,]+\.\d+", amounts_str)

        # Rate columns are before amounts - smaller decimal numbers (unit prices)
        rates = []
        if len(parts) >= 3:
            # Check parts from right to left, before the amount column
            for part_idx in range(len(parts) - 2, max(1, len(parts) - 5), -1):
                part = parts[part_idx]
                if "." in part:
                    # Match decimal numbers with optional commas
                    found_rates = re.findall(r"[\d,]*\d+\.\d+", part)
                    # Rates should match number of items
                    if len(found_rates) == len(item_codes):
                        try:
                            # Check if these look like unit prices (typically < 1000)
                            # Remove commas for comparison
                            numeric_rates = [float(r.replace(',', '')) for r in found_rates]
                            if all(r < 1000 for r in numeric_rates):
                                rates = found_rates
                                break
                        except (ValueError, TypeError):
                            pass

        # Quantity columns are before rates
        # Quantities can have commas (e.g., "1,257 2,550" or "224 268")
        quantities = []
        for part_idx in range(2, len(parts)):  # Skip codes and first description
            part = parts[part_idx]
            # Match integers with optional commas, but no decimals
            # Use word boundary to avoid matching parts of decimals
            found_qty = re.findall(r"\b[\d,]+\b", part)
            # Filter out anything with decimals (those are prices/amounts)
            found_qty = [q for q in found_qty if "." not in q]
            if len(found_qty) == len(item_codes):
                quantities = found_qty
                break

        # Create line items (one per item code)
        for i in range(len(item_codes)):
            try:
                # Remove commas from numeric strings before converting to Decimal
                qty_value = None
                if i < len(quantities) and quantities[i]:
                    qty_value = Decimal(quantities[i].replace(',', ''))

                price_value = None
                if i < len(rates) and rates[i]:
                    price_value = Decimal(rates[i].replace(',', ''))

                amount_value = Decimal("0")
                if i < len(amounts) and amounts[i]:
                    amount_value = Decimal(amounts[i].replace(',', ''))

                item = LineItem(
                    item_code=item_codes[i],
                    description=descriptions[i] if i < len(descriptions) else "Unknown",
                    quantity=qty_value,
                    price_each=price_value,
                    amount=amount_value,
                )
                invoice.line_items.append(item)
            except Exception as e:
                logger.warning(f"Failed to create line item {i} ({item_codes[i]}): {e}")
                invoice.add_error(f"Failed to parse line item {item_codes[i]}")

    def _extract_totals(self, markdown: str, invoice: Invoice) -> None:
        """Extract total, subtotal, and any other totals."""
        # Look for Balance Due (final total)
        balance_match = re.search(
            r"Balance\s+Due[^\$]*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if balance_match:
            invoice.total = self._parse_decimal(balance_match.group(1))
        else:
            # Try to find just "Total"
            total_match = re.search(
                r"Total[^\$]*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
            )
            if total_match:
                invoice.total = self._parse_decimal(total_match.group(1))
            else:
                invoice.add_error("Could not extract total amount")
                logger.warning(f"Total not found in {invoice.source_file}")

        # REFLEX MEDICAL typically doesn't separate subtotal and tax
        # The Total line is the subtotal
        # If there's a Total and Balance Due, Total is subtotal
        total_match = re.search(
            r"(?<!Balance\s)(?<!Due\s)Total[^\$]*\$\s*([\d,]+\.?\d*)",
            markdown,
            re.IGNORECASE,
        )
        if total_match and balance_match:
            invoice.subtotal = self._parse_decimal(total_match.group(1))
        else:
            invoice.subtotal = invoice.total

        # Sales tax is typically 0 for REFLEX MEDICAL
        invoice.sales_tax = Decimal("0.00")
