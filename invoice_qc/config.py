"""
Configuration constants and enums for the Invoice QC Service.
"""

import logging
import os
from enum import Enum
from typing import Final

# ============================================================================
# Supported Currencies
# ============================================================================

SUPPORTED_CURRENCIES: Final[set[str]] = {
    "USD",  # US Dollar
    "EUR",  # Euro
    "GBP",  # British Pound
    "INR",  # Indian Rupee
    "JPY",  # Japanese Yen
    "CAD",  # Canadian Dollar
    "AUD",  # Australian Dollar
    "CHF",  # Swiss Franc
    "CNY",  # Chinese Yuan
    "SGD",  # Singapore Dollar
    "AED",  # UAE Dirham
    "HKD",  # Hong Kong Dollar
}

# ============================================================================
# Validation Tolerances
# ============================================================================

# Tolerance for floating-point amount comparisons (e.g., net + tax ≈ gross)
AMOUNT_TOLERANCE: Final[float] = float(os.getenv("AMOUNT_TOLERANCE", "0.01"))

# ============================================================================
# Date Formats
# ============================================================================

# Common date formats to try when parsing invoice dates
DATE_FORMATS: Final[list[str]] = [
    "%Y-%m-%d",      # ISO format: 2024-01-15
    "%d/%m/%Y",      # European: 15/01/2024
    "%m/%d/%Y",      # US: 01/15/2024
    "%d-%m-%Y",      # European with dashes: 15-01-2024
    "%d.%m.%Y",      # European with dots: 15.01.2024
    "%B %d, %Y",     # Long format: January 15, 2024
    "%b %d, %Y",     # Short month: Jan 15, 2024
    "%d %B %Y",      # European long: 15 January 2024
    "%d %b %Y",      # European short: 15 Jan 2024
]

# ============================================================================
# Extraction Patterns
# ============================================================================

# Labels to search for when extracting invoice number
INVOICE_NUMBER_LABELS: Final[list[str]] = [
    "invoice no",
    "invoice number",
    "invoice #",
    "invoice:",
    "inv no",
    "inv #",
    "bill no",
    "bill number",
    "document no",
    "doc no",
    # German labels
    "rechnungsnr",
    "rechnung nr",
    "bestellung",
    "aufnr",
    "bestellnummer",
]

# Labels for seller/vendor identification
SELLER_LABELS: Final[list[str]] = [
    "from:",
    "seller:",
    "vendor:",
    "sold by:",
    "supplier:",
    "bill from:",
    "ship from:",
    # German labels
    "lieferant:",
    "verkäufer:",
    "absender:",
]

# Labels for buyer identification
BUYER_LABELS: Final[list[str]] = [
    "to:",
    "bill to:",
    "buyer:",
    "sold to:",
    "customer:",
    "ship to:",
    "invoice to:",
    # German labels
    "kundenanschrift",
    "empfänger:",
    "käufer:",
    "kunde:",
]

# ============================================================================
# Error Code Prefixes
# ============================================================================

class ErrorCategory(str, Enum):
    """Categories for validation error codes."""
    MISSING_FIELD = "missing_field"
    FORMAT_ERROR = "format_error"
    BUSINESS_RULE = "business_rule"
    ANOMALY = "anomaly"


# ============================================================================
# API Configuration
# ============================================================================

API_HOST: Final[str] = os.getenv("API_HOST", "0.0.0.0")
API_PORT: Final[int] = int(os.getenv("API_PORT", "8000"))
MAX_UPLOAD_SIZE_MB: Final[int] = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")

def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("invoice_qc")


logger = setup_logging()
