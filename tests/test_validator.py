"""
Tests for the invoice validator module.

These tests verify validation rules and the overall validation logic.
"""

import pytest
from datetime import date

from invoice_qc.schemas import Invoice, LineItem, InvoiceValidationResult, ValidationSummary
from invoice_qc.validator import validate_invoice, validate_batch, format_summary_text
from invoice_qc.rules import (
    check_invoice_number,
    check_invoice_date,
    check_seller_name,
    check_buyer_name,
    check_currency_valid,
    check_line_items_sum,
    check_totals_consistency,
    check_due_date_valid,
    check_non_negative_totals,
    check_duplicate_invoice,
    VALIDATION_RULES,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def valid_invoice() -> Invoice:
    """Create a valid invoice for testing."""
    return Invoice(
        invoice_number="INV-2024-001",
        seller_name="Acme Corp",
        buyer_name="Global Inc",
        invoice_date=date(2024, 1, 15),
        due_date=date(2024, 2, 14),
        currency="USD",
        net_total=1000.00,
        tax_amount=100.00,
        gross_total=1100.00,
        line_items=[
            LineItem(
                description="Service A",
                quantity=10,
                unit_price=100.00,
                line_total=1000.00,
            )
        ],
    )


@pytest.fixture
def invalid_invoice() -> Invoice:
    """Create an invoice with validation errors."""
    return Invoice(
        invoice_number="INV-2024-002",
        seller_name="Bad Corp",
        buyer_name="   ",  # Whitespace-only buyer name (passes Pydantic, fails validation)
        invoice_date=date(2024, 1, 15),
        due_date=date(2024, 1, 10),  # Due date before invoice date
        currency="XXX",  # Invalid currency (3 chars passes Pydantic, but not in allowed list)
        net_total=1000.00,
        tax_amount=100.00,
        gross_total=1200.00,  # Totals don't match (should be 1100)
        line_items=[],
    )


# ============================================================================
# Individual Rule Tests
# ============================================================================

class TestCompletenessRules:
    """Tests for completeness validation rules."""
    
    def test_check_invoice_number_valid(self, valid_invoice):
        result = check_invoice_number(valid_invoice)
        assert result is None
    
    def test_check_invoice_number_empty(self, valid_invoice):
        valid_invoice.invoice_number = ""
        result = check_invoice_number(valid_invoice)
        assert result == "missing_field:invoice_number"
    
    def test_check_seller_name_valid(self, valid_invoice):
        result = check_seller_name(valid_invoice)
        assert result is None
    
    def test_check_seller_name_empty(self, valid_invoice):
        valid_invoice.seller_name = "   "
        result = check_seller_name(valid_invoice)
        assert result == "missing_field:seller_name"
    
    def test_check_buyer_name_valid(self, valid_invoice):
        result = check_buyer_name(valid_invoice)
        assert result is None
    
    def test_check_buyer_name_empty(self, valid_invoice):
        valid_invoice.buyer_name = ""
        result = check_buyer_name(valid_invoice)
        assert result == "missing_field:buyer_name"


class TestFormatRules:
    """Tests for format validation rules."""
    
    def test_check_currency_valid(self, valid_invoice):
        result = check_currency_valid(valid_invoice)
        assert result is None
    
    def test_check_currency_invalid(self, valid_invoice):
        valid_invoice.currency = "INVALID"
        result = check_currency_valid(valid_invoice)
        assert result == "format_error:currency"
    
    def test_check_currency_eur(self, valid_invoice):
        valid_invoice.currency = "EUR"
        result = check_currency_valid(valid_invoice)
        assert result is None


class TestBusinessRules:
    """Tests for business logic validation rules."""
    
    def test_check_totals_consistency_valid(self, valid_invoice):
        result = check_totals_consistency(valid_invoice)
        assert result is None
    
    def test_check_totals_consistency_mismatch(self, valid_invoice):
        valid_invoice.gross_total = 1500.00  # Should be 1100
        result = check_totals_consistency(valid_invoice)
        assert result == "business_rule:totals_mismatch"
    
    def test_check_line_items_sum_valid(self, valid_invoice):
        result = check_line_items_sum(valid_invoice)
        assert result is None
    
    def test_check_line_items_sum_mismatch(self, valid_invoice):
        valid_invoice.line_items[0].line_total = 500.00  # Net is 1000
        result = check_line_items_sum(valid_invoice)
        assert result == "business_rule:line_items_mismatch"
    
    def test_check_line_items_sum_empty_list(self, valid_invoice):
        valid_invoice.line_items = []
        result = check_line_items_sum(valid_invoice)
        assert result is None  # Skip check for empty line items
    
    def test_check_due_date_valid(self, valid_invoice):
        result = check_due_date_valid(valid_invoice)
        assert result is None
    
    def test_check_due_date_before_invoice(self, valid_invoice):
        valid_invoice.due_date = date(2024, 1, 10)  # Before invoice date
        result = check_due_date_valid(valid_invoice)
        assert result == "business_rule:invalid_due_date"
    
    def test_check_due_date_none(self, valid_invoice):
        valid_invoice.due_date = None
        result = check_due_date_valid(valid_invoice)
        assert result is None


class TestAnomalyRules:
    """Tests for anomaly detection rules."""
    
    def test_check_non_negative_totals_valid(self, valid_invoice):
        result = check_non_negative_totals(valid_invoice)
        assert result is None
    
    def test_check_negative_net_total(self, valid_invoice):
        valid_invoice.net_total = -100.00
        result = check_non_negative_totals(valid_invoice)
        assert result == "anomaly:negative_net_total"
    
    def test_check_negative_tax_amount(self, valid_invoice):
        valid_invoice.tax_amount = -10.00
        result = check_non_negative_totals(valid_invoice)
        assert result == "anomaly:negative_tax_amount"
    
    def test_check_duplicate_no_context(self, valid_invoice):
        result = check_duplicate_invoice(valid_invoice, None)
        assert result is None
    
    def test_check_duplicate_first_occurrence(self, valid_invoice):
        context = {"seen_invoices": set()}
        result = check_duplicate_invoice(valid_invoice, context)
        assert result is None
    
    def test_check_duplicate_second_occurrence(self, valid_invoice):
        context = {"seen_invoices": set()}
        # First call
        check_duplicate_invoice(valid_invoice, context)
        # Second call with same invoice
        result = check_duplicate_invoice(valid_invoice, context)
        assert result == "anomaly:duplicate_invoice"


# ============================================================================
# Validator Integration Tests
# ============================================================================

class TestValidateInvoice:
    """Tests for the validate_invoice function."""
    
    def test_valid_invoice_passes(self, valid_invoice):
        result = validate_invoice(valid_invoice)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.invoice_id == valid_invoice.invoice_number
    
    def test_invalid_invoice_fails(self, invalid_invoice):
        result = validate_invoice(invalid_invoice)
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_multiple_errors_collected(self, invalid_invoice):
        result = validate_invoice(invalid_invoice)
        # Should have: missing buyer_name, invalid currency, totals mismatch, invalid due date
        assert len(result.errors) >= 3


class TestValidateBatch:
    """Tests for batch validation."""
    
    def test_batch_with_valid_invoices(self, valid_invoice):
        invoices = [valid_invoice]
        results, summary = validate_batch(invoices)
        
        assert len(results) == 1
        assert summary.total_invoices == 1
        assert summary.valid_invoices == 1
        assert summary.invalid_invoices == 0
    
    def test_batch_with_mixed_invoices(self, valid_invoice, invalid_invoice):
        invoices = [valid_invoice, invalid_invoice]
        results, summary = validate_batch(invoices)
        
        assert len(results) == 2
        assert summary.total_invoices == 2
        assert summary.valid_invoices == 1
        assert summary.invalid_invoices == 1
    
    def test_duplicate_detection_in_batch(self, valid_invoice):
        # Create two invoices with same key
        invoice2 = Invoice(
            invoice_number=valid_invoice.invoice_number,
            seller_name=valid_invoice.seller_name,
            buyer_name="Different Buyer",
            invoice_date=valid_invoice.invoice_date,
            currency="USD",
            net_total=500.00,
            tax_amount=50.00,
            gross_total=550.00,
        )
        
        invoices = [valid_invoice, invoice2]
        results, summary = validate_batch(invoices)
        
        # Second invoice should be flagged as duplicate
        assert summary.duplicates_detected >= 1
        duplicate_errors = [r for r in results if "duplicate" in str(r.errors)]
        assert len(duplicate_errors) >= 1
    
    def test_error_counts_aggregated(self, invalid_invoice):
        invoices = [invalid_invoice, invalid_invoice]
        results, summary = validate_batch(invoices)
        
        # Error counts should be aggregated
        assert len(summary.error_counts) > 0
        total_errors = sum(summary.error_counts.values())
        assert total_errors > 0


class TestFormatSummaryText:
    """Tests for summary text formatting."""
    
    def test_format_with_errors(self):
        summary = ValidationSummary(
            total_invoices=10,
            valid_invoices=7,
            invalid_invoices=3,
            error_counts={
                "missing_field:buyer_name": 2,
                "business_rule:totals_mismatch": 1,
            },
            duplicates_detected=1,
        )
        
        text = format_summary_text(summary)
        
        assert "Total invoices processed: 10" in text
        assert "Valid invoices:" in text
        assert "Invalid invoices:" in text
        assert "missing_field:buyer_name" in text
    
    def test_format_no_errors(self):
        summary = ValidationSummary(
            total_invoices=5,
            valid_invoices=5,
            invalid_invoices=0,
            error_counts={},
        )
        
        text = format_summary_text(summary)
        
        assert "Total invoices processed: 5" in text
        assert "Valid invoices" in text


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_empty_batch(self):
        results, summary = validate_batch([])
        assert summary.total_invoices == 0
        assert summary.valid_invoices == 0
        assert summary.invalid_invoices == 0
    
    def test_invoice_with_zero_amounts(self, valid_invoice):
        valid_invoice.net_total = 0.0
        valid_invoice.tax_amount = 0.0
        valid_invoice.gross_total = 0.0
        valid_invoice.line_items = []
        
        result = validate_invoice(valid_invoice)
        # Should trigger zero value warning
        warnings_or_errors = result.warnings + result.errors
        zero_warnings = [w for w in warnings_or_errors if "zero" in w]
        assert len(zero_warnings) >= 1
    
    def test_tolerance_boundary(self, valid_invoice):
        # Set gross to be just within tolerance
        valid_invoice.gross_total = 1100.005  # Within 0.01 tolerance
        result = validate_invoice(valid_invoice)
        totals_errors = [e for e in result.errors if "totals_mismatch" in e]
        assert len(totals_errors) == 0
    
    def test_tolerance_exceeded(self, valid_invoice):
        # Set gross to exceed tolerance
        valid_invoice.gross_total = 1100.02  # Beyond 0.01 tolerance
        result = validate_invoice(valid_invoice)
        totals_errors = [e for e in result.errors if "totals_mismatch" in e]
        assert len(totals_errors) == 1
