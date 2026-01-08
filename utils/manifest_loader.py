"""Utility to load and query vendor manifest."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from models.vendor import VendorType


class VendorManifest:
    """Vendor manifest loader and query interface."""

    def __init__(self, manifest_path: Path):
        """
        Load vendor manifest from JSON file.

        Args:
            manifest_path: Path to manifest JSON file
        """
        self.manifest_path = manifest_path
        with open(manifest_path) as f:
            self.data = json.load(f)

        # Build lookup index for fast queries
        self._build_index()

    def _build_index(self):
        """Build filename -> invoice mapping for fast lookups."""
        self.by_filename = {}
        self.by_vendor = {}

        for invoice in self.data["invoices"]:
            filename = invoice["filename"]
            vendor = invoice["vendor"]

            self.by_filename[filename] = invoice

            if vendor not in self.by_vendor:
                self.by_vendor[vendor] = []
            self.by_vendor[vendor].append(invoice)

    def get_vendor_for_file(self, filename: str) -> Optional[VendorType]:
        """
        Get vendor type for a specific filename.

        Args:
            filename: PDF filename (basename only)

        Returns:
            VendorType or None if not found
        """
        invoice = self.by_filename.get(filename)
        if not invoice:
            return None

        vendor_str = invoice.get("vendor", "Unknown")
        try:
            return VendorType(vendor_str)
        except ValueError:
            return VendorType.UNKNOWN

    def get_files_for_vendor(self, vendor: VendorType) -> List[str]:
        """
        Get all filenames for a specific vendor.

        Args:
            vendor: VendorType to query

        Returns:
            List of filenames
        """
        invoices = self.by_vendor.get(vendor.value, [])
        return [inv["filename"] for inv in invoices]

    def get_invoice_metadata(self, filename: str) -> Optional[Dict]:
        """
        Get full metadata for an invoice.

        Args:
            filename: PDF filename

        Returns:
            Invoice metadata dict or None
        """
        return self.by_filename.get(filename)

    def get_statistics(self) -> Dict:
        """Get manifest statistics."""
        return self.data.get("statistics", {})

    def get_high_confidence_files(self, min_confidence: float = 0.8) -> List[str]:
        """
        Get filenames with confidence above threshold.

        Args:
            min_confidence: Minimum confidence threshold

        Returns:
            List of high-confidence filenames
        """
        return [
            inv["filename"]
            for inv in self.data["invoices"]
            if inv.get("confidence", 0) >= min_confidence
        ]

    def get_files_needing_review(self, max_confidence: float = 0.6) -> List[str]:
        """
        Get filenames that need manual review.

        Args:
            max_confidence: Maximum confidence for review

        Returns:
            List of filenames needing review
        """
        return [
            inv["filename"]
            for inv in self.data["invoices"]
            if inv.get("confidence", 0) < max_confidence
        ]

    def get_all_filenames(self) -> List[str]:
        """Get all invoice filenames in manifest."""
        return list(self.by_filename.keys())

    def filter_by_vendor(
        self, vendors: List[VendorType], min_confidence: float = 0.0
    ) -> List[str]:
        """
        Filter filenames by vendor list and optional confidence.

        Args:
            vendors: List of VendorTypes to include
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching filenames
        """
        vendor_values = [v.value for v in vendors]
        return [
            inv["filename"]
            for inv in self.data["invoices"]
            if inv.get("vendor") in vendor_values
            and inv.get("confidence", 0) >= min_confidence
        ]

    def print_summary(self):
        """Print manifest summary."""
        stats = self.get_statistics()

        print("\n" + "=" * 80)
        print("VENDOR MANIFEST SUMMARY")
        print("=" * 80)
        print(f"\nTotal Invoices: {stats.get('total_invoices', 0)}")
        print("\nBy Vendor:")
        print("-" * 80)

        for vendor, count in sorted(
            stats.get("by_vendor", {}).items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / stats["total_invoices"]) * 100
            print(f"  {vendor:30s} {count:3d} ({pct:5.1f}%)")

        print("\nBy Confidence:")
        print("-" * 80)
        for level, count in stats.get("by_confidence", {}).items():
            pct = (count / stats["total_invoices"]) * 100
            print(f"  {level.capitalize():10s} {count:3d} ({pct:5.1f}%)")

        print("\n" + "=" * 80)


# Convenience function
def load_manifest(
    manifest_path: str | Path = "vendor_manifest_by_filename.json",
) -> VendorManifest:
    """
    Load vendor manifest from file.

    Args:
        manifest_path: Path to manifest file

    Returns:
        VendorManifest instance
    """
    return VendorManifest(Path(manifest_path))
