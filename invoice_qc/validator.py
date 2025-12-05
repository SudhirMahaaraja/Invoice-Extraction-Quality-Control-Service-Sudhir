"""
Validation engine for invoice quality control.

This module orchestrates the validation of invoices against defined rules
and produces both per-invoice results and aggregated summaries.
"""

from collections import Counter
from typing import Optional

from .config import logger
from .rules import VALIDATION_RULES, ValidationRule
from .schemas import Invoice, InvoiceValidationResult, ValidationSummary, ValidationReport


def validate_invoice(
    invoice: Invoice,
    context: Optional[dict] = None,
    rules: Optional[list[ValidationRule]] = None
) -> InvoiceValidationResult:
    """
    Validate a single invoice against all defined rules.
    
    Args:
        invoice: The Invoice object to validate
        context: Optional context dict for stateful rules (e.g., duplicate detection)
        rules: Optional list of rules to apply (defaults to all VALIDATION_RULES)
        
    Returns:
        InvoiceValidationResult with all errors and warnings found
    """
    if rules is None:
        rules = VALIDATION_RULES
    
    if context is None:
        context = {}
    
    errors: list[str] = []
    warnings: list[str] = []
    
    for rule in rules:
        try:
            error_code = rule.check(invoice, context)
            if error_code:
                # Anomaly rules generate warnings, others generate errors
                if error_code.startswith("anomaly:"):
                    # Some anomalies are errors (duplicates), some are warnings
                    if "duplicate" in error_code or "negative" in error_code:
                        errors.append(error_code)
                    else:
                        warnings.append(error_code)
                else:
                    errors.append(error_code)
        except Exception as e:
            logger.error(f"Error running rule {rule.code} on invoice {invoice.invoice_number}: {e}")
            errors.append(f"rule_error:{rule.code}")
    
    return InvoiceValidationResult(
        invoice_id=invoice.invoice_number,
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_batch(
    invoices: list[Invoice],
    rules: Optional[list[ValidationRule]] = None
) -> tuple[list[InvoiceValidationResult], ValidationSummary]:
    """
    Validate a batch of invoices and produce aggregated summary.
    
    This function maintains context across invoices for rules that need
    batch-level information (e.g., duplicate detection).
    
    Args:
        invoices: List of Invoice objects to validate
        rules: Optional list of rules to apply
        
    Returns:
        Tuple of (list of per-invoice results, batch summary)
    """
    logger.info(f"Validating batch of {len(invoices)} invoices")
    
    # Shared context for batch-level rules
    context: dict = {
        "seen_invoices": set(),
    }
    
    results: list[InvoiceValidationResult] = []
    all_errors: list[str] = []
    all_warnings: list[str] = []
    
    for invoice in invoices:
        result = validate_invoice(invoice, context, rules)
        results.append(result)
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
    
    # Count errors and warnings
    error_counts = dict(Counter(all_errors))
    warning_counts = dict(Counter(all_warnings))
    
    # Calculate summary stats
    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count
    duplicates = sum(1 for e in all_errors if "duplicate" in e)
    
    summary = ValidationSummary(
        total_invoices=len(invoices),
        valid_invoices=valid_count,
        invalid_invoices=invalid_count,
        error_counts=error_counts,
        warning_counts=warning_counts,
        duplicates_detected=duplicates,
    )
    
    logger.info(f"Validation complete: {valid_count} valid, {invalid_count} invalid")
    
    return results, summary


def create_validation_report(
    invoices: list[Invoice],
    rules: Optional[list[ValidationRule]] = None
) -> ValidationReport:
    """
    Create a complete validation report for a batch of invoices.
    
    Args:
        invoices: List of Invoice objects to validate
        rules: Optional list of rules to apply
        
    Returns:
        ValidationReport containing summary and per-invoice results
    """
    results, summary = validate_batch(invoices, rules)
    
    return ValidationReport(
        summary=summary,
        per_invoice_results=results,
    )


def get_top_errors(summary: ValidationSummary, n: int = 5) -> list[tuple[str, int]]:
    """
    Get the top N most frequent error types from a summary.
    
    Args:
        summary: ValidationSummary to analyze
        n: Number of top errors to return
        
    Returns:
        List of (error_code, count) tuples, sorted by count descending
    """
    sorted_errors = sorted(
        summary.error_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    return sorted_errors[:n]


def format_summary_text(summary: ValidationSummary) -> str:
    """
    Format a ValidationSummary as human-readable text for CLI output.
    
    Args:
        summary: ValidationSummary to format
        
    Returns:
        Formatted string for display
    """
    lines = [
        "=" * 50,
        "VALIDATION SUMMARY",
        "=" * 50,
        f"Total invoices processed: {summary.total_invoices}",
        f"Valid invoices:           {summary.valid_invoices}",
        f"Invalid invoices:         {summary.invalid_invoices}",
        "",
    ]
    
    if summary.duplicates_detected > 0:
        lines.append(f"Duplicates detected:      {summary.duplicates_detected}")
        lines.append("")
    
    if summary.error_counts:
        lines.append("Top Error Types:")
        lines.append("-" * 40)
        for error_code, count in get_top_errors(summary):
            lines.append(f"  {error_code}: {count}")
        lines.append("")
    
    if summary.warning_counts:
        lines.append("Warnings:")
        lines.append("-" * 40)
        for warning_code, count in sorted(summary.warning_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {warning_code}: {count}")
        lines.append("")
    
    lines.append("=" * 50)
    
    return "\n".join(lines)
