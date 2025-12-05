"""
Pydantic models for invoice data and validation results.

This module defines the core data structures used throughout the Invoice QC Service:
- Invoice and LineItem models for extracted invoice data
- InvoiceValidationResult for per-invoice validation outcomes
- ValidationSummary for batch-level statistics
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LineItem(BaseModel):
    """
    Represents a single line item in an invoice.
    
    Attributes:
        description: Text description of the item or service
        quantity: Number of units
        unit_price: Price per unit
        line_total: Total for this line (quantity × unit_price)
        tax_rate: Optional tax rate percentage applied to this line
        unit_of_measure: Optional unit (e.g., "pcs", "hours", "kg")
    """
    description: str = Field(..., min_length=1, description="Item or service description")
    quantity: float = Field(..., ge=0, description="Number of units")
    unit_price: float = Field(..., ge=0, description="Price per unit")
    line_total: float = Field(..., description="Total for this line item")
    tax_rate: Optional[float] = Field(None, ge=0, le=100, description="Tax rate percentage")
    unit_of_measure: Optional[str] = Field(None, description="Unit of measure (e.g., pcs, hours)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Software Development Services",
                    "quantity": 40,
                    "unit_price": 150.00,
                    "line_total": 6000.00,
                    "tax_rate": 18.0,
                    "unit_of_measure": "hours"
                }
            ]
        }
    }


class Invoice(BaseModel):
    """
    Represents a B2B invoice with all extracted fields.
    
    This model captures the essential information from a business invoice,
    including identifiers, party information, dates, financial totals,
    and itemized details.
    """
    
    # ========================================================================
    # Core Identifiers
    # ========================================================================
    invoice_number: str = Field(
        ..., 
        min_length=1,
        description="Unique invoice identifier assigned by the seller"
    )
    external_reference: Optional[str] = Field(
        None,
        description="External reference such as PO number, contract ID, or internal reference"
    )
    
    # ========================================================================
    # Seller (Vendor) Information
    # ========================================================================
    seller_name: str = Field(
        ...,
        min_length=1,
        description="Legal name of the seller/vendor issuing the invoice"
    )
    seller_tax_id: Optional[str] = Field(
        None,
        description="Seller's tax identification number (VAT ID, GST number, TIN, etc.)"
    )
    seller_address: Optional[str] = Field(
        None,
        description="Seller's business address"
    )
    
    # ========================================================================
    # Buyer (Customer) Information
    # ========================================================================
    buyer_name: str = Field(
        ...,
        min_length=1,
        description="Legal name of the buyer/customer receiving the invoice"
    )
    buyer_tax_id: Optional[str] = Field(
        None,
        description="Buyer's tax identification number"
    )
    buyer_address: Optional[str] = Field(
        None,
        description="Buyer's billing address"
    )
    
    # ========================================================================
    # Dates
    # ========================================================================
    invoice_date: date = Field(
        ...,
        description="Date when the invoice was issued"
    )
    due_date: Optional[date] = Field(
        None,
        description="Payment due date"
    )
    
    # ========================================================================
    # Financial Information
    # ========================================================================
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Three-letter ISO currency code (e.g., USD, EUR, INR)"
    )
    net_total: float = Field(
        ...,
        description="Subtotal before tax (sum of all line items)"
    )
    tax_amount: float = Field(
        ...,
        description="Total tax amount"
    )
    gross_total: float = Field(
        ...,
        description="Total amount due including tax (net_total + tax_amount)"
    )
    payment_terms: Optional[str] = Field(
        None,
        description="Payment terms (e.g., 'Net 30', '2/10 Net 30')"
    )
    
    # ========================================================================
    # Line Items
    # ========================================================================
    line_items: list[LineItem] = Field(
        default_factory=list,
        description="Itemized list of products or services"
    )

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        """Normalize currency code to uppercase."""
        return v.upper().strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "invoice_number": "INV-2024-001234",
                    "external_reference": "PO-98765",
                    "seller_name": "Acme Software Solutions Ltd",
                    "seller_tax_id": "GB123456789",
                    "seller_address": "123 Tech Park, London, UK",
                    "buyer_name": "Global Enterprises Inc",
                    "buyer_tax_id": "US-87654321",
                    "buyer_address": "456 Business Ave, New York, USA",
                    "invoice_date": "2024-01-15",
                    "due_date": "2024-02-14",
                    "currency": "USD",
                    "net_total": 10000.00,
                    "tax_amount": 1800.00,
                    "gross_total": 11800.00,
                    "payment_terms": "Net 30",
                    "line_items": [
                        {
                            "description": "Software Development Services",
                            "quantity": 40,
                            "unit_price": 150.00,
                            "line_total": 6000.00,
                            "tax_rate": 18.0,
                            "unit_of_measure": "hours"
                        },
                        {
                            "description": "Cloud Infrastructure Setup",
                            "quantity": 1,
                            "unit_price": 4000.00,
                            "line_total": 4000.00,
                            "tax_rate": 18.0,
                            "unit_of_measure": "project"
                        }
                    ]
                }
            ]
        }
    }


class InvoiceValidationResult(BaseModel):
    """
    Validation result for a single invoice.
    
    Contains the validation outcome including all errors and warnings
    found during the validation process.
    """
    invoice_id: str = Field(
        ...,
        description="Identifier for the invoice (typically invoice_number)"
    )
    is_valid: bool = Field(
        ...,
        description="True if the invoice passed all validation rules"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of validation error codes (e.g., 'missing_field:buyer_name')"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning codes for non-critical issues"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "invoice_id": "INV-2024-001234",
                    "is_valid": False,
                    "errors": [
                        "missing_field:buyer_tax_id",
                        "business_rule:totals_mismatch"
                    ],
                    "warnings": [
                        "anomaly:high_tax_rate"
                    ]
                }
            ]
        }
    }


class ValidationSummary(BaseModel):
    """
    Aggregated validation summary for a batch of invoices.
    
    Provides high-level statistics about the validation results
    including counts and error type distribution.
    """
    total_invoices: int = Field(
        ...,
        ge=0,
        description="Total number of invoices processed"
    )
    valid_invoices: int = Field(
        ...,
        ge=0,
        description="Number of invoices that passed all validation rules"
    )
    invalid_invoices: int = Field(
        ...,
        ge=0,
        description="Number of invoices with one or more validation errors"
    )
    error_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of each error type across all invoices"
    )
    warning_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of each warning type across all invoices"
    )
    duplicates_detected: int = Field(
        0,
        ge=0,
        description="Number of duplicate invoices detected in the batch"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total_invoices": 100,
                    "valid_invoices": 85,
                    "invalid_invoices": 15,
                    "error_counts": {
                        "missing_field:buyer_tax_id": 5,
                        "business_rule:totals_mismatch": 8,
                        "anomaly:duplicate_invoice": 2
                    },
                    "warning_counts": {
                        "anomaly:high_tax_rate": 3
                    },
                    "duplicates_detected": 2
                }
            ]
        }
    }


class ValidationReport(BaseModel):
    """
    Complete validation report containing per-invoice results and summary.
    
    This is the primary output format for validation operations.
    """
    summary: ValidationSummary = Field(
        ...,
        description="Aggregated statistics for the validation batch"
    )
    per_invoice_results: list[InvoiceValidationResult] = Field(
        default_factory=list,
        description="Detailed validation results for each invoice"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": {
                        "total_invoices": 2,
                        "valid_invoices": 1,
                        "invalid_invoices": 1,
                        "error_counts": {"business_rule:totals_mismatch": 1},
                        "warning_counts": {},
                        "duplicates_detected": 0
                    },
                    "per_invoice_results": [
                        {
                            "invoice_id": "INV-001",
                            "is_valid": True,
                            "errors": [],
                            "warnings": []
                        },
                        {
                            "invoice_id": "INV-002",
                            "is_valid": False,
                            "errors": ["business_rule:totals_mismatch"],
                            "warnings": []
                        }
                    ]
                }
            ]
        }
    }


# ============================================================================
# API Request/Response Models
# ============================================================================

class ValidateJsonRequest(BaseModel):
    """Request body for the /validate-json endpoint."""
    invoices: list[Invoice] = Field(
        ...,
        min_length=1,
        description="List of invoice objects to validate"
    )


class ExtractAndValidateResponse(BaseModel):
    """Response for the /extract-and-validate-pdfs endpoint."""
    extracted_invoices: list[Invoice] = Field(
        ...,
        description="List of invoices extracted from uploaded PDFs"
    )
    validation_summary: ValidationSummary = Field(
        ...,
        description="Aggregated validation statistics"
    )
    per_invoice_results: list[InvoiceValidationResult] = Field(
        ...,
        description="Detailed validation results for each extracted invoice"
    )
