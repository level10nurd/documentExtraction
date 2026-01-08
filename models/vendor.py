"""Vendor types and detection patterns for invoice processing."""

import re
from enum import Enum
from typing import Pattern


class VendorType(str, Enum):
    """Enumeration of supported invoice vendors."""

    SUNSET_PRESS = "Sunset Press"
    REFLEX_MEDICAL = "REFLEX MEDICAL CORP"
    WOLVERINE_PRINTING = "Wolverine Printing"
    OMICO = "OMICO"
    YES_SOLUTIONS = "YES Solutions LLC"
    STOLZLE_LAUSITZ = "Stölzle Glassware"
    PRIDE_PRINTING = "Pride Printing LLC"
    DIMAX = "Dimax Corporation"
    AMANDA_ANDREWS = "AMANDA-ANDREWS PERSONNEL CORP"
    ABOX = "ABox"
    UNKNOWN = "Unknown"


# Vendor to directory name mapping
# Each vendor's invoices are organized in Bills/<directory_name>/
VENDOR_DIRECTORIES: dict[VendorType, str] = {
    VendorType.REFLEX_MEDICAL: "Reflex",
    VendorType.SUNSET_PRESS: "Sunset",
    VendorType.WOLVERINE_PRINTING: "Wolverine",
    VendorType.OMICO: "Omico",
    VendorType.YES_SOLUTIONS: "YesSolutions",
    VendorType.STOLZLE_LAUSITZ: "Stolzle",
    VendorType.PRIDE_PRINTING: "PridePrinting",
    VendorType.DIMAX: "DiMax",
    VendorType.AMANDA_ANDREWS: "AmandaAndrews",
    VendorType.ABOX: "ABox",
}

# Reverse mapping for directory -> vendor lookups
DIRECTORY_TO_VENDOR: dict[str, VendorType] = {
    dirname.lower(): vendor for vendor, dirname in VENDOR_DIRECTORIES.items()
}


# Vendor detection patterns - multiple patterns increase confidence
VENDOR_PATTERNS: dict[VendorType, list[Pattern]] = {
    VendorType.SUNSET_PRESS: [
        re.compile(r"Sunset\s+Press", re.IGNORECASE),
        re.compile(r"sunsetpressinc\.com", re.IGNORECASE),
        re.compile(r"10908\s+Bluff\s+Bend\s+Drive", re.IGNORECASE),
    ],
    VendorType.REFLEX_MEDICAL: [
        re.compile(r"REFLEX\s+MEDICAL\s+CORP", re.IGNORECASE),
        re.compile(r"2480\s+7th\s+Ave\s+E\s+North\s+St\s+Paul", re.IGNORECASE),
        re.compile(r"reflexmedical", re.IGNORECASE),
    ],
    VendorType.WOLVERINE_PRINTING: [
        re.compile(r"Wolverine.*Printing", re.IGNORECASE),
        re.compile(r"WOLVERINEPRINTING\.COM", re.IGNORECASE),
        re.compile(r"315\s+GRANDVILLE\s+AVE\s+SW.*GRAND\s+RAPIDS", re.IGNORECASE),
    ],
    VendorType.OMICO: [
        re.compile(r"OMICO,?\s*Inc", re.IGNORECASE),
        re.compile(r"2025\s+Ragu\s+Drive.*Owensboro", re.IGNORECASE),
        re.compile(r"omico", re.IGNORECASE),
    ],
    VendorType.YES_SOLUTIONS: [
        re.compile(r"YES\s+Solutions\s+LLC", re.IGNORECASE),
        re.compile(r"Thank\s+YOU\s+for\s+choosing\s+YES\s+Solutions", re.IGNORECASE),
    ],
    VendorType.STOLZLE_LAUSITZ: [
        re.compile(r"St[oö]lzle\s+Glassware", re.IGNORECASE),
        re.compile(r"St[oö]lzle\s+Lausitz", re.IGNORECASE),
        re.compile(r"4401\s+Eastern\s+Avenue.*Baltimore", re.IGNORECASE),
    ],
    VendorType.PRIDE_PRINTING: [
        re.compile(r"Pride\s+Printing\s+LLC", re.IGNORECASE),
        re.compile(r"prideprinting@aol\.com", re.IGNORECASE),
        re.compile(r"11875\s+W\s+Little\s+York\s+Rd.*Houston", re.IGNORECASE),
    ],
    VendorType.DIMAX: [
        re.compile(r"Dimax\s+Corporation", re.IGNORECASE),
        re.compile(r"1107\s+INDUSTRIAL\s+LANE.*Winsted", re.IGNORECASE),
        re.compile(r"320-485-3232", re.IGNORECASE),
    ],
    VendorType.AMANDA_ANDREWS: [
        re.compile(r"AMANDA[-\s]ANDREWS\s+PERSONNEL\s+CORP", re.IGNORECASE),
        re.compile(r"VIP\s+STAFFING", re.IGNORECASE),
        re.compile(r"153\s+Treeline\s+Park.*San\s+Antonio", re.IGNORECASE),
        re.compile(r"\(210\)\s*340-2000", re.IGNORECASE),
    ],
}


def detect_vendor_from_path(file_path: str) -> VendorType:
    """
    Detect vendor type from file path based on directory structure.

    The Bills directory is organized with vendor subdirectories:
    Bills/Reflex/invoice.pdf -> VendorType.REFLEX_MEDICAL
    Bills/Sunset/invoice.pdf -> VendorType.SUNSET_PRESS

    Args:
        file_path: Full path to the invoice PDF file

    Returns:
        VendorType based on parent directory, or UNKNOWN if not found
    """
    from pathlib import Path

    path = Path(file_path)

    # Look for Bills directory in path
    parts = path.parts
    try:
        bills_index = next(i for i, part in enumerate(parts) if part == "Bills")
        # The next part should be the vendor directory
        if bills_index + 1 < len(parts):
            vendor_dir = parts[bills_index + 1]
            vendor = DIRECTORY_TO_VENDOR.get(vendor_dir.lower())
            if vendor:
                return vendor
    except StopIteration:
        pass

    return VendorType.UNKNOWN
