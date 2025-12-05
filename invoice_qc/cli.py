"""
Command-line interface for the Invoice QC Service.

Provides three main commands:
- extract: Extract invoices from PDFs to JSON
- validate: Validate invoice JSON and generate report
- full-run: Extract and validate in one step
"""

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from .config import logger
from .extractor import extract_invoices_from_dir, write_extracted_invoices
from .schemas import Invoice, ValidationReport
from .validator import validate_batch, format_summary_text


# Create Typer app
app = typer.Typer(
    name="invoice-qc",
    help="Invoice Extraction & Quality Control Service CLI",
    add_completion=False,
)


@app.command()
def extract(
    pdf_dir: Path = typer.Option(
        ...,
        "--pdf-dir",
        "-p",
        help="Directory containing invoice PDF files",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        "extracted_invoices.json",
        "--output",
        "-o",
        help="Output JSON file path",
    ),
) -> None:
    """
    Extract invoices from PDF files to JSON.
    
    Reads all PDF files from the specified directory, extracts structured
    invoice data, and writes the results to a JSON file.
    """
    typer.echo(f"Extracting invoices from: {pdf_dir}")
    
    try:
        invoices = extract_invoices_from_dir(pdf_dir)
        
        if not invoices:
            typer.echo("No invoices were extracted.", err=True)
            raise typer.Exit(code=1)
        
        write_extracted_invoices(invoices, output)
        
        typer.echo(f"\n[OK] Extracted {len(invoices)} invoice(s) to: {output}")
        typer.echo("\nExtracted invoices:")
        for inv in invoices[:10]:  # Show first 10
            typer.echo(f"  - {inv.invoice_number} | {inv.seller_name} | {inv.gross_total} {inv.currency}")
        if len(invoices) > 10:
            typer.echo(f"  ... and {len(invoices) - 10} more")
            
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error during extraction: {e}", err=True)
        logger.exception("Extraction failed")
        raise typer.Exit(code=1)


@app.command()
def validate(
    input_file: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Input JSON file containing extracted invoices",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    report: Path = typer.Option(
        "validation_report.json",
        "--report",
        "-r",
        help="Output validation report JSON file path",
    ),
    fail_on_invalid: bool = typer.Option(
        False,
        "--fail-on-invalid",
        help="Exit with non-zero status if any invoices are invalid",
    ),
) -> None:
    """
    Validate invoices from a JSON file.
    
    Reads the extracted invoice JSON, runs validation rules, and generates
    a detailed report with per-invoice results and summary statistics.
    """
    typer.echo(f"Validating invoices from: {input_file}")
    
    try:
        # Load invoices from JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            invoice_data = json.load(f)
        
        if not isinstance(invoice_data, list):
            invoice_data = [invoice_data]
        
        invoices = [Invoice.model_validate(inv) for inv in invoice_data]
        
        if not invoices:
            typer.echo("No invoices found in input file.", err=True)
            raise typer.Exit(code=1)
        
        # Run validation
        results, summary = validate_batch(invoices)
        
        # Create and save report
        validation_report = ValidationReport(
            summary=summary,
            per_invoice_results=results,
        )
        
        with open(report, 'w', encoding='utf-8') as f:
            json.dump(validation_report.model_dump(), f, indent=2)
        
        # Print summary
        typer.echo("\n" + format_summary_text(summary))
        typer.echo(f"\n[OK] Validation report saved to: {report}")
        
        # Show invalid invoice details
        invalid_results = [r for r in results if not r.is_valid]
        if invalid_results:
            typer.echo("\nInvalid Invoices:")
            for r in invalid_results[:5]:  # Show first 5
                typer.echo(f"  {r.invoice_id}:")
                for err in r.errors:
                    typer.echo(f"    - {err}")
            if len(invalid_results) > 5:
                typer.echo(f"  ... and {len(invalid_results) - 5} more invalid invoices")
        
        # Exit with error if requested and there are invalid invoices
        if fail_on_invalid and summary.invalid_invoices > 0:
            raise typer.Exit(code=1)
            
    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON in input file: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error during validation: {e}", err=True)
        logger.exception("Validation failed")
        raise typer.Exit(code=1)


@app.command("full-run")
def full_run(
    pdf_dir: Path = typer.Option(
        ...,
        "--pdf-dir",
        "-p",
        help="Directory containing invoice PDF files",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    report: Path = typer.Option(
        "validation_report.json",
        "--report",
        "-r",
        help="Output validation report JSON file path",
    ),
    save_extracted: Optional[Path] = typer.Option(
        None,
        "--save-extracted",
        "-s",
        help="Also save extracted invoices to this JSON file",
    ),
    fail_on_invalid: bool = typer.Option(
        False,
        "--fail-on-invalid",
        help="Exit with non-zero status if any invoices are invalid",
    ),
) -> None:
    """
    Extract invoices from PDFs and validate them in one step.
    
    This combines the extract and validate commands for a streamlined workflow.
    """
    typer.echo(f"Running full extraction and validation pipeline")
    typer.echo(f"PDF directory: {pdf_dir}")
    
    try:
        # Extract invoices
        typer.echo("\n[1/2] Extracting invoices...")
        invoices = extract_invoices_from_dir(pdf_dir)
        
        if not invoices:
            typer.echo("No invoices were extracted.", err=True)
            raise typer.Exit(code=1)
        
        typer.echo(f"      Extracted {len(invoices)} invoice(s)")
        
        # Optionally save extracted invoices
        if save_extracted:
            write_extracted_invoices(invoices, save_extracted)
            typer.echo(f"      Saved extracted invoices to: {save_extracted}")
        
        # Validate invoices
        typer.echo("\n[2/2] Validating invoices...")
        results, summary = validate_batch(invoices)
        
        # Create and save report
        validation_report = ValidationReport(
            summary=summary,
            per_invoice_results=results,
        )
        
        with open(report, 'w', encoding='utf-8') as f:
            json.dump(validation_report.model_dump(), f, indent=2)
        
        # Print summary
        typer.echo("\n" + format_summary_text(summary))
        typer.echo(f"\n[OK] Validation report saved to: {report}")
        
        # Exit with error if requested and there are invalid invoices
        if fail_on_invalid and summary.invalid_invoices > 0:
            raise typer.Exit(code=1)
            
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        logger.exception("Full run failed")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Show version information."""
    from . import __version__
    typer.echo(f"Invoice QC Service v{__version__}")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
