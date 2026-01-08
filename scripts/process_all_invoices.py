"""Process all invoices from all vendors and export to CSV."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config  # noqa: E402
from exporters import CSVExporter, SummaryGenerator  # noqa: E402
from processors.batch_processor import BatchProcessor  # noqa: E402
from utils.logging_config import setup_logging  # noqa: E402
import time  # noqa: E402

# Setup logging
setup_logging()


def main():
    """Process all invoices from all vendor directories."""
    # Load environment configuration
    try:
        env_name = Config.load_environment()
        print()
        print("=" * 80)
        print("PROCESSING ALL INVOICES")
        print("=" * 80)
        print()
        print(f"Environment:      {env_name}")
        print(f"Source Directory: {Config.SOURCE_DIR}")
        print(f"Output Directory: {Config.OUTPUT_DIR}")
        print()
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        print("Please check your environments.json configuration")
        sys.exit(1)

    # Create single output directory for this run
    from datetime import datetime
    combined_run_dir = Config.OUTPUT_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    combined_run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output Directory: {combined_run_dir}")
    print()

    # Initialize batch processor
    processor = BatchProcessor(num_workers=8, output_dir=Config.OUTPUT_DIR)
    # Set the run directory explicitly to prevent creating subdirectories
    processor.run_dir = combined_run_dir

    # Start timing
    start_time = time.time()

    # Get all vendor directories
    vendor_dirs = Config.get_all_vendor_directories()

    print(f"Found {len(vendor_dirs)} vendor directories:")
    for vendor, path in vendor_dirs.items():
        if path.exists():
            pdf_count = len(list(path.glob("*.pdf")))
            print(f"  {vendor.value:30s} - {pdf_count} PDFs")
        else:
            print(f"  {vendor.value:30s} - [DIRECTORY NOT FOUND]")
    print()

    # Process each vendor directory
    all_results = []

    for vendor, vendor_dir in vendor_dirs.items():
        if not vendor_dir.exists():
            print(f"⚠️  Skipping {vendor.value} - directory not found")
            continue

        pdf_files = list(vendor_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"⚠️  Skipping {vendor.value} - no PDF files found")
            continue

        print()
        print("-" * 80)
        print(f"Processing {vendor.value} ({len(pdf_files)} invoices)")
        print("-" * 80)

        result = processor.process_directory(vendor_dir)
        all_results.append(result)

        # Print vendor summary
        print(f"✅ {vendor.value}: {result.statistics.successful}/{result.statistics.total_files} successful")

    # Combine all successful invoices
    print()
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print()

    total_processed = sum(r.statistics.total_files for r in all_results)
    total_successful = sum(r.statistics.successful for r in all_results)
    total_failed = total_processed - total_successful

    print(f"Total Files Processed: {total_processed}")

    if total_processed > 0:
        print(f"Successful:           {total_successful} ({total_successful/total_processed*100:.1f}%)")
        print(f"Failed:               {total_failed} ({total_failed/total_processed*100:.1f}%)")
    else:
        print(f"Successful:           {total_successful}")
        print(f"Failed:               {total_failed}")
        print()
        print("⚠️  No files were processed. Check vendor directories.")
        sys.exit(1)

    print()

    # Collect all successful invoices
    all_invoices = []
    for result in all_results:
        all_invoices.extend(result.get_successful_invoices())

    print(f"Collected {len(all_invoices)} invoices for export")
    print()

    if not all_invoices:
        print("⚠️  No invoices to export!")
        return

    # Export to CSV (using the shared output directory)
    print("=" * 80)
    print("EXPORTING TO CSV")
    print("=" * 80)
    print()

    # Export normalized format (separate files for invoices and line items)
    exporter = CSVExporter(
        format_type="normalized",
        include_duplicates=False,
        output_dir=combined_run_dir
    )

    print("Exporting normalized format (invoices + line_items)...")
    files = exporter.export(all_invoices, filename_prefix="all_invoices")

    for file_type, file_path in files.items():
        print(f"  ✅ {file_type:12s}: {file_path}")

    # Export summary report
    print("\nGenerating summary report...")
    summary_file = exporter.export_summary(all_invoices)
    print(f"  ✅ summary      : {summary_file}")

    # Export denormalized format (flat file)
    print("\nExporting denormalized format (single flat file)...")
    denorm_exporter = CSVExporter(
        format_type="denormalized",
        include_duplicates=False,
        output_dir=combined_run_dir
    )
    denorm_files = denorm_exporter.export(all_invoices, filename_prefix="all_invoices_flat")

    for file_type, file_path in denorm_files.items():
        print(f"  ✅ {file_type:12s}: {file_path}")

    # Generate batch summary report
    print()
    print("=" * 80)
    print("GENERATING BATCH SUMMARY")
    print("=" * 80)
    print()

    end_time = time.time()
    total_processing_time = end_time - start_time

    summary_gen = SummaryGenerator(output_dir=combined_run_dir)
    summary_file = summary_gen.generate_summary(
        batch_results=all_results,
        all_invoices=all_invoices,
        processing_time=total_processing_time,
    )

    print(f"  ✅ Batch Summary: {summary_file.name}")
    print()

    print("=" * 80)
    print("COMPLETE! 🎉")
    print("=" * 80)
    print()
    print(f"Successfully processed and exported {len(all_invoices)} invoices")
    print(f"Total processing time: {total_processing_time:.1f}s")
    print()
    print(f"📁 All outputs saved to: {combined_run_dir}")
    print(f"📊 Review batch summary: {summary_file.name}")
    print()


if __name__ == "__main__":
    main()
