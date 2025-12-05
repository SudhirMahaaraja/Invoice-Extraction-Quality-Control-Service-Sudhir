"""
Validation rules for invoice quality control.

This module defines a structured set of validation rules organized by category:
- Completeness rules: Check for required fields
- Format rules: Validate data formats and allowed values
- Business rules: Enforce business logic constraints
- Anomaly rules: Detect suspicious or duplicate data

Each rule is implemented as a function that returns an error code if validation
fails, or None if validation passes.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from .config import SUPPORTED_CURRENCIES, AMOUNT_TOLERANCE, ErrorCategory
from .schemas import Invoice


# Type alias for rule check functions
# The function takes an Invoice and optional context dict, returns error code or None
RuleCheckFn = Callable[[Invoice, Optional[dict]], Optional[str]]


@dataclass
class ValidationRule:
    """
    Represents a single validation rule.
    
    Attributes:
        code: Machine-readable error code (e.g., "missing_field:invoice_number")
        description: Human-readable description of the rule
        category: Category of the rule (completeness, format, business, anomaly)
        check: Function that performs the validation check
    """
    code: str
    description: str
    category: ErrorCategory
    check: RuleCheckFn


# ============================================================================
# Completeness Rules
# ============================================================================

def check_invoice_number(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """Every invoice must have a non-empty invoice number."""
    if not invoice.invoice_number or not invoice.invoice_number.strip():
        return f"{ErrorCategory.MISSING_FIELD.value}:invoice_number"
    return None


def check_invoice_date(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """Invoice date must be present."""
    if invoice.invoice_date is None:
        return f"{ErrorCategory.MISSING_FIELD.value}:invoice_date"
    return None


def check_seller_name(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """Seller name must not be empty."""
    if not invoice.seller_name or not invoice.seller_name.strip():
        return f"{ErrorCategory.MISSING_FIELD.value}:seller_name"
    return None


def check_buyer_name(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """Buyer name must not be empty."""
    if not invoice.buyer_name or not invoice.buyer_name.strip():
        return f"{ErrorCategory.MISSING_FIELD.value}:buyer_name"
    return None


def check_currency_present(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """Currency must be present."""
    if not invoice.currency or not invoice.currency.strip():
        return f"{ErrorCategory.MISSING_FIELD.value}:currency"
    return None


# ============================================================================
# Format Rules
# ============================================================================

def check_currency_valid(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """Currency must be one of the supported currency codes."""
    if invoice.currency and invoice.currency.upper() not in SUPPORTED_CURRENCIES:
        return f"{ErrorCategory.FORMAT_ERROR.value}:currency"
    return None


def check_totals_numeric(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """
    Net total, tax amount, and gross total must be numeric values.
    Pydantic handles this, but we double-check for None.
    """
    if invoice.net_total is None:
        return f"{ErrorCategory.FORMAT_ERROR.value}:net_total"
    if invoice.tax_amount is None:
        return f"{ErrorCategory.FORMAT_ERROR.value}:tax_amount"
    if invoice.gross_total is None:
        return f"{ErrorCategory.FORMAT_ERROR.value}:gross_total"
    return None


# ============================================================================
# Business Rules
# ============================================================================

def check_line_items_sum(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """
    Sum of all line_items.line_total should approximately equal net_total.
    
    Rationale: If line items are present, their sum should match the 
    invoice subtotal. This catches data entry errors or extraction issues.
    """
    if not invoice.line_items:
        # Skip this check if no line items (common for simple invoices)
        return None
    
    line_items_sum = sum(item.line_total for item in invoice.line_items)
    
    if abs(line_items_sum - invoice.net_total) > AMOUNT_TOLERANCE:
        return f"{ErrorCategory.BUSINESS_RULE.value}:line_items_mismatch"
    
    return None


def check_totals_consistency(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """
    net_total + tax_amount should approximately equal gross_total.
    
    Rationale: This is the fundamental invoice equation. Any mismatch
    indicates data corruption or extraction errors.
    """
    expected_gross = invoice.net_total + invoice.tax_amount
    
    if abs(expected_gross - invoice.gross_total) > AMOUNT_TOLERANCE:
        return f"{ErrorCategory.BUSINESS_RULE.value}:totals_mismatch"
    
    return None


def check_due_date_valid(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """
    If due_date is present, it must not be earlier than invoice_date.
    
    Rationale: A payment cannot be due before the invoice is issued.
    This catches date parsing errors or data entry mistakes.
    """
    if invoice.due_date is None:
        return None
    
    if invoice.due_date < invoice.invoice_date:
        return f"{ErrorCategory.BUSINESS_RULE.value}:invalid_due_date"
    
    return None


def check_line_items_validity(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """
    Each line item should have quantity × unit_price ≈ line_total.
    
    Rationale: Ensures line item calculations are correct.
    """
    for i, item in enumerate(invoice.line_items):
        expected_total = item.quantity * item.unit_price
        if abs(expected_total - item.line_total) > AMOUNT_TOLERANCE:
            return f"{ErrorCategory.BUSINESS_RULE.value}:line_item_calculation_error"
    
    return None


# ============================================================================
# Anomaly Rules
# ============================================================================

def check_non_negative_totals(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """
    Totals should not be negative (net_total, tax_amount, gross_total >= 0).
    
    Rationale: While credit notes may have negative values, standard invoices
    should have non-negative amounts. Mark as anomaly for review.
    """
    if invoice.net_total < 0:
        return f"{ErrorCategory.ANOMALY.value}:negative_net_total"
    if invoice.tax_amount < 0:
        return f"{ErrorCategory.ANOMALY.value}:negative_tax_amount"
    if invoice.gross_total < 0:
        return f"{ErrorCategory.ANOMALY.value}:negative_gross_total"
    return None


def check_duplicate_invoice(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """
    Check for duplicate invoices within the batch.
    
    Duplicates are identified by the combination:
    (invoice_number, seller_name, invoice_date)
    
    Rationale: The same invoice from the same seller on the same date
    is likely a duplicate entry, which can cause double payments.
    
    Context should contain a 'seen_invoices' set that tracks unique keys.
    """
    if context is None:
        return None
    
    seen_invoices: set = context.get("seen_invoices", set())
    
    # Create a unique key for this invoice
    key = (
        invoice.invoice_number.strip().lower(),
        invoice.seller_name.strip().lower(),
        invoice.invoice_date.isoformat() if invoice.invoice_date else ""
    )
    
    if key in seen_invoices:
        return f"{ErrorCategory.ANOMALY.value}:duplicate_invoice"
    
    # Add to seen set for future checks
    seen_invoices.add(key)
    context["seen_invoices"] = seen_invoices
    
    return None


def check_unreasonable_amounts(invoice: Invoice, context: Optional[dict] = None) -> Optional[str]:
    """
    Flag invoices with suspiciously high or zero gross totals.
    
    Rationale: Zero-value invoices or extremely high amounts may
    indicate data extraction errors or require manual review.
    """
    # Flag zero-value invoices as they may be errors
    if invoice.gross_total == 0 and invoice.net_total == 0:
        return f"{ErrorCategory.ANOMALY.value}:zero_value_invoice"
    
    # Flag extremely high amounts (over 10 million) - configurable threshold
    if invoice.gross_total > 10_000_000:
        return f"{ErrorCategory.ANOMALY.value}:high_value_invoice"
    
    return None


# ============================================================================
# Rule Registry
# ============================================================================

# All validation rules in execution order
VALIDATION_RULES: list[ValidationRule] = [
    # Completeness rules (run first to catch missing required data)
    ValidationRule(
        code="missing_field:invoice_number",
        description="Every invoice must have a non-empty invoice number",
        category=ErrorCategory.MISSING_FIELD,
        check=check_invoice_number,
    ),
    ValidationRule(
        code="missing_field:invoice_date",
        description="Invoice date must be present",
        category=ErrorCategory.MISSING_FIELD,
        check=check_invoice_date,
    ),
    ValidationRule(
        code="missing_field:seller_name",
        description="Seller name must not be empty",
        category=ErrorCategory.MISSING_FIELD,
        check=check_seller_name,
    ),
    ValidationRule(
        code="missing_field:buyer_name",
        description="Buyer name must not be empty",
        category=ErrorCategory.MISSING_FIELD,
        check=check_buyer_name,
    ),
    ValidationRule(
        code="missing_field:currency",
        description="Currency must be present",
        category=ErrorCategory.MISSING_FIELD,
        check=check_currency_present,
    ),
    
    # Format rules
    ValidationRule(
        code="format_error:currency",
        description="Currency must be a valid ISO currency code",
        category=ErrorCategory.FORMAT_ERROR,
        check=check_currency_valid,
    ),
    ValidationRule(
        code="format_error:totals",
        description="Financial totals must be numeric values",
        category=ErrorCategory.FORMAT_ERROR,
        check=check_totals_numeric,
    ),
    
    # Business rules
    ValidationRule(
        code="business_rule:line_items_mismatch",
        description="Sum of line item totals should equal net total",
        category=ErrorCategory.BUSINESS_RULE,
        check=check_line_items_sum,
    ),
    ValidationRule(
        code="business_rule:totals_mismatch",
        description="net_total + tax_amount should equal gross_total",
        category=ErrorCategory.BUSINESS_RULE,
        check=check_totals_consistency,
    ),
    ValidationRule(
        code="business_rule:invalid_due_date",
        description="Due date must not be earlier than invoice date",
        category=ErrorCategory.BUSINESS_RULE,
        check=check_due_date_valid,
    ),
    ValidationRule(
        code="business_rule:line_item_calculation",
        description="Line item quantity × unit_price should equal line_total",
        category=ErrorCategory.BUSINESS_RULE,
        check=check_line_items_validity,
    ),
    
    # Anomaly rules
    ValidationRule(
        code="anomaly:negative_totals",
        description="Invoice totals should not be negative",
        category=ErrorCategory.ANOMALY,
        check=check_non_negative_totals,
    ),
    ValidationRule(
        code="anomaly:duplicate_invoice",
        description="Invoice should be unique (by number, seller, and date)",
        category=ErrorCategory.ANOMALY,
        check=check_duplicate_invoice,
    ),
    ValidationRule(
        code="anomaly:unreasonable_amounts",
        description="Invoice amounts should be within reasonable bounds",
        category=ErrorCategory.ANOMALY,
        check=check_unreasonable_amounts,
    ),
]


def get_rules_by_category(category: ErrorCategory) -> list[ValidationRule]:
    """Get all rules belonging to a specific category."""
    return [rule for rule in VALIDATION_RULES if rule.category == category]


def get_rule_descriptions() -> dict[str, str]:
    """Get a mapping of rule codes to their descriptions."""
    return {rule.code: rule.description for rule in VALIDATION_RULES}
