"""CSV export functionality for invoice data."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config
from models import Invoice
from utils import get_logger

logger = get_logger(__name__)


class CSVExporter:
    """Export invoice data to CSV format."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        format_type: str = "normalized",
        include_duplicates: bool = False,
    ):
        """
        Initialize CSV exporter.

        Args:
            output_dir: Directory for output files (defaults to Config.OUTPUT_DIR)
            format_type: Export format - "normalized" or "denormalized"
            include_duplicates: Whether to include duplicate invoices
        """
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.format_type = format_type
        self.include_duplicates = include_duplicates
        logger.info(
            f"Initialized CSVExporter: format={format_type}, "
            f"include_duplicates={include_duplicates}"
        )

    def export(
        self, invoices: list[Invoice], filename_prefix: str = "invoices"
    ) -> dict[str, Path]:
        """
        Export invoices to CSV.

        Args:
            invoices: List of Invoice objects to export
            filename_prefix: Prefix for output filenames

        Returns:
            Dictionary mapping file type to output path
        """
        # Filter duplicates if needed
        if not self.include_duplicates:
            invoices = [inv for inv in invoices if not inv.is_duplicate]
            logger.info(f"Filtered to {len(invoices)} non-duplicate invoices")

        if not invoices:
            logger.warning("No invoices to export")
            return {}

        if self.format_type == "normalized":
            return self._export_normalized(invoices, filename_prefix)
        else:
            return self._export_denormalized(invoices, filename_prefix)

    def _export_normalized(
        self, invoices: list[Invoice], filename_prefix: str
    ) -> dict[str, Path]:
        """
        Export in normalized format (separate invoice and line item files).

        Args:
            invoices: List of invoices to export
            filename_prefix: Prefix for output filenames

        Returns:
            Dictionary with 'invoices' and 'line_items' file paths
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        invoice_file = self.output_dir / f"{filename_prefix}_{timestamp}.csv"
        line_items_file = (
            self.output_dir / f"{filename_prefix}_line_items_{timestamp}.csv"
        )

        # Export invoice headers
        invoice_headers = [
            "invoice_id",
            "vendor",
            "invoice_date",
            "invoice_number",
            "po_number",
            "subtotal",
            "sales_tax",
            "total",
            "source_file",
            "extraction_confidence",
            "extraction_errors",
            "duplicate_files",
        ]

        logger.info(f"Writing {len(invoices)} invoices to {invoice_file}")
        with open(invoice_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=invoice_headers)
            writer.writeheader()

            for idx, invoice in enumerate(invoices, start=1):
                invoice_id = f"INV_{idx:05d}"
                writer.writerow(
                    {
                        "invoice_id": invoice_id,
                        "vendor": invoice.vendor.value,
                        "invoice_date": (
                            invoice.invoice_date.strftime(Config.DATE_FORMAT)
                            if invoice.invoice_date
                            else ""
                        ),
                        "invoice_number": invoice.invoice_number,
                        "po_number": invoice.po_number or "",
                        "subtotal": (
                            f"{invoice.subtotal:.2f}" if invoice.subtotal else ""
                        ),
                        "sales_tax": (
                            f"{invoice.sales_tax:.2f}" if invoice.sales_tax else ""
                        ),
                        "total": f"{invoice.total:.2f}",
                        "source_file": invoice.source_file,
                        "extraction_confidence": f"{invoice.extraction_confidence:.2f}",
                        "extraction_errors": "; ".join(invoice.extraction_errors),
                        "duplicate_files": "; ".join(invoice.duplicate_files),
                    }
                )

        # Export line items
        line_item_headers = [
            "invoice_id",
            "line_number",
            "quantity",
            "item_code",
            "description",
            "price_each",
            "amount",
        ]

        total_line_items = sum(len(inv.line_items) for inv in invoices)
        logger.info(f"Writing {total_line_items} line items to {line_items_file}")

        with open(line_items_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=line_item_headers)
            writer.writeheader()

            for idx, invoice in enumerate(invoices, start=1):
                invoice_id = f"INV_{idx:05d}"
                for line_num, item in enumerate(invoice.line_items, start=1):
                    writer.writerow(
                        {
                            "invoice_id": invoice_id,
                            "line_number": line_num,
                            "quantity": (
                                f"{item.quantity:.2f}" if item.quantity else ""
                            ),
                            "item_code": item.item_code or "",
                            "description": item.description,
                            "price_each": (
                                f"{item.price_each:.2f}" if item.price_each else ""
                            ),
                            "amount": f"{item.amount:.2f}",
                        }
                    )

        logger.info("Normalized export complete")
        return {"invoices": invoice_file, "line_items": line_items_file}

    def _export_denormalized(
        self, invoices: list[Invoice], filename_prefix: str
    ) -> dict[str, Path]:
        """
        Export in denormalized format (flat structure with repeated invoice data).

        Args:
            invoices: List of invoices to export
            filename_prefix: Prefix for output filenames

        Returns:
            Dictionary with 'invoices' file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"{filename_prefix}_{timestamp}.csv"

        headers = [
            "vendor",
            "invoice_date",
            "invoice_number",
            "po_number",
            "line_number",
            "quantity",
            "item_code",
            "description",
            "price_each",
            "amount",
            "subtotal",
            "sales_tax",
            "total",
            "source_file",
            "extraction_confidence",
            "extraction_errors",
            "duplicate_files",
        ]

        total_rows = sum(
            len(inv.line_items) if inv.line_items else 1 for inv in invoices
        )
        logger.info(f"Writing {total_rows} rows to {output_file}")

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for invoice in invoices:
                # Invoice-level data that repeats for each line item
                base_row = {
                    "vendor": invoice.vendor.value,
                    "invoice_date": (
                        invoice.invoice_date.strftime(Config.DATE_FORMAT)
                        if invoice.invoice_date
                        else ""
                    ),
                    "invoice_number": invoice.invoice_number,
                    "po_number": invoice.po_number or "",
                    "subtotal": f"{invoice.subtotal:.2f}" if invoice.subtotal else "",
                    "sales_tax": (
                        f"{invoice.sales_tax:.2f}" if invoice.sales_tax else ""
                    ),
                    "total": f"{invoice.total:.2f}",
                    "source_file": invoice.source_file,
                    "extraction_confidence": f"{invoice.extraction_confidence:.2f}",
                    "extraction_errors": "; ".join(invoice.extraction_errors),
                    "duplicate_files": "; ".join(invoice.duplicate_files),
                }

                # If invoice has no line items, write a single row
                if not invoice.line_items:
                    writer.writerow(
                        {
                            **base_row,
                            "line_number": "",
                            "quantity": "",
                            "item_code": "",
                            "description": "",
                            "price_each": "",
                            "amount": "",
                        }
                    )
                else:
                    # Write a row for each line item
                    for line_num, item in enumerate(invoice.line_items, start=1):
                        writer.writerow(
                            {
                                **base_row,
                                "line_number": line_num,
                                "quantity": (
                                    f"{item.quantity:.2f}" if item.quantity else ""
                                ),
                                "item_code": item.item_code or "",
                                "description": item.description,
                                "price_each": (
                                    f"{item.price_each:.2f}" if item.price_each else ""
                                ),
                                "amount": f"{item.amount:.2f}",
                            }
                        )

        logger.info("Denormalized export complete")
        return {"invoices": output_file}

    def export_summary(self, invoices: list[Invoice]) -> Path:
        """
        Export a summary report with statistics.

        Args:
            invoices: List of invoices to summarize

        Returns:
            Path to summary CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.output_dir / f"summary_{timestamp}.csv"

        # Calculate statistics
        total_count = len(invoices)
        duplicate_count = sum(1 for inv in invoices if inv.is_duplicate)
        unique_count = total_count - duplicate_count

        # Vendor breakdown
        vendor_counts = {}
        vendor_totals = {}
        for inv in invoices:
            vendor = inv.vendor.value
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
            vendor_totals[vendor] = vendor_totals.get(vendor, 0) + float(inv.total)

        # Confidence breakdown
        low_confidence = sum(1 for inv in invoices if inv.extraction_confidence < 0.6)
        medium_confidence = sum(
            1 for inv in invoices if 0.6 <= inv.extraction_confidence < 0.8
        )
        high_confidence = sum(1 for inv in invoices if inv.extraction_confidence >= 0.8)

        logger.info(f"Writing summary to {summary_file}")
        with open(summary_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Invoice Processing Summary"])
            writer.writerow([])
            writer.writerow(["Total Invoices", total_count])
            writer.writerow(["Unique Invoices", unique_count])
            writer.writerow(["Duplicate Invoices", duplicate_count])
            writer.writerow([])
            writer.writerow(["Confidence Distribution"])
            writer.writerow(["High (≥0.8)", high_confidence])
            writer.writerow(["Medium (0.6-0.8)", medium_confidence])
            writer.writerow(["Low (<0.6)", low_confidence])
            writer.writerow([])
            writer.writerow(["Vendor", "Count", "Total Amount"])
            for vendor in sorted(vendor_counts.keys()):
                writer.writerow(
                    [vendor, vendor_counts[vendor], f"${vendor_totals[vendor]:.2f}"]
                )

        logger.info("Summary export complete")
        return summary_file
