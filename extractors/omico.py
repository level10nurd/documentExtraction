"""OMICO, Inc. invoice extractor."""

import logging
from decimal import Decimal
from typing import Optional

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class OmicoExtractor(BaseExtractor):
    """Extractor for OMICO, Inc. invoices."""

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from OMICO document.

        OMICO invoices typically have a standard format with:
        - Header information with invoice number and date
        - Customer/billing information
        - Line items table with quantities, descriptions, and pricing
        - Totals section with subtotal, tax, and total

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.OMICO, filename)

        try:
            # Extract basic invoice information
            self._extract_invoice_number(markdown, invoice)
            self._extract_invoice_date(markdown, invoice)
            self._extract_po_number(markdown, invoice)

            # Extract line items
            self._extract_line_items(markdown, invoice)

            # Extract totals
            self._extract_totals(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted OMICO invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting OMICO invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_number(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number from document."""
        # Try various patterns for invoice number
        patterns = [
            r"Invoice\s*(?:Number|#|No\.?)[:\s]*(\d+)",
            r"Invoice[:\s]+(\d+)",
            r"(?:Inv|INV)[:\s#]+(\d+)",
        ]

        for pattern in patterns:
            inv_num = self._extract_regex(markdown, pattern)
            if inv_num:
                invoice.invoice_number = self._clean_invoice_number(inv_num)
                return

        invoice.add_error("Could not extract invoice number")
        logger.warning(f"Invoice number not found in {invoice.source_file}")

    def _extract_invoice_date(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice date from document."""
        # Look for date patterns near invoice number or date label
        patterns = [
            r"Invoice\s+Date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"Date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]

        from dateutil.parser import parse

        for pattern in patterns:
            date_str = self._extract_regex(markdown, pattern)
            if date_str:
                try:
                    invoice.invoice_date = parse(date_str).date()
                    return
                except Exception as e:
                    logger.debug(f"Failed to parse date '{date_str}': {e}")
                    continue

        logger.warning(f"Invoice date not found in {invoice.source_file}")

    def _extract_po_number(self, markdown: str, invoice: Invoice) -> None:
        """Extract PO number from document."""
        import re

        # OMICO invoices have PO in a table: | VOCHILL | 1003 | Net 60 Days | ...
        # Try to extract from the Customer table first
        table_pattern = r"Customer\s+PO[^|]*\|[^\d]*(\d+(?:\-\d+)?)"
        match = re.search(table_pattern, markdown)
        if match:
            invoice.po_number = self._clean_po_number(match.group(1))
            return

        # Try various other patterns for PO number
        patterns = [
            r"P\.?O\.?\s*(?:Number|#|No\.?)[:\s]*([A-Z0-9\-]+)",
            r"Purchase\s+Order[:\s]*([A-Z0-9\-]+)",
            r"PO[:\s]+([A-Z0-9\-]+)",
        ]

        for pattern in patterns:
            po_num = self._extract_regex(markdown, pattern)
            if po_num:
                invoice.po_number = self._clean_po_number(po_num)
                return

        logger.debug(f"PO number not found in {invoice.source_file}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from the OMICO invoice table.

        OMICO invoices have TWO different table formats:

        Format 1 (5 columns):
        | Quantity | Part Number | Description | Unit Price USD | Amount USD |
        | 1,650.00 | VCBM20 STEMLESS VCBM01 | STEMLESS BLOW MOLD... | 2.14000 2.04000 | 3,366.00 |

        Format 2 (4 columns - combined):
        | Quantity Part Number | Description | Unit Price USD | Amount USD |
        | VCBM20 STEMLESS 2,700.00 VCBM01 | STEMLESS BLOW MOLD... | 2.14000 2.04000 | 5,508.00 |

        Both formats may have multiple part numbers and prices in different columns.
        """
        import re

        # Try Format 1 first (5 columns): | Qty (+ opt part) | Part Number | Desc | Price | Amt |
        # More flexible pattern that handles bullets, multiple quantities, and multiple amounts
        pattern1 = r"\|\s*([\d,]+\.?\d+(?:\s+[\d,]+\.?\d+)*)\s*(?:([A-Z0-9]+(?:\s+[A-Z0-9]+)*))?\s*\|\s*[•\s]*([A-Z0-9]+(?:\s+[A-Z0-9]+)*)\s*\|\s*([^|]+?)\s*\|\s*([\d,\.]+(?:\s+[\d,\.]+)*)\s*\|\s*([\d,]+\.?\d+(?:\s+[\d,]+\.?\d+)*)\s*\|"
        matches1 = list(re.finditer(pattern1, markdown))

        # Try Format 2 (4 columns): | Part(s) Qty Part(s) | Description | Price | Amount |
        # More flexible to handle bullets and complex combinations
        pattern2 = r"\|\s*[•\s]*([A-Z0-9]+(?:\s+[A-Z0-9]+)*\s+[\d,]+\.?\d+(?:\s+[\d,]+\.?\d+)?(?:\s+[A-Z0-9]+(?:\s+[A-Z0-9]+)*)?)\s*\|\s*([^|]+?)\s*\|\s*([\d,\.]+(?:\s+[\d,\.]+)*)\s*\|\s*([\d,]+\.?\d+(?:\s+[\d,]+\.?\d+)*)\s*\|"
        matches2 = list(re.finditer(pattern2, markdown))

        # Use whichever format found more matches
        if len(matches1) >= len(matches2):
            matches = matches1
            format_type = "5-column"
        else:
            matches = matches2
            format_type = "4-column"

        logger.debug(
            f"Found {len(matches)} potential line items using {format_type} format "
            f"(5-col: {len(matches1)}, 4-col: {len(matches2)})"
        )

        for match in matches:
            try:
                if format_type == "5-column":
                    # Format 1: | Qty | Part | Desc | Price | Amt |
                    quantity_str = match.group(1)  # Quantity
                    part_from_qty_col = match.group(2)  # Optional part from qty column
                    part_from_part_col = match.group(3)  # Part number column
                    description = match.group(4).strip()  # Description
                    price_str = match.group(5).strip()  # Unit price(s)
                    amount_str = match.group(6)  # Amount

                    # Prefer part number from part column
                    part_number = part_from_part_col
                    quantity = self._parse_decimal(quantity_str)

                else:
                    # Format 2: | Part(s) Qty Part(s) | Desc | Price | Amt |
                    # Need to parse the first column to extract quantity and parts
                    combined_col = match.group(1)  # Everything from first column
                    description = match.group(2).strip()  # Description
                    price_str = match.group(3).strip()  # Unit price(s)
                    amount_str = match.group(4)  # Amount

                    # Extract quantity from the combined column (find the FIRST number)
                    qty_match = re.search(r'([\d,]+\.?\d+)', combined_col)
                    if not qty_match:
                        continue
                    quantity_str = qty_match.group(1)
                    quantity = self._parse_decimal(quantity_str)

                    # Extract part number(s) - take everything except the quantity
                    # Example: "VCBM20 STEMLESS 2,700.00 VCBM01" -> "VCBM20 STEMLESS VCBM01"
                    part_number = combined_col.replace(quantity_str, '').strip()
                    part_number = re.sub(r'\s+', ' ', part_number)  # Normalize spaces
                    # Remove any remaining numbers (in case multiple quantities merged)
                    part_number = re.sub(r'[\d,]+\.?\d+', '', part_number).strip()
                    part_number = re.sub(r'\s+', ' ', part_number)  # Normalize again

                # Skip rows that are totals or headers
                desc_lower = description.lower()
                if any(
                    word in desc_lower
                    for word in ["subtotal", "total", "tax", "payment", "credit"]
                ):
                    continue

                # Skip if we don't have the minimum required data
                if not amount_str or not quantity:
                    continue

                # Parse amount - if multiple amounts in the string, take the first
                # This handles cases where Docling merged multiple rows
                amount_numbers = re.findall(r'[\d,]+\.?\d+', amount_str)
                if not amount_numbers:
                    continue
                amount = self._parse_decimal(amount_numbers[0])

                # Parse price - take the last value if multiple prices listed
                price_each = None
                if price_str:
                    # Split on whitespace and take the last valid number
                    prices = re.findall(r"[\d,]+\.?\d*", price_str)
                    if prices:
                        price_each = self._parse_decimal(prices[-1])

                # Create line item
                if description and amount:
                    item = LineItem(
                        item_code=part_number if part_number else None,
                        description=description,
                        quantity=quantity,
                        price_each=price_each,
                        amount=amount,
                    )
                    invoice.line_items.append(item)
                    logger.debug(
                        f"Extracted line item: {part_number} - {description[:50]}... "
                        f"qty={quantity}, price={price_each}, amount={amount}"
                    )

            except Exception as e:
                logger.warning(f"Failed to parse line item from match: {e}")
                logger.debug(f"Match groups: {match.groups()}")
                continue

        if not invoice.line_items:
            logger.warning(f"No line items extracted from {invoice.source_file}")
            invoice.add_error("Could not extract line items")

    def _parse_line_item(self, row: dict) -> Optional[LineItem]:
        """
        Parse a single line item from table row data.

        Args:
            row: Dictionary containing row data with column headers as keys

        Returns:
            LineItem object or None if parsing fails
        """
        # Common column name variations
        qty_keys = ["Qty", "Quantity", "QTY"]
        desc_keys = ["Description", "Item", "Product", "DESC"]
        price_keys = ["Price", "Unit Price", "Price Each", "Rate"]
        amount_keys = ["Amount", "Total", "Line Total", "Extended"]
        item_code_keys = ["Item Code", "Item #", "SKU", "Part #", "Code"]

        # Extract values with flexible column name matching
        quantity = None
        for key in qty_keys:
            if key in row:
                qty_str = row[key]
                if qty_str and qty_str.strip():
                    try:
                        quantity = Decimal(qty_str.replace(",", ""))
                        break
                    except Exception:
                        pass

        description = None
        for key in desc_keys:
            if key in row and row[key]:
                description = row[key].strip()
                break

        price_each = None
        for key in price_keys:
            if key in row:
                price_each = self._parse_decimal(row[key])
                if price_each:
                    break

        amount = None
        for key in amount_keys:
            if key in row:
                amount = self._parse_decimal(row[key])
                if amount:
                    break

        item_code = None
        for key in item_code_keys:
            if key in row and row[key]:
                item_code = row[key].strip()
                break

        # Create line item if we have minimum required fields
        if description or amount:
            return LineItem(
                item_code=item_code,
                description=description or "Unknown",
                quantity=quantity,
                price_each=price_each,
                amount=amount or Decimal("0"),
            )

        return None

    def _extract_totals(self, markdown: str, invoice: Invoice) -> None:
        """Extract subtotal, tax, and total amounts from OMICO invoice table."""
        # OMICO invoices have totals in a table format where labels are in one column
        # and values are in the next column, e.g.:
        # | Subtotal                                          |                  | 10,400.40    |
        # | Total Invoice Amount                              |                  | 10,400.40    |
        # | TOTAL                                             | USD              | 10,400.40    |

        # Extract subtotal - look for "Subtotal" followed by amount in table
        subtotal_patterns = [
            r"Subtotal\s*\|\s*[\d,]*\.?\d*\s*\|\s*([\d,]+\.?\d+)",
            r"\|\s*Subtotal\s*\|[^|]*\|\s*([\d,]+\.?\d+)",
            r"Subtotal[:\s]*\$?\s*([\d,]+\.?\d+)",
        ]
        for pattern in subtotal_patterns:
            subtotal = self._extract_regex(markdown, pattern)
            if subtotal:
                invoice.subtotal = self._parse_decimal(subtotal)
                break

        # Extract sales tax - usually empty or 0 for OMICO
        tax_patterns = [
            r"Sales\s+Tax\s*\|\s*[\d,]*\.?\d*\s*\|\s*([\d,]+\.?\d+)",
            r"\|\s*Sales\s+Tax\s*\|[^|]*\|\s*([\d,]+\.?\d+)",
            r"Sales\s+Tax[:\s]*\$?\s*([\d,]+\.?\d+)",
        ]
        for pattern in tax_patterns:
            tax = self._extract_regex(markdown, pattern)
            if tax:
                invoice.sales_tax = self._parse_decimal(tax)
                break

        # Extract total - try multiple patterns for table-based format
        total_patterns = [
            # Table format: "Total Invoice Amount" or "TOTAL" followed by amount
            r"Total\s+Invoice\s+Amount\s*\|\s*[\d,]*\.?\d*\s*\|\s*([\d,]+\.?\d+)",
            r"\|\s*Total\s+Invoice\s+Amount\s*\|[^|]*\|\s*([\d,]+\.?\d+)",
            r"TOTAL\s*\|\s*USD\s*\|\s*([\d,]+\.?\d+)",
            r"\|\s*TOTAL\s*\|\s*USD\s*\|\s*([\d,]+\.?\d+)",
            # Fallback to standard patterns
            r"(?:Invoice\s+)?Total[:\s]*\$?\s*([\d,]+\.?\d+)",
            r"(?:Balance\s+)?Due[:\s]*\$?\s*([\d,]+\.?\d+)",
            r"Amount\s+Due[:\s]*\$?\s*([\d,]+\.?\d+)",
        ]
        for pattern in total_patterns:
            total = self._extract_regex(markdown, pattern)
            if total:
                invoice.total = self._parse_decimal(total)
                logger.debug(f"Extracted total {invoice.total} using pattern: {pattern}")
                break

        # Validate we have at least a total
        if not invoice.total:
            invoice.add_error("Could not extract total amount")
            logger.warning(f"Total not found in {invoice.source_file}")

        # Set defaults if not found
        if not invoice.subtotal:
            invoice.subtotal = invoice.total or Decimal("0")

        if invoice.sales_tax is None:
            invoice.sales_tax = Decimal("0.00")
