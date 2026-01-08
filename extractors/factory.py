"""Factory for creating vendor-specific extractors."""

from typing import Optional

from extractors.abox import ABoxExtractor
from extractors.amanda_andrews import AmandaAndrewsExtractor
from extractors.base import BaseExtractor
from extractors.dimax import DimaxExtractor
from extractors.omico import OmicoExtractor
from extractors.pride_printing import PridePrintingExtractor
from extractors.reflex_medical import ReflexMedicalExtractor
from extractors.stolzle_lausitz import StolzleLausitzExtractor
from extractors.sunset_press import SunsetPressExtractor
from extractors.wolverine_printing import WolverinePrintingExtractor
from extractors.yes_solutions import YesSolutionsExtractor
from models.vendor import VendorType
from processors.document_processor import DocumentProcessor


class ExtractorFactory:
    """Factory for creating appropriate extractor based on vendor type."""

    def __init__(self, document_processor: DocumentProcessor):
        """Initialize factory with document processor."""
        self.document_processor = document_processor
        self._extractors = self._build_extractor_map()

    def _build_extractor_map(self) -> dict[VendorType, BaseExtractor]:
        """Build mapping of vendor types to extractor instances."""
        return {
            VendorType.REFLEX_MEDICAL: ReflexMedicalExtractor(self.document_processor),
            VendorType.SUNSET_PRESS: SunsetPressExtractor(self.document_processor),
            VendorType.WOLVERINE_PRINTING: WolverinePrintingExtractor(
                self.document_processor
            ),
            VendorType.OMICO: OmicoExtractor(self.document_processor),
            VendorType.PRIDE_PRINTING: PridePrintingExtractor(self.document_processor),
            VendorType.DIMAX: DimaxExtractor(self.document_processor),
            VendorType.AMANDA_ANDREWS: AmandaAndrewsExtractor(self.document_processor),
            VendorType.STOLZLE_LAUSITZ: StolzleLausitzExtractor(
                self.document_processor
            ),
            VendorType.YES_SOLUTIONS: YesSolutionsExtractor(self.document_processor),
            VendorType.ABOX: ABoxExtractor(self.document_processor),
        }

    def get_extractor(self, vendor_type: VendorType) -> Optional[BaseExtractor]:
        """
        Get appropriate extractor for vendor type.

        Args:
            vendor_type: The vendor type to get extractor for

        Returns:
            Extractor instance or None if vendor type not supported
        """
        return self._extractors.get(vendor_type)

    def get_supported_vendors(self) -> list[VendorType]:
        """Get list of supported vendor types."""
        return list(self._extractors.keys())

    def is_vendor_supported(self, vendor_type: VendorType) -> bool:
        """Check if vendor type has an extractor implemented."""
        return vendor_type in self._extractors
