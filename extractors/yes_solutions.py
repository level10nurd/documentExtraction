"""YES Solutions LLC invoice extractor."""

import logging
import re
from decimal import Decimal
from typing import Optional

from extractors.base import BaseExtractor
from models.invoice import Invoice, LineItem
from models.vendor import VendorType

logger = logging.getLogger(__name__)


class YesSolutionsExtractor(BaseExtractor):
    """Extractor for YES Solutions LLC invoices."""

    def extract(self, doc_key: str, markdown: str, filename: str) -> Invoice:
        """
        Extract invoice data from YES Solutions document.

        YES Solutions invoices have:
        - Invoice table with invoice number, date, terms, and W/O reference
        - Load details section with shipment info
        - Rates and charges section with line items
        - Total amount in USD

        Args:
            doc_key: Document key from Docling conversion
            markdown: Document content in markdown format
            filename: Original PDF filename

        Returns:
            Extracted Invoice object
        """
        invoice = self._create_base_invoice(VendorType.YES_SOLUTIONS, filename)

        try:
            # Extract invoice header (number, date, terms)
            self._extract_invoice_header(markdown, invoice)

            # Extract load number (used as PO number)
            self._extract_load_number(markdown, invoice)

            # Extract line items from rates and charges
            self._extract_line_items(markdown, invoice)

            # Extract total
            self._extract_totals(markdown, invoice)

            # Calculate confidence
            invoice.extraction_confidence = invoice.calculate_confidence()

            logger.info(
                f"Successfully extracted YES Solutions invoice {invoice.invoice_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting YES Solutions invoice: {e}")
            invoice.add_error(str(e))

        return invoice

    def _extract_invoice_header(self, markdown: str, invoice: Invoice) -> None:
        """Extract invoice number, date, and terms from invoice table."""
        # Look for the invoice table
        # Pattern: | INVOICE #     | 25716      |
        #          | Invoice Date: | 03/11/2024 |
        #          | Terms:        | Net 15     |

        # Extract invoice number
        inv_match = re.search(
            r"\|\s*INVOICE\s*#\s*\|\s*(\d+)\s*\|", markdown, re.IGNORECASE
        )
        if inv_match:
            invoice.invoice_number = inv_match.group(1).strip()
        else:
            invoice.add_error("Could not extract invoice number")
            logger.warning(f"Invoice number not found in {invoice.source_file}")

        # Extract invoice date
        date_match = re.search(
            r"\|\s*Invoice\s+Date:\s*\|\s*(\d{2}/\d{2}/\d{4})\s*\|",
            markdown,
            re.IGNORECASE,
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

        # Extract terms (optional, not a required field in Invoice model)
        terms_match = re.search(
            r"\|\s*Terms:\s*\|\s*([^\|]+)\s*\|", markdown, re.IGNORECASE
        )
        if terms_match:
            terms = terms_match.group(1).strip()
            logger.debug(f"Payment terms: {terms}")

    def _extract_load_number(self, markdown: str, invoice: Invoice) -> None:
        """Extract load number to use as PO number."""
        # Pattern: ## LOAD #: 25716
        load_match = re.search(r"LOAD\s*#:\s*(\d+)", markdown, re.IGNORECASE)
        if load_match:
            invoice.po_number = load_match.group(1).strip()
        else:
            logger.debug(f"Load number not found in {invoice.source_file}")

    def _extract_line_items(self, markdown: str, invoice: Invoice) -> None:
        """Extract line items from rates and charges section."""
        # YES Solutions typically has simple line items
        # Pattern: Line Haul    $672.00
        # Sometimes there's a description with the shipment details

        # Extract the main charge (Line Haul)
        line_haul_match = re.search(
            r"Line\s+Haul\s+\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )

        if line_haul_match:
            amount = self._parse_decimal(line_haul_match.group(1))

            # Try to extract description from load details
            description = self._extract_shipment_description(markdown)

            # Create line item
            line_item = LineItem(
                item_code="LINE_HAUL",
                description=description or "Line Haul Freight Charges",
                quantity=Decimal("1"),
                price_each=amount,
                amount=amount,
            )
            invoice.line_items.append(line_item)
        else:
            invoice.add_error("Could not extract line items")
            logger.warning(f"Line items not found in {invoice.source_file}")

    def _extract_shipment_description(self, markdown: str) -> Optional[str]:
        """Extract shipment description from load details."""
        # Try to extract description from load details
        # Pattern: Description: Freeze Packs 42660
        desc_match = re.search(
            r"Description:\s*\n\n([^\n]+)", markdown, re.IGNORECASE | re.MULTILINE
        )
        if desc_match:
            return desc_match.group(1).strip()

        # Alternative: look for description in the load details table
        desc_match = re.search(
            r"Description:\s+([^\n]+?)(?:\n|Purchase Order)", markdown, re.IGNORECASE
        )
        if desc_match:
            return desc_match.group(1).strip()

        return None

    def _extract_totals(self, markdown: str, invoice: Invoice) -> None:
        """Extract total amount."""
        # Look for Total Rate or the final USD amount
        # Pattern: Total Rate:    $672.00 USD
        # Or:      $672.00 USD

        # Try to find "Total Rate" first
        total_match = re.search(
            r"Total\s+Rate:\s+\$\s*([\d,]+\.?\d*)", markdown, re.IGNORECASE
        )

        if not total_match:
            # Try to find any amount in USD format
            total_match = re.search(
                r"\$\s*([\d,]+\.?\d*)\s+USD", markdown, re.IGNORECASE
            )

        if total_match:
            invoice.total = self._parse_decimal(total_match.group(1))
            invoice.subtotal = invoice.total
            invoice.sales_tax = Decimal("0.00")
        else:
            invoice.add_error("Could not extract total amount")
            logger.warning(f"Total not found in {invoice.source_file}")
