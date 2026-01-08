"""Dimax Corporation invoice extractor."""

import logging
import re
from decimal import Decimal

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class DimaxExtractor(BaseExtractor):
    """Extractor for Dimax Corporation invoices."""

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from Dimax Corporation document.

        Dimax invoices have a simple structure:
        - Header with "Dimax Corporation" and company info
        - Invoice metadata: Invoice Number, Date, PO Number, Customer, etc.
        - Single line item table with Item, Quantity, Description, Unit Price, Amount, Revision
        - Totals: Sub-total, Sales Tax, Shipping, Invoice Total, Paid To Date, Balance Due

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.DIMAX, filename)

        try:
            # Extract invoice metadata
            self._extract_invoice_metadata(markdown, invoice)

            # Extract line items
            self._extract_line_items(markdown, invoice)

            # Extract totals
            self._extract_totals(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted Dimax invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting Dimax invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_metadata(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number, date, and PO number."""
        # In Dimax invoices, the values often appear BEFORE the labels due to Docling parsing
        # Pattern: "56639\n\nInvoice Number:" OR "Invoice Number:\n\n56639"

        lines = markdown.split("\n")

        # Find Invoice Number
        for i, line in enumerate(lines):
            if "Invoice Number" in line:
                # Check if number is on the same line
                num_on_line = re.search(
                    r"Invoice\s+Number:\s*(\d+)", line, re.IGNORECASE
                )
                if num_on_line:
                    invoice.invoice_number = num_on_line.group(1).strip()
                    break

                # Check previous lines (value before label)
                for j in range(max(0, i - 3), i):
                    if lines[j].strip().isdigit():
                        invoice.invoice_number = lines[j].strip()
                        break

                # Check next lines (value after label)
                if not invoice.invoice_number:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        if lines[j].strip().isdigit():
                            invoice.invoice_number = lines[j].strip()
                            break
                break

        if not invoice.invoice_number:
            invoice.add_error("Could not extract invoice number")
            logger.warning(f"Invoice number not found in {invoice.source_file}")

        # Find Invoice Date
        # The date in Dimax invoices may appear many lines before the "Invoice Date:" label
        # Look backwards from the label to find the closest date
        for i, line in enumerate(lines):
            if "Invoice Date" in line:
                # Check if date is on the same line
                date_on_line = re.search(
                    r"Invoice\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})", line, re.IGNORECASE
                )
                if date_on_line:
                    try:
                        from dateutil.parser import parse

                        invoice.invoice_date = parse(date_on_line.group(1)).date()
                        break
                    except Exception:
                        pass

                # Check next lines (value after label) first
                for j in range(i + 1, min(i + 4, len(lines))):
                    date_search = re.search(r"\d{1,2}/\d{1,2}/\d{4}", lines[j])
                    if date_search:
                        try:
                            from dateutil.parser import parse

                            invoice.invoice_date = parse(date_search.group(0)).date()
                            break
                        except Exception:
                            continue

                # Check previous lines (value before label) - look back further
                if not invoice.invoice_date:
                    # Look backwards up to 20 lines to find the date (it may be far away)
                    for j in range(i - 1, max(0, i - 20), -1):
                        date_search = re.search(r"\d{1,2}/\d{1,2}/\d{4}", lines[j])
                        if date_search:
                            try:
                                from dateutil.parser import parse

                                invoice.invoice_date = parse(
                                    date_search.group(0)
                                ).date()
                                break
                            except Exception:
                                continue
                break

        if not invoice.invoice_date:
            invoice.add_error("Could not extract invoice date")
            logger.warning(f"Invoice date not found in {invoice.source_file}")

        # Find PO Number
        for i, line in enumerate(lines):
            if "PO Number" in line:
                # Check if number is on the same line
                po_on_line = re.search(r"PO\s+Number:\s*(\d+)", line, re.IGNORECASE)
                if po_on_line:
                    invoice.po_number = self._clean_po_number(po_on_line.group(1))
                    break

                # Check previous lines (value before label)
                for j in range(max(0, i - 3), i):
                    if lines[j].strip().isdigit():
                        invoice.po_number = self._clean_po_number(lines[j].strip())
                        break

                # Check next lines (value after label)
                if not invoice.po_number:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        if lines[j].strip().isdigit():
                            invoice.po_number = self._clean_po_number(lines[j].strip())
                            break
                break

        if not invoice.po_number:
            logger.debug(f"PO number not found in {invoice.source_file}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from the invoice table."""
        # Dimax line items are spread across multiple lines in the markdown
        # Structure after "## Item":
        # Line 0: ## Item
        # Line 2: Quantity Description
        # Line 4: Unit Price
        # Line 6: Revision
        # Line 8: 2               (multiplier)
        # Line 10: 12574          (actual quantity)
        # Line 12: / EA $0.5871   (unit price)
        # Line 14: 20434 - VoChill Non-slip Pad Dots...  (description)
        # Line 16: $7,382.20      (amount)
        # Line 18: B              (revision)

        lines = markdown.split("\n")

        for i, line in enumerate(lines):
            # Find the "## Item" section
            if line.strip() == "## Item":
                # Collect non-empty lines after the header until we hit "Sub-total"
                item_data_lines = []
                for j in range(i + 1, min(i + 50, len(lines))):
                    if "Sub-total" in lines[j] or "Invoice Total" in lines[j]:
                        break
                    # Skip header lines and empty lines
                    if lines[j].strip() and not any(
                        header in lines[j]
                        for header in [
                            "Quantity",
                            "Description",
                            "Unit Price",
                            "Revision",
                            "Amount",
                        ]
                    ):
                        item_data_lines.append(lines[j].strip())

                if item_data_lines:
                    # Concatenate all item data into a single line for parsing
                    combined_line = " ".join(item_data_lines)
                    self._parse_item_line(combined_line, invoice)
                break

    def _parse_item_line(self, line: str, invoice: Invoice) -> None:
        """
        Parse a line item from Dimax invoice.

        Pattern examples from actual invoices:
        "2 / 12574 / EA $0.5871 20434 - VoChill Non-slip Pad Dots... $7,382.20 B"
        Or multi-line: "2\n\n12574\n\n/ EA $0.5871\n\n20434 - VoChill Non-slip Pad Dots...\n\n$7,382.20\n\nB"

        Args:
            line: Line containing item data
            invoice: Invoice object to add items to
        """
        # Normalize line by removing excess whitespace and newlines
        normalized = " ".join(line.split())

        # Extract quantity - look for pattern like "2 12574" or "2 / 12574"
        # The actual quantity is the larger number
        qty_match = re.search(r"(\d+)\s*(?:/\s*)?\s*(\d+)", normalized)
        quantity = None
        if qty_match:
            # Use the larger number as quantity (12574, not 2)
            num1 = int(qty_match.group(1))
            num2 = int(qty_match.group(2)) if qty_match.group(2) else num1
            quantity = Decimal(max(num1, num2))

        # Item code: Pattern like "20434 -" at the start of description
        item_code_match = re.search(r"(\d{4,5})\s*-", normalized)
        if item_code_match:
            item_code = item_code_match.group(1)
        else:
            item_code = "Unknown"

        # Description: Text after item code until price or revision
        # Look for pattern: "20434 - VoChill Non-slip Pad Dots..."
        desc_match = re.search(r"\d{4,5}\s*-\s*(.+?)(?:\s+\$|$)", normalized, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()
            # Remove trailing single letters (revision codes) and extra whitespace
            description = re.sub(r"\s+[A-Z]\s*$", "", description)
            # Clean up multiple spaces
            description = " ".join(description.split())
        else:
            description = "Unknown"

        # Unit Price: Pattern like "EA $0.5871" or "/ EA $0.5871"
        price_match = re.search(r"EA\s*\$\s*([\d.]+)", normalized)
        price_each = None
        if price_match:
            price_each = self._parse_decimal(price_match.group(1))

        # Amount: Dollar amount that appears after the description
        # Find all dollar amounts and pick the largest (the line total, not unit price)
        amount_matches = re.findall(r"\$\s*([\d,]+\.\d{2})", normalized)
        amount = None
        if amount_matches:
            amounts = [self._parse_decimal(a) for a in amount_matches]
            amounts = [a for a in amounts if a is not None]
            if amounts:
                # The largest value is the line total
                amount = max(amounts)

        # Revision: Single letter, often at the end (e.g., "B")
        # Note: Revision code is extracted but not currently stored in LineItem model
        # revision_match = re.search(r"\b([A-Z])\s*$", normalized)
        # revision = revision_match.group(1) if revision_match else None

        # Create line item
        try:
            item = LineItem(
                item_code=item_code,
                description=description,
                quantity=quantity,
                price_each=price_each,
                amount=amount or Decimal("0"),
            )
            invoice.line_items.append(item)
        except Exception as e:
            logger.warning(f"Failed to create line item: {e}")
            invoice.add_error(f"Failed to parse line item: {e}")

    def _extract_totals(self, markdown: str, invoice: Invoice) -> None:
        """Extract subtotal, sales tax, and total amounts."""
        # Sub-total pattern: "Sub-total:\n\n$7,382.20"
        subtotal_match = re.search(
            r"Sub-total:\s*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if subtotal_match:
            invoice.subtotal = self._parse_decimal(subtotal_match.group(1))
        else:
            logger.debug(f"Subtotal not found in {invoice.source_file}")

        # Sales Tax pattern: "Sales Tax:\n\n$0.00"
        tax_match = re.search(
            r"Sales\s+Tax:\s*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if tax_match:
            invoice.sales_tax = self._parse_decimal(tax_match.group(1))
        else:
            invoice.sales_tax = Decimal("0.00")

        # Invoice Total or Balance Due pattern
        # Try "Invoice Total:" first
        total_match = re.search(
            r"Invoice\s+Total:\s*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )
        if total_match:
            invoice.total = self._parse_decimal(total_match.group(1))
        else:
            # Try "Balance Due:" as fallback
            balance_match = re.search(
                r"Balance\s+Due:\s*\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
            )
            if balance_match:
                invoice.total = self._parse_decimal(balance_match.group(1))
            else:
                invoice.add_error("Could not extract total amount")
                logger.warning(f"Total not found in {invoice.source_file}")
