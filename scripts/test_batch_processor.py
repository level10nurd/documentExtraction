"""Test script for batch processor - processes a small subset of invoices."""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config  # noqa: E402
from processors.batch_processor import BatchProcessor  # noqa: E402
from utils.logging_config import setup_logging  # noqa: E402

# Setup logging
setup_logging()


def main():
    """Test batch processor with a small sample of invoices."""
    print()
    print("=" * 80)
    print("BATCH PROCESSOR TEST")
    print("=" * 80)
    print()

    # Initialize batch processor
    processor = BatchProcessor(num_workers=4)

    # Test with Reflex vendor directory (has 100+ invoices)
    test_dir = Config.SOURCE_DIR / "Reflex"

    print(f"Input Directory: {test_dir}")
    print("Workers: 4")
    print("Processing first 10 Reflex Medical invoices as test...")
    print()

    # Process small batch
    result = processor.process_directory(
        directory=test_dir,
        max_files=10,  # Test with first 10 files
    )

    # Print summary
    processor.print_summary(result)

    # Save detailed results to JSON
    output_file = Path("output/batch_test_results.json")
    output_file.parent.mkdir(exist_ok=True)

    # Convert to dict and save (excluding actual Invoice objects for readability)
    result_dict = result.model_dump(exclude={"results": {"__all__": {"invoice"}}})

    with open(output_file, "w") as f:
        json.dump(result_dict, f, indent=2, default=str)

    print(f"Detailed results saved to: {output_file}")
    print()

    # Show sample of successful extractions
    successful = result.get_successful_invoices()
    if successful:
        print(f"Sample Successful Extraction ({successful[0].vendor}):")
        print("-" * 80)
        print(f"  Invoice #: {successful[0].invoice_number}")
        print(f"  Date:      {successful[0].invoice_date}")
        print(f"  Total:     ${successful[0].total}")
        print(f"  Line Items: {len(successful[0].line_items)}")
        print()

    # Show failed files if any
    failed = result.get_failed_results()
    if failed:
        print(f"Failed Files ({len(failed)}):")
        print("-" * 80)
        for fail in failed[:5]:
            print(f"  {fail.filename:50s} - {fail.status.value}")
            if fail.error_message:
                print(f"    {fail.error_message[:70]}")
        if len(failed) > 5:
            print(f"  ... and {len(failed) - 5} more")
        print()


if __name__ == "__main__":
    main()
