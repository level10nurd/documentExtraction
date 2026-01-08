"""Batch processor for parallel invoice extraction."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from tqdm import tqdm

from config import Config
from extractors.factory import ExtractorFactory
from models.batch_result import (
    BatchResult,
    BatchStatistics,
    InvoiceResult,
    ProcessingStatus,
)
from models.vendor import VendorType
from processors.document_processor import DocumentProcessor
from utils.logging_config import get_logger

logger = get_logger(__name__)


class BatchProcessor:
    """Process multiple invoices in parallel using vendor-specific extractors."""

    def __init__(
        self,
        document_processor: Optional[DocumentProcessor] = None,
        num_workers: int = 4,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize batch processor.

        Args:
            document_processor: Document processor instance (creates new if None)
            num_workers: Number of parallel workers for processing
            output_dir: Base output directory (defaults to Config.OUTPUT_DIR)
        """
        self.document_processor = document_processor or DocumentProcessor()
        self.factory = ExtractorFactory(self.document_processor)
        self.num_workers = num_workers
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.run_dir: Optional[Path] = None  # Set when processing starts
        logger.info(
            f"BatchProcessor initialized with {num_workers} workers, "
            f"{len(self.factory.get_supported_vendors())} supported vendors"
        )

    def _create_run_directory(self) -> Path:
        """
        Create a timestamped directory for this run.

        Returns:
            Path to the created run directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created run directory: {run_dir}")
        return run_dir

    def process_directory(
        self,
        directory: Path,
        file_pattern: str = "*.pdf",
        max_files: Optional[int] = None,
        skip_existing: bool = False,
        progress_callback: Optional[Callable[[InvoiceResult], None]] = None,
    ) -> BatchResult:
        """
        Process all invoices in a directory.

        Args:
            directory: Directory containing invoice PDFs
            file_pattern: Glob pattern for files to process (default: *.pdf)
            max_files: Optional limit on number of files to process
            skip_existing: Skip files that have already been processed
            progress_callback: Optional callback function called after each file

        Returns:
            BatchResult with all processing results and statistics
        """
        directory = Path(directory)
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        # Create timestamped run directory
        self.run_dir = self._create_run_directory()

        # Get list of files to process
        pdf_files = sorted(directory.glob(file_pattern))
        if max_files:
            pdf_files = pdf_files[:max_files]

        logger.info(
            f"Starting batch processing of {len(pdf_files)} files from {directory}"
        )

        # Initialize batch result
        batch_result = BatchResult(
            started_at=datetime.now(),
            input_directory=str(directory),
            output_directory=str(self.run_dir)
        )

        # Process files in parallel with progress bar
        with tqdm(total=len(pdf_files), desc="Processing invoices") as pbar:
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self._process_single_file, pdf_path): pdf_path
                    for pdf_path in pdf_files
                }

                # Collect results as they complete
                for future in as_completed(future_to_file):
                    result = future.result()
                    batch_result.results.append(result)

                    # Update progress bar with status
                    status_emoji = (
                        "✅" if result.status == ProcessingStatus.SUCCESS else "❌"
                    )
                    pbar.set_postfix_str(
                        f"{status_emoji} {result.filename[:40]}... ({result.status.value})"
                    )
                    pbar.update(1)

                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(result)

        # Finalize batch result
        batch_result.completed_at = datetime.now()
        batch_result.statistics = self._calculate_statistics(batch_result)

        # Save batch result to run directory
        self._save_batch_result(batch_result)

        logger.info(
            f"Batch processing complete: {batch_result.statistics.successful}/{batch_result.statistics.total_files} successful "
            f"({batch_result.statistics.success_rate:.1f}% success rate)"
        )

        return batch_result

    def _process_single_file(self, pdf_path: Path) -> InvoiceResult:
        """
        Process a single PDF invoice.

        Args:
            pdf_path: Path to PDF file

        Returns:
            InvoiceResult with processing outcome
        """
        start_time = time.time()
        filename = pdf_path.name

        try:
            # Step 1: Convert document
            logger.debug(f"Converting document: {filename}")
            doc_key = self.document_processor.convert_document(pdf_path)

            # Step 2: Detect vendor (prioritize file path for directory-based detection)
            logger.debug(f"Detecting vendor for: {filename}")
            vendor_type, confidence = self.document_processor.detect_vendor(
                file_path=str(pdf_path), filename=filename
            )

            if vendor_type == VendorType.UNKNOWN:
                return InvoiceResult(
                    filename=filename,
                    file_path=str(pdf_path),
                    status=ProcessingStatus.FAILED_DETECTION,
                    vendor_type=vendor_type,
                    vendor_confidence=confidence,
                    error_message=f"Could not identify vendor (confidence: {confidence:.2f})",
                    processing_time_seconds=time.time() - start_time,
                    doc_key=doc_key,
                )

            # Step 3: Get appropriate extractor
            extractor = self.factory.get_extractor(vendor_type)
            if not extractor:
                return InvoiceResult(
                    filename=filename,
                    file_path=str(pdf_path),
                    status=ProcessingStatus.VENDOR_NOT_SUPPORTED,
                    vendor_type=vendor_type,
                    vendor_confidence=confidence,
                    error_message=f"No extractor implemented for {vendor_type.value}",
                    processing_time_seconds=time.time() - start_time,
                    doc_key=doc_key,
                )

            # Step 4: Extract invoice data
            logger.debug(f"Extracting data from {filename} using {vendor_type.value}")
            # Get full markdown without truncation for proper line item extraction
            markdown = self.document_processor.get_document_markdown(doc_key, max_size=None)
            invoice = extractor.extract(doc_key, markdown, filename)

            # Success!
            return InvoiceResult(
                filename=filename,
                file_path=str(pdf_path),
                status=ProcessingStatus.SUCCESS,
                vendor_type=vendor_type,
                vendor_confidence=confidence,
                invoice=invoice,
                processing_time_seconds=time.time() - start_time,
                doc_key=doc_key,
            )

        except Exception as e:
            logger.error(f"Failed to process {filename}: {str(e)}", exc_info=True)

            # Determine failure type based on exception
            if "convert" in str(e).lower():
                status = ProcessingStatus.FAILED_CONVERSION
            elif "detect" in str(e).lower() or "vendor" in str(e).lower():
                status = ProcessingStatus.FAILED_DETECTION
            else:
                status = ProcessingStatus.FAILED_EXTRACTION

            return InvoiceResult(
                filename=filename,
                file_path=str(pdf_path),
                status=status,
                error_message=str(e),
                processing_time_seconds=time.time() - start_time,
            )

    def _save_batch_result(self, batch_result: BatchResult) -> None:
        """
        Save batch result to JSON file in run directory.

        Args:
            batch_result: Batch result to save
        """
        if not self.run_dir:
            logger.warning("No run directory set, skipping batch result save")
            return

        result_file = self.run_dir / "batch_result.json"
        try:
            with open(result_file, "w") as f:
                json.dump(batch_result.model_dump(mode="json"), f, indent=2, default=str)
            logger.info(f"Saved batch result to {result_file}")
        except Exception as e:
            logger.error(f"Failed to save batch result: {e}")

    def _calculate_statistics(self, batch_result: BatchResult) -> BatchStatistics:
        """Calculate statistics from batch results."""
        stats = BatchStatistics(
            total_files=len(batch_result.results),
            successful=0,
            failed_conversion=0,
            failed_detection=0,
            failed_extraction=0,
            vendor_not_supported=0,
            skipped=0,
            total_processing_time_seconds=batch_result.duration_seconds or 0,
            average_time_per_file_seconds=0,
        )

        # Count by status
        for result in batch_result.results:
            if result.status == ProcessingStatus.SUCCESS:
                stats.successful += 1
            elif result.status == ProcessingStatus.FAILED_CONVERSION:
                stats.failed_conversion += 1
            elif result.status == ProcessingStatus.FAILED_DETECTION:
                stats.failed_detection += 1
            elif result.status == ProcessingStatus.FAILED_EXTRACTION:
                stats.failed_extraction += 1
            elif result.status == ProcessingStatus.VENDOR_NOT_SUPPORTED:
                stats.vendor_not_supported += 1
            elif result.status == ProcessingStatus.SKIPPED:
                stats.skipped += 1

            # Count by vendor
            if result.vendor_type:
                vendor_name = result.vendor_type.value
                stats.by_vendor[vendor_name] = stats.by_vendor.get(vendor_name, 0) + 1

        # Calculate average processing time
        if stats.total_files > 0:
            total_time = sum(
                r.processing_time_seconds or 0 for r in batch_result.results
            )
            stats.average_time_per_file_seconds = total_time / stats.total_files

        return stats

    def print_summary(self, batch_result: BatchResult) -> None:
        """Print detailed summary of batch processing results."""
        stats = batch_result.statistics
        if not stats:
            print("No statistics available")
            return

        print()
        print("=" * 80)
        print("BATCH PROCESSING SUMMARY")
        print("=" * 80)
        print()

        # Run information
        if batch_result.output_directory:
            print(f"Output Directory:     {batch_result.output_directory}")
            print()

        # Overall statistics
        print(f"Total Files Processed: {stats.total_files}")
        print(f"Successful:           {stats.successful} ({stats.success_rate:.1f}%)")
        print(f"Failed:               {stats.failed_total}")
        print()

        # Breakdown by failure type
        if stats.failed_total > 0:
            print("Failure Breakdown:")
            print("-" * 80)
            if stats.failed_conversion:
                print(f"  Document Conversion:    {stats.failed_conversion}")
            if stats.failed_detection:
                print(f"  Vendor Detection:       {stats.failed_detection}")
            if stats.failed_extraction:
                print(f"  Data Extraction:        {stats.failed_extraction}")
            if stats.vendor_not_supported:
                print(f"  Vendor Not Supported:   {stats.vendor_not_supported}")
            print()

        # Breakdown by vendor
        if stats.by_vendor:
            print("By Vendor:")
            print("-" * 80)
            for vendor, count in sorted(
                stats.by_vendor.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / stats.total_files) * 100
                print(f"  {vendor:30s} {count:3d} ({percentage:5.1f}%)")
            print()

        # Timing information
        print("Processing Time:")
        print("-" * 80)
        print(f"  Total Time:      {stats.total_processing_time_seconds:.2f} seconds")
        print(f"  Average per File: {stats.average_time_per_file_seconds:.2f} seconds")
        print()

        # Failed files (if any)
        failed_results = batch_result.get_failed_results()
        if failed_results and len(failed_results) <= 20:
            print("Failed Files:")
            print("-" * 80)
            for result in failed_results[:20]:
                print(f"  {result.filename:50s} {result.status.value:20s}")
                if result.error_message:
                    print(f"    Error: {result.error_message[:70]}")
            if len(failed_results) > 20:
                print(f"  ... and {len(failed_results) - 20} more")
            print()

        print("=" * 80)
