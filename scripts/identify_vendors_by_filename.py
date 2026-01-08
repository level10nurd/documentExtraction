"""Quick vendor identification based on filename patterns (no document conversion needed)."""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from models.vendor import VendorType


def identify_vendor_from_filename(filename: str) -> Tuple[VendorType, float]:
    """
    Identify vendor from filename patterns.

    Args:
        filename: PDF filename

    Returns:
        Tuple of (VendorType, confidence_score)
    """
    filename_lower = filename.lower()

    # REFLEX MEDICAL CORP - very clear from filename
    if "reflex" in filename_lower or "reflex_medical_corp" in filename_lower:
        return VendorType.REFLEX_MEDICAL, 1.0

    # Sunset Press / VoChill invoices
    if "vochill" in filename_lower:
        return VendorType.SUNSET_PRESS, 0.9

    # Pride Printing
    if "pride_printing" in filename_lower:
        # Add to patterns if this is a new vendor
        return VendorType.UNKNOWN, 0.7  # Mark for manual review

    # Digital Commerce Corporation
    if "digital_commerce" in filename_lower:
        return VendorType.UNKNOWN, 0.7  # Mark for manual review

    # Wolverine patterns (based on bill numbers)
    # Bill_110458_110458.pdf, Bill_95293_95293.pdf format
    if re.match(r"Bill_\d{5,6}_\d{5,6}\.pdf", filename):
        return VendorType.WOLVERINE_PRINTING, 0.6

    # OMICO patterns (based on bill numbers)
    # Bill_96206_96206.pdf format (96xxx range might be OMICO)
    if re.match(r"Bill_96\d{3}_96\d{3}\.pdf", filename):
        return VendorType.OMICO, 0.5

    # Invoice number patterns that might indicate specific vendors
    # Bill_0009xxx - specific vendor pattern
    if re.match(r"Bill_000\d{4}_", filename):
        return VendorType.UNKNOWN, 0.4

    # Other patterns
    if "invoice" in filename_lower:
        return VendorType.UNKNOWN, 0.3

    return VendorType.UNKNOWN, 0.2


def scan_directory(directory: Path) -> List[Dict]:
    """Scan directory and identify vendors from filenames."""
    pdf_files = sorted(directory.glob("*.pdf"))
    results = []

    for pdf_path in pdf_files:
        vendor, confidence = identify_vendor_from_filename(pdf_path.name)

        result = {
            "filename": pdf_path.name,
            "path": str(pdf_path),
            "vendor": vendor.value,
            "confidence": round(confidence, 2),
            "method": "filename_pattern",
        }
        results.append(result)

    return results


def generate_statistics(results: List[Dict]) -> Dict:
    """Generate vendor statistics from results."""
    stats = {
        "total_invoices": len(results),
        "by_vendor": {},
        "by_confidence": {
            "high": 0,  # >= 0.8
            "medium": 0,  # 0.5 - 0.79
            "low": 0,  # < 0.5
        },
    }

    for result in results:
        vendor = result["vendor"]
        stats["by_vendor"][vendor] = stats["by_vendor"].get(vendor, 0) + 1

        confidence = result.get("confidence", 0)
        if confidence >= 0.8:
            stats["by_confidence"]["high"] += 1
        elif confidence >= 0.5:
            stats["by_confidence"]["medium"] += 1
        else:
            stats["by_confidence"]["low"] += 1

    return stats


def print_statistics(stats: Dict, results: List[Dict]) -> None:
    """Print vendor identification statistics."""
    print()
    print("=" * 80)
    print("VENDOR IDENTIFICATION STATISTICS (Filename-Based)")
    print("=" * 80)
    print()

    print(f"Total Invoices: {stats['total_invoices']}")
    print()

    print("By Vendor:")
    print("-" * 80)
    for vendor, count in sorted(
        stats["by_vendor"].items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (count / stats["total_invoices"]) * 100
        print(f"  {vendor:30s} {count:3d} ({percentage:5.1f}%)")
    print()

    print("By Confidence Level:")
    print("-" * 80)
    for level, count in stats["by_confidence"].items():
        percentage = (count / stats["total_invoices"]) * 100
        print(f"  {level.capitalize():10s} {count:3d} ({percentage:5.1f}%)")
    print()

    # Show samples for each vendor
    print("Sample Files by Vendor:")
    print("-" * 80)
    for vendor in sorted(set(r["vendor"] for r in results)):
        vendor_files = [r for r in results if r["vendor"] == vendor]
        print(f"\n{vendor} ({len(vendor_files)} files):")
        for inv in vendor_files[:3]:  # Show first 3
            print(f"  {inv['filename']:50s} (conf: {inv['confidence']:.2f})")
        if len(vendor_files) > 3:
            print(f"  ... and {len(vendor_files) - 3} more")

    print()
    print("=" * 80)


def main():
    """Main entry point."""
    from config import Config

    directory = Config.SOURCE_DIR
    output_file = Path("vendor_manifest_by_filename.json")

    print()
    print("=" * 80)
    print("QUICK VENDOR IDENTIFICATION (Filename Patterns)")
    print("=" * 80)
    print()
    print(f"Source Directory: {directory}")
    print(f"Output Manifest:  {output_file}")
    print()

    # Scan directory
    results = scan_directory(directory)

    # Generate statistics
    stats = generate_statistics(results)

    # Create manifest
    from datetime import datetime

    manifest = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "method": "filename_pattern_matching",
        "statistics": stats,
        "invoices": results,
    }

    # Save manifest
    with open(output_file, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✓ Scanned {len(results)} PDF files")
    print(f"✓ Manifest saved to {output_file}")

    # Display statistics
    print_statistics(stats, results)

    print()
    print("Next Steps:")
    print(
        "  1. Review the vendor assignments (especially Unknown and medium/low confidence)"
    )
    print("  2. Manually verify a few samples from each vendor")
    print("  3. Update the manifest JSON file if needed")
    print(
        "  4. Use for extraction: python main.py --manifest vendor_manifest_by_filename.json"
    )
    print()


if __name__ == "__main__":
    main()
