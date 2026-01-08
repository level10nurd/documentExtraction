"""Data models for batch processing results."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from models.invoice import Invoice
from models.vendor import VendorType


class ProcessingStatus(str, Enum):
    """Status of invoice processing."""

    SUCCESS = "success"
    FAILED_CONVERSION = "failed_conversion"
    FAILED_DETECTION = "failed_detection"
    FAILED_EXTRACTION = "failed_extraction"
    VENDOR_NOT_SUPPORTED = "vendor_not_supported"
    SKIPPED = "skipped"


class InvoiceResult(BaseModel):
    """Result of processing a single invoice."""

    filename: str
    file_path: str
    status: ProcessingStatus
    vendor_type: Optional[VendorType] = None
    vendor_confidence: Optional[float] = None
    invoice: Optional[Invoice] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    doc_key: Optional[str] = None


class BatchStatistics(BaseModel):
    """Statistics for batch processing run."""

    total_files: int
    successful: int
    failed_conversion: int = 0
    failed_detection: int = 0
    failed_extraction: int = 0
    vendor_not_supported: int = 0
    skipped: int = 0

    # Vendor breakdown
    by_vendor: dict[str, int] = Field(default_factory=dict)

    # Timing
    total_processing_time_seconds: float
    average_time_per_file_seconds: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.successful / self.total_files) * 100

    @property
    def failed_total(self) -> int:
        """Total number of failed invoices."""
        return (
            self.failed_conversion
            + self.failed_detection
            + self.failed_extraction
            + self.vendor_not_supported
        )


class BatchResult(BaseModel):
    """Complete result of batch processing operation."""

    started_at: datetime
    completed_at: Optional[datetime] = None
    input_directory: str
    output_directory: Optional[str] = None
    results: list[InvoiceResult] = Field(default_factory=list)
    statistics: Optional[BatchStatistics] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate total duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def get_successful_invoices(self) -> list[Invoice]:
        """Get all successfully extracted invoices."""
        return [
            result.invoice
            for result in self.results
            if result.status == ProcessingStatus.SUCCESS and result.invoice
        ]

    def get_failed_results(self) -> list[InvoiceResult]:
        """Get all failed processing results."""
        return [
            result
            for result in self.results
            if result.status != ProcessingStatus.SUCCESS
        ]

    def get_results_by_vendor(self, vendor_type: VendorType) -> list[InvoiceResult]:
        """Get all results for a specific vendor."""
        return [result for result in self.results if result.vendor_type == vendor_type]

    def get_results_by_status(self, status: ProcessingStatus) -> list[InvoiceResult]:
        """Get all results with a specific status."""
        return [result for result in self.results if result.status == status]
