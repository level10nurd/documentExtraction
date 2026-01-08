"""Data models for invoice processing."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.vendor import VendorType


class LineItem(BaseModel):
    """Represents a single line item on an invoice."""

    quantity: Optional[Decimal] = None
    item_code: Optional[str] = None
    description: str
    price_each: Optional[Decimal] = None
    amount: Decimal

    @field_validator("amount", "price_each", "quantity", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        """Strip currency symbols and convert to Decimal."""
        if v is None or v == "":
            return None
        if isinstance(v, (int, float, Decimal)):
            return Decimal(str(v))
        if isinstance(v, str):
            # Remove currency symbols, commas, and whitespace
            v = v.replace("$", "").replace(",", "").strip()
            if not v:
                return None
            try:
                return Decimal(v)
            except (InvalidOperation, ValueError):
                return None
        return None


class Invoice(BaseModel):
    """Represents a complete invoice with header and line items."""

    # Header fields
    vendor: VendorType
    invoice_date: Optional[date] = None
    invoice_number: str
    po_number: Optional[str] = None

    # Line items
    line_items: list[LineItem] = Field(default_factory=list)

    # Totals
    subtotal: Optional[Decimal] = None
    sales_tax: Optional[Decimal] = None
    total: Decimal

    # Metadata
    source_file: str
    extraction_confidence: float = 1.0  # 0.0 to 1.0
    extraction_errors: list[str] = Field(default_factory=list)

    # Duplicate tracking
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None  # points to original file
    duplicate_files: list[str] = Field(default_factory=list)

    @field_validator("subtotal", "sales_tax", "total", mode="before")
    @classmethod
    def parse_currency(cls, v):
        """Strip currency symbols and convert to Decimal."""
        if v is None or v == "":
            return None
        if isinstance(v, (int, float, Decimal)):
            return Decimal(str(v))
        if isinstance(v, str):
            v = v.replace("$", "").replace(",", "").strip()
            if not v:
                return None
            try:
                return Decimal(v)
            except (InvalidOperation, ValueError):
                return None
        return None

    @field_validator("invoice_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        """Parse various date formats."""
        if v is None or isinstance(v, date):
            return v
        if isinstance(v, str):
            from dateutil.parser import parse

            try:
                return parse(v).date()
            except Exception:
                return None
        return None

    def calculate_confidence(self) -> float:
        """Calculate extraction confidence based on field completeness."""
        score = 1.0

        # Critical fields
        if not self.invoice_number:
            score -= 0.3
        if self.total is None:
            score -= 0.3

        # Important fields
        if not self.invoice_date:
            score -= 0.2
        if not self.po_number:
            score -= 0.1

        # Line items
        if not self.line_items:
            score -= 0.2
        elif len(self.line_items) == 0:
            score -= 0.1

        return max(0.0, score)

    def add_error(self, error_message: str) -> None:
        """Add an extraction error and adjust confidence."""
        self.extraction_errors.append(error_message)
        self.extraction_confidence = min(
            self.extraction_confidence, self.calculate_confidence()
        )
