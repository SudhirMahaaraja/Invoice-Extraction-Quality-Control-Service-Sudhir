"""
FastAPI application for the Invoice QC Service.

Provides REST API endpoints for:
- Health check
- JSON invoice validation
- PDF extraction and validation
"""

import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import logger, API_HOST, API_PORT, MAX_UPLOAD_SIZE_MB
from .extractor import extract_invoice_from_bytes
from .schemas import (
    Invoice,
    InvoiceValidationResult,
    ValidationSummary,
    ValidationReport,
    ExtractAndValidateResponse,
)
from .validator import validate_batch, create_validation_report


# ============================================================================
# FastAPI App Configuration
# ============================================================================

app = FastAPI(
    title="Invoice QC Service API",
    description="""
    Invoice Extraction & Quality Control Service API.
    
    This API provides endpoints for validating B2B invoices against
    configurable business rules and extracting structured data from PDFs.
    
    ## Features
    
    - **Validate JSON**: Submit invoice data directly for validation
    - **Extract & Validate PDFs**: Upload PDF invoices for extraction and validation
    - **Batch Processing**: Process multiple invoices in a single request
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "*",  # Allow all origins for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str


class ValidateJsonRequest(BaseModel):
    """Request body for JSON validation endpoint."""
    invoices: List[Invoice]
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "invoices": [{
                    "invoice_number": "INV-001",
                    "seller_name": "Acme Corp",
                    "buyer_name": "Global Inc",
                    "invoice_date": "2024-01-15",
                    "currency": "USD",
                    "net_total": 1000.00,
                    "tax_amount": 100.00,
                    "gross_total": 1100.00,
                    "line_items": []
                }]
            }]
        }
    }


class ValidateJsonResponse(BaseModel):
    """Response for JSON validation endpoint."""
    summary: ValidationSummary
    per_invoice_results: List[InvoiceValidationResult]


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the service status and version information.
    Use this endpoint for load balancer health checks and monitoring.
    """
    from . import __version__
    return HealthResponse(status="ok", version=__version__)


@app.post(
    "/validate-json",
    response_model=ValidateJsonResponse,
    tags=["Validation"],
    summary="Validate invoice JSON",
)
async def validate_json(request: ValidateJsonRequest) -> ValidateJsonResponse:
    """
    Validate a list of invoices provided as JSON.
    
    This endpoint accepts invoice data in JSON format and validates each
    invoice against the configured business rules. Returns per-invoice
    validation results and an aggregated summary.
    
    **Validation Rules Applied:**
    - Completeness checks (required fields present)
    - Format validation (valid currency, date formats)
    - Business logic (totals consistency, line items sum)
    - Anomaly detection (duplicates, negative values)
    """
    try:
        logger.info(f"Received validation request for {len(request.invoices)} invoices")
        
        results, summary = validate_batch(request.invoices)
        
        return ValidateJsonResponse(
            summary=summary,
            per_invoice_results=results,
        )
        
    except Exception as e:
        logger.exception("Validation failed")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@app.post(
    "/extract-and-validate-pdfs",
    response_model=ExtractAndValidateResponse,
    tags=["Extraction"],
    summary="Extract and validate PDF invoices",
)
async def extract_and_validate_pdfs(
    files: List[UploadFile] = File(..., description="PDF invoice files to process")
) -> ExtractAndValidateResponse:
    """
    Extract invoices from uploaded PDF files and validate them.
    
    This endpoint accepts multiple PDF files, extracts structured invoice
    data from each, and validates the extracted invoices against business rules.
    
    **Processing Steps:**
    1. Extract text and tables from each PDF
    2. Parse invoice fields (numbers, dates, amounts, parties)
    3. Validate extracted data against rules
    4. Return extracted invoices with validation results
    
    **Limitations:**
    - Maximum file size: 10MB per file
    - Supported formats: PDF only
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    max_size = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    extracted_invoices: List[Invoice] = []
    errors: List[str] = []
    
    for file in files:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            errors.append(f"{file.filename}: Not a PDF file")
            continue
        
        try:
            # Read file content
            content = await file.read()
            
            # Check file size
            if len(content) > max_size:
                errors.append(f"{file.filename}: File too large (max {MAX_UPLOAD_SIZE_MB}MB)")
                continue
            
            # Extract invoice
            invoice = extract_invoice_from_bytes(content, file.filename)
            extracted_invoices.append(invoice)
            
            logger.info(f"Successfully extracted invoice from: {file.filename}")
            
        except Exception as e:
            logger.error(f"Failed to extract from {file.filename}: {e}")
            errors.append(f"{file.filename}: Extraction failed - {str(e)}")
        
        finally:
            await file.seek(0)  # Reset file position
    
    if not extracted_invoices:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract any invoices. Errors: {'; '.join(errors)}"
        )
    
    # Validate extracted invoices
    results, summary = validate_batch(extracted_invoices)
    
    return ExtractAndValidateResponse(
        extracted_invoices=extracted_invoices,
        validation_summary=summary,
        per_invoice_results=results,
    )


@app.get("/rules", tags=["System"])
async def list_rules():
    """
    List all validation rules applied by the service.
    
    Returns the complete list of validation rules with their codes
    and descriptions, organized by category.
    """
    from .rules import VALIDATION_RULES, get_rules_by_category
    from .config import ErrorCategory
    
    rules_by_category = {}
    for category in ErrorCategory:
        category_rules = get_rules_by_category(category)
        if category_rules:
            rules_by_category[category.value] = [
                {"code": rule.code, "description": rule.description}
                for rule in category_rules
            ]
    
    return {
        "total_rules": len(VALIDATION_RULES),
        "rules_by_category": rules_by_category,
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info(f"Invoice QC Service API starting on {API_HOST}:{API_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Invoice QC Service API shutting down")


# ============================================================================
# Main Entry Point
# ============================================================================

def run_server():
    """Run the API server using uvicorn."""
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    run_server()
