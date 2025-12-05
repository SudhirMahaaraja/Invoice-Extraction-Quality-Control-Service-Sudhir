"""
Invoice Extraction & Quality Control Service

A Python service for extracting structured data from B2B invoice PDFs
and validating them against configurable business rules.
"""

__version__ = "0.1.0"
__author__ = "Invoice QC Team"

from .schemas import Invoice, LineItem, InvoiceValidationResult, ValidationSummary
from .extractor import extract_invoices_from_dir, extract_invoice_from_pdf
from .validator import validate_invoice, validate_batch

__all__ = [
    "Invoice",
    "LineItem", 
    "InvoiceValidationResult",
    "ValidationSummary",
    "extract_invoices_from_dir",
    "extract_invoice_from_pdf",
    "validate_invoice",
    "validate_batch",
]
