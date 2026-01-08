"""Test script for CSV exporter - exports batch processing results to CSV."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config  # noqa: E402
from exporters import CSVExporter  # noqa: E402
from processors.batch_processor import BatchProcessor  # noqa: E402
from utils.logging_config import setup_logging  # noqa: E402

# Setup logging
setup_logging()


def main():
    """Test CSV export with batch processor results."""
    print()
    print("=" * 80)
    print("CSV EXPORT TEST")
    print("=" * 80)
    print()

    # Initialize batch processor
    processor = BatchProcessor(num_workers=4)

    # Process small batch from Reflex directory
    test_dir = Config.SOURCE_DIR / "Reflex"
    print(f"Input Directory: {test_dir}")
    print("Processing first 10 Reflex Medical invoices...")
    print()

    result = processor.process_directory(test_dir, max_files=10)

    # Print processing summary
    processor.print_summary(result)

    # Get successful invoices
    invoices = result.get_successful_invoices()

    if not invoices:
        print("\nNo successful invoices to export!")
        return

    print()
    print("=" * 80)
    print("CSV EXPORT")
    print("=" * 80)
    print()
    print(f"Output Directory: {processor.run_dir}")
    print()

    # Test normalized export
    print("Exporting in NORMALIZED format...")
    normalized_exporter = CSVExporter(
        format_type="normalized",
        include_duplicates=False,
        output_dir=processor.run_dir
    )
    normalized_files = normalized_exporter.export(invoices, filename_prefix="test_normalized")

    for file_type, file_path in normalized_files.items():
        print(f"  {file_type:12s}: {file_path}")

    # Test denormalized export
    print("\nExporting in DENORMALIZED format...")
    denorm_exporter = CSVExporter(
        format_type="denormalized",
        include_duplicates=False,
        output_dir=processor.run_dir
    )
    denorm_files = denorm_exporter.export(invoices, filename_prefix="test_denormalized")

    for file_type, file_path in denorm_files.items():
        print(f"  {file_type:12s}: {file_path}")

    # Export summary report
    print("\nExporting SUMMARY report...")
    summary_file = normalized_exporter.export_summary(invoices)
    print(f"  summary     : {summary_file}")

    print()
    print("=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print()
    print(f"Successfully exported {len(invoices)} invoices")
    print(f"Total files created: {len(normalized_files) + len(denorm_files) + 1}")
    print(f"Check the directory: {processor.run_dir}")
    print()


if __name__ == "__main__":
    main()
