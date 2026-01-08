"""Configuration settings for invoice extraction."""

import os
from decimal import Decimal
from pathlib import Path


class Config:
    """Application configuration settings."""

    # Directories
    SOURCE_DIR = Path(
        "/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills"
    )
    OUTPUT_DIR = Path("output")
    CACHE_DIR = Path(".cache")

    # Processing
    MAX_WORKERS = 4
    BATCH_SIZE = 50

    # Validation
    MIN_CONFIDENCE_THRESHOLD = 0.6
    REQUIRE_MANUAL_REVIEW_BELOW = 0.8

    # Duplicate detection
    DUPLICATE_AMOUNT_TOLERANCE = Decimal("0.01")  # ±$0.01

    # Export
    CSV_FORMAT = "normalized"  # or "denormalized"
    DATE_FORMAT = "%Y-%m-%d"
    INCLUDE_DUPLICATES = False
    DEDUPLICATE_STRATEGY = "keep_first"  # keep_first, keep_last, keep_newest_file

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "extraction.log"

    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables."""
        cls.SOURCE_DIR = Path(os.getenv("INVOICE_SOURCE_DIR", cls.SOURCE_DIR))
        cls.OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", cls.OUTPUT_DIR))
        cls.MAX_WORKERS = int(os.getenv("MAX_WORKERS", cls.MAX_WORKERS))
        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", cls.LOG_LEVEL)
        cls.INCLUDE_DUPLICATES = (
            os.getenv("INCLUDE_DUPLICATES", "false").lower() == "true"
        )
        cls.DEDUPLICATE_STRATEGY = os.getenv(
            "DEDUPLICATE_STRATEGY", cls.DEDUPLICATE_STRATEGY
        )

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_vendor_directory(cls, vendor_type) -> Path:
        """
        Get the directory path for a specific vendor.

        Args:
            vendor_type: VendorType enum value

        Returns:
            Path to vendor's invoice directory
        """
        from models.vendor import VENDOR_DIRECTORIES

        dirname = VENDOR_DIRECTORIES.get(vendor_type)
        if not dirname:
            raise ValueError(f"No directory mapping for vendor: {vendor_type}")

        return cls.SOURCE_DIR / dirname

    @classmethod
    def get_all_vendor_directories(cls) -> dict:
        """
        Get all vendor directories.

        Returns:
            Dict mapping VendorType to Path for each vendor directory
        """
        from models.vendor import VENDOR_DIRECTORIES

        return {
            vendor: cls.SOURCE_DIR / dirname
            for vendor, dirname in VENDOR_DIRECTORIES.items()
        }
