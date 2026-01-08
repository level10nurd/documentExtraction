"""Vendor-specific invoice extractors."""

from extractors.abox import ABoxExtractor
from extractors.amanda_andrews import AmandaAndrewsExtractor
from extractors.base import BaseExtractor
from extractors.dimax import DimaxExtractor
from extractors.factory import ExtractorFactory
from extractors.omico import OmicoExtractor
from extractors.pride_printing import PridePrintingExtractor
from extractors.reflex_medical import ReflexMedicalExtractor
from extractors.stolzle_lausitz import StolzleLausitzExtractor
from extractors.sunset_press import SunsetPressExtractor
from extractors.wolverine_printing import WolverinePrintingExtractor
from extractors.yes_solutions import YesSolutionsExtractor

__all__ = [
    "BaseExtractor",
    "ExtractorFactory",
    "ReflexMedicalExtractor",
    "SunsetPressExtractor",
    "WolverinePrintingExtractor",
    "OmicoExtractor",
    "PridePrintingExtractor",
    "DimaxExtractor",
    "AmandaAndrewsExtractor",
    "StolzleLausitzExtractor",
    "YesSolutionsExtractor",
    "ABoxExtractor",
]
