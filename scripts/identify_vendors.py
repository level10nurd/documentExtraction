"""Vendor identification script - scans all invoices and generates a manifest."""

import json
import sys
from pathlib import Path
from typing import Dict, List

from tqdm import tqdm

from config import Config
from models.vendor import VENDOR_PATTERNS, VendorType
from processors.document_processor import DocumentProcessor
from utils.logging_config import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)


def identify_vendor_from_markdown(
    markdown: str, filename: str
) -> tuple[VendorType, float]:
    """
    Identify vendor from document markdown content.

    Args:
        markdown: Document content in markdown format
        filename: Original filename for fallback detection

    Returns:
        Tuple of (VendorType, confidence_score)
    """
    # Score each vendor based on pattern matches
    vendor_scores = {}

    for vendor_type, patterns in VENDOR_PATTERNS.items():
        matches = 0
        for pattern in patterns:
            if pattern.search(markdown):
                matches += 1

        if matches > 0:
            vendor_scores[vendor_type] = matches

    # Check filename patterns as secondary signal
    filename_lower = filename.lower()
    if "vochill" in filename_lower:
        vendor_scores[VendorType.SUNSET_PRESS] = (
            vendor_scores.get(VendorType.SUNSET_PRESS, 0) + 0.5
        )

    if "reflex" in filename_lower:
        vendor_scores[VendorType.REFLEX_MEDICAL] = (
            vendor_scores.get(VendorType.REFLEX_MEDICAL, 0) + 0.5
        )

    # Select vendor with highest score
    if not vendor_scores:
        logger.warning(f"No vendor patterns matched for {filename}")
        return VendorType.UNKNOWN, 0.3

    best_vendor = max(vendor_scores, key=vendor_scores.get)
    score = vendor_scores[best_vendor]

    # Calculate confidence
    if score >= 3:
        confidence = 1.0  # High confidence
    elif score >= 2:
        confidence = 0.8  # Medium confidence
    elif score >= 1:
        confidence = 0.6  # Low confidence
    else:
        confidence = 0.4

    return best_vendor, confidence


def scan_invoices(directory: Path, max_invoices: int = None) -> List[Dict]:
    """
    Scan all PDF invoices in directory and identify vendors.

    Args:
        directory: Directory containing PDF invoices
        max_invoices: Optional limit on number of invoices to scan

    Returns:
        List of invoice metadata dictionaries
    """
    # Get all PDF files
    pdf_files = sorted(directory.glob("*.pdf"))

    if max_invoices:
        pdf_files = pdf_files[:max_invoices]

    logger.info(f"Found {len(pdf_files)} PDF files to scan")

    # Initialize document processor
    processor = DocumentProcessor()

    # Scan each invoice
    results = []

    for pdf_path in tqdm(pdf_files, desc="Scanning invoices"):
        try:
            # Convert document
            doc_key = processor.convert_document(pdf_path)

            # Get markdown for vendor detection
            markdown = processor.get_document_markdown(doc_key, max_size=3000)

            # Identify vendor
            vendor, confidence = identify_vendor_from_markdown(markdown, pdf_path.name)

            # Create result entry
            result = {
                "filename": pdf_path.name,
                "path": str(pdf_path),
                "vendor": vendor.value,
                "confidence": round(confidence, 2),
                "doc_key": doc_key,
            }

            results.append(result)

            logger.debug(
                f"✓ {pdf_path.name}: {vendor.value} (confidence: {confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            # Add as unknown
            results.append(
                {
                    "filename": pdf_path.name,
                    "path": str(pdf_path),
                    "vendor": VendorType.UNKNOWN.value,
                    "confidence": 0.0,
                    "error": str(e),
                }
            )

    return results


def generate_manifest(results: List[Dict], output_path: Path) -> None:
    """
    Generate vendor manifest file from scan results.

    Args:
        results: List of invoice scan results
        output_path: Path to save manifest file
    """
    # Generate statistics
    stats = {
        "total_invoices": len(results),
        "by_vendor": {},
        "by_confidence": {
            "high": 0,  # >= 0.8
            "medium": 0,  # 0.6 - 0.79
            "low": 0,  # < 0.6
        },
    }

    # Count by vendor
    for result in results:
        vendor = result["vendor"]
        stats["by_vendor"][vendor] = stats["by_vendor"].get(vendor, 0) + 1

        # Count by confidence
        confidence = result.get("confidence", 0)
        if confidence >= 0.8:
            stats["by_confidence"]["high"] += 1
        elif confidence >= 0.6:
            stats["by_confidence"]["medium"] += 1
        else:
            stats["by_confidence"]["low"] += 1

    # Create manifest
    manifest = {
        "version": "1.0",
        "generated_at": None,  # Will be set when saved
        "statistics": stats,
        "invoices": results,
    }

    # Add timestamp
    from datetime import datetime

    manifest["generated_at"] = datetime.now().isoformat()

    # Save as JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest saved to {output_path}")


def print_statistics(manifest: Dict) -> None:
    """Print vendor identification statistics."""
    stats = manifest["statistics"]

    print()
    print("=" * 80)
    print("VENDOR IDENTIFICATION STATISTICS")
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

    # Show low confidence invoices that need review
    low_conf_invoices = [
        inv for inv in manifest["invoices"] if inv.get("confidence", 0) < 0.6
    ]

    if low_conf_invoices:
        print("Low Confidence Invoices (need manual review):")
        print("-" * 80)
        for inv in low_conf_invoices:
            print(
                f"  {inv['filename']:50s} {inv['vendor']:20s} "
                f"(conf: {inv.get('confidence', 0):.2f})"
            )
        print()

    print("=" * 80)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Identify vendors for all invoice PDFs and generate manifest"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Config.SOURCE_DIR,
        help="Directory containing PDF invoices",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("vendor_manifest.json"),
        help="Output manifest file path",
    )
    parser.add_argument(
        "--max-invoices",
        type=int,
        help="Limit number of invoices to scan (for testing)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only display statistics from existing manifest",
    )

    args = parser.parse_args()

    # If stats-only mode, load and display existing manifest
    if args.stats_only:
        if not args.output.exists():
            print(f"Error: Manifest file not found: {args.output}")
            sys.exit(1)

        with open(args.output) as f:
            manifest = json.load(f)

        print_statistics(manifest)
        sys.exit(0)

    # Verify source directory exists
    if not args.input_dir.exists():
        print(f"Error: Source directory not found: {args.input_dir}")
        sys.exit(1)

    print()
    print("=" * 80)
    print("INVOICE VENDOR IDENTIFICATION")
    print("=" * 80)
    print()
    print(f"Source Directory: {args.input_dir}")
    print(f"Output Manifest:  {args.output}")
    if args.max_invoices:
        print(f"Limit:            {args.max_invoices} invoices")
    print()

    # Scan invoices
    results = scan_invoices(args.input_dir, args.max_invoices)

    # Generate manifest
    generate_manifest(results, args.output)

    # Load and display statistics
    with open(args.output) as f:
        manifest = json.load(f)

    print_statistics(manifest)

    print()
    print("✅ Vendor identification complete!")
    print(f"📄 Manifest saved to: {args.output}")
    print()
    print("Next steps:")
    print("  1. Review low-confidence invoices and update manifest manually if needed")
    print(
        "  2. Use manifest for batch extraction: python main.py --manifest vendor_manifest.json"
    )


if __name__ == "__main__":
    main()
