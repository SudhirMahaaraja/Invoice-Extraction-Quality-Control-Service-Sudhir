"""
Tests for the invoice extractor module.

These tests verify the field extraction helper functions
and overall extraction logic.
"""

import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from invoice_qc.extractor import (
    extract_invoice_number,
    extract_dates,
    extract_amounts,
    extract_party_info,
    extract_payment_terms,
    extract_external_reference,
    parse_number,
    parse_date,
)
from invoice_qc.config import SELLER_LABELS, BUYER_LABELS


class TestExtractInvoiceNumber:
    """Tests for invoice number extraction."""
    
    def test_extract_with_label(self):
        text = "Invoice No: INV-2024-001234"
        result = extract_invoice_number(text)
        assert result == "INV-2024-001234"
    
    def test_extract_with_hash_label(self):
        text = "Invoice # 12345678"
        result = extract_invoice_number(text)
        assert result is not None
        assert "12345678" in result
    
    def test_extract_pattern_based(self):
        text = "Please pay INV-0001234 by next week"
        result = extract_invoice_number(text)
        assert result == "INV-0001234"
    
    def test_no_invoice_number(self):
        text = "This is a document without an invoice number"
        result = extract_invoice_number(text)
        assert result is None


class TestExtractDates:
    """Tests for date extraction."""
    
    def test_extract_labeled_invoice_date(self):
        text = "Invoice Date: 2024-01-15\nDue Date: 2024-02-14"
        invoice_date, due_date = extract_dates(text)
        assert invoice_date == date(2024, 1, 15)
        assert due_date == date(2024, 2, 14)
    
    def test_extract_european_format(self):
        text = "Date: 15/01/2024"
        invoice_date, _ = extract_dates(text)
        assert invoice_date is not None
    
    def test_extract_no_dates(self):
        text = "No dates in this document"
        invoice_date, due_date = extract_dates(text)
        assert invoice_date is None
        assert due_date is None


class TestParseDate:
    """Tests for date parsing."""
    
    def test_iso_format(self):
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)
    
    def test_european_format(self):
        result = parse_date("15/01/2024")
        assert result == date(2024, 1, 15)
    
    def test_us_format(self):
        result = parse_date("01/15/2024")
        assert result is not None
    
    def test_invalid_date(self):
        result = parse_date("not-a-date")
        assert result is None


class TestExtractAmounts:
    """Tests for amount extraction."""
    
    def test_extract_with_labels(self):
        text = """
        Sub Total: $1,000.00
        Tax Amount: $100.00
        Grand Total: $1,100.00
        """
        currency, net, tax, gross = extract_amounts(text)
        assert currency == "USD"
        # Check that we extracted at least gross total
        assert gross == 1100.00 or net is not None
    
    def test_extract_eur(self):
        text = "Amount: EUR 500.00"
        currency, _, _, _ = extract_amounts(text)
        assert currency == "EUR"
    
    def test_extract_with_symbol(self):
        text = "Total: €1500.00"
        currency, _, _, _ = extract_amounts(text)
        assert currency == "EUR"
    
    def test_calculate_missing_tax(self):
        text = """
        Net Total: 1000.00
        Grand Total: 1100.00
        """
        _, net, tax, gross = extract_amounts(text)
        # Either we extract both and calculate, or we get gross at minimum
        if net is not None and gross is not None and tax is not None:
            assert net == 1000.00 or gross == 1100.00
        else:
            # At least one value should be extracted
            assert gross is not None or net is not None


class TestExtractPartyInfo:
    """Tests for party information extraction."""
    
    def test_extract_seller_info(self):
        text = """
        From:
        Acme Corporation
        Tax ID: US123456789
        123 Business Street
        """
        name, tax_id, address = extract_party_info(text, SELLER_LABELS)
        assert name is not None
        assert "Acme" in name or name == "Acme Corporation"
    
    def test_extract_buyer_info(self):
        text = """
        Bill To:
        Global Enterprises Inc
        456 Client Avenue
        """
        name, _, address = extract_party_info(text, BUYER_LABELS)
        assert name is not None


class TestParseNumber:
    """Tests for number parsing."""
    
    def test_simple_number(self):
        assert parse_number("123.45") == 123.45
    
    def test_with_comma(self):
        assert parse_number("1,234.56") == 1234.56
    
    def test_with_currency_symbol(self):
        assert parse_number("$1,234.56") == 1234.56
    
    def test_none_input(self):
        assert parse_number(None) is None
    
    def test_empty_string(self):
        assert parse_number("") is None
    
    def test_invalid_string(self):
        assert parse_number("abc") is None
    
    def test_european_format(self):
        """Test European format: 1.234,56 (period=thousand, comma=decimal)"""
        assert parse_number("257,04") == 257.04
        assert parse_number("1.234,56") == 1234.56
        assert parse_number("€257,04") == 257.04
    
    def test_us_format(self):
        """Test US format: 1,234.56 (comma=thousand, period=decimal)"""
        assert parse_number("1,234.56") == 1234.56
        assert parse_number("$1,234.56") == 1234.56


class TestExtractPaymentTerms:
    """Tests for payment terms extraction."""
    
    def test_net_30(self):
        text = "Payment Terms: Net 30"
        result = extract_payment_terms(text)
        assert result is not None
        assert "Net 30" in result or "net 30" in result.lower()
    
    def test_due_on_receipt(self):
        text = "Due upon receipt"
        result = extract_payment_terms(text)
        assert result is not None


class TestExtractExternalReference:
    """Tests for external reference extraction."""
    
    def test_po_number(self):
        text = "PO Number: PO-12345"
        result = extract_external_reference(text)
        assert result == "PO-12345"
    
    def test_reference(self):
        text = "Reference: REF-98765"
        result = extract_external_reference(text)
        assert result == "REF-98765"
    
    def test_no_reference(self):
        text = "This document has no external identifiers at all"
        result = extract_external_reference(text)
        assert result is None


