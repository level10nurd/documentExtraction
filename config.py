"""Configuration settings for invoice extraction."""

import json
import os
from decimal import Decimal
from pathlib import Path


class Config:
    """Application configuration settings."""

    # Directories (defaults, can be overridden by environment)
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

    # Environment tracking
    CURRENT_ENVIRONMENT = None

    @classmethod
    def load_environment(
        cls, env_name: str = None, config_file: str = "environments.json"
    ):
        """
        Load configuration from environments.json file.

        Args:
            env_name: Name of the environment to load (e.g., 'work_mac', 'home_mac').
                     If None, uses default from config file or INVOICE_ENV environment variable.
            config_file: Path to the environments configuration file.

        Raises:
            FileNotFoundError: If environments.json doesn't exist.
            ValueError: If specified environment doesn't exist in config.
        """
        config_path = Path(config_file)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Environment configuration file not found: {config_file}\n"
                "Create environments.json with your computer-specific settings."
            )

        with open(config_path) as f:
            env_config = json.load(f)

        # Determine which environment to use (priority order):
        # 1. Explicitly passed env_name parameter
        # 2. INVOICE_ENV environment variable
        # 3. Default from config file
        if env_name is None:
            env_name = os.getenv("INVOICE_ENV", env_config.get("default"))

        if env_name not in env_config["environments"]:
            available = ", ".join(env_config["environments"].keys())
            raise ValueError(
                f"Environment '{env_name}' not found in {config_file}.\n"
                f"Available environments: {available}"
            )

        env_settings = env_config["environments"][env_name]

        # Apply environment-specific settings
        cls.SOURCE_DIR = Path(env_settings["source_dir"])
        cls.OUTPUT_DIR = Path(env_settings.get("output_dir", cls.OUTPUT_DIR))
        cls.MAX_WORKERS = env_settings.get("max_workers", cls.MAX_WORKERS)
        cls.CURRENT_ENVIRONMENT = env_name

        # Still allow environment variable overrides
        cls._apply_env_overrides()

        return env_name

    @classmethod
    def _apply_env_overrides(cls):
        """Apply environment variable overrides after loading base config."""
        if os.getenv("INVOICE_SOURCE_DIR"):
            cls.SOURCE_DIR = Path(os.getenv("INVOICE_SOURCE_DIR"))
        if os.getenv("OUTPUT_DIR"):
            cls.OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR"))
        if os.getenv("MAX_WORKERS"):
            cls.MAX_WORKERS = int(os.getenv("MAX_WORKERS"))
        if os.getenv("LOG_LEVEL"):
            cls.LOG_LEVEL = os.getenv("LOG_LEVEL")
        if os.getenv("INCLUDE_DUPLICATES"):
            cls.INCLUDE_DUPLICATES = (
                os.getenv("INCLUDE_DUPLICATES", "false").lower() == "true"
            )
        if os.getenv("DEDUPLICATE_STRATEGY"):
            cls.DEDUPLICATE_STRATEGY = os.getenv("DEDUPLICATE_STRATEGY")

    @classmethod
    def load_from_env(cls):
        """
        Load configuration from environment variables (legacy method).

        For new code, prefer load_environment() which uses environments.json.
        This method is kept for backward compatibility.
        """
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
    def list_environments(cls, config_file: str = "environments.json") -> dict:
        """
        List all available environments from config file.

        Args:
            config_file: Path to the environments configuration file.

        Returns:
            Dict mapping environment names to their descriptions and settings.
        """
        config_path = Path(config_file)

        if not config_path.exists():
            return {}

        with open(config_path) as f:
            env_config = json.load(f)

        return {
            name: {
                "description": settings.get("description", "No description"),
                "source_dir": settings["source_dir"],
                "is_default": name == env_config.get("default"),
            }
            for name, settings in env_config["environments"].items()
        }

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
