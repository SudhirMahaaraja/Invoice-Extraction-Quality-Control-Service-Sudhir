# AI Usage Log

## Project: Invoice Extraction & Quality Control Service

**AI Assistant Used**: Google Antigravity AI Agent (Claude-based)  
**Development Period**: December 2025

---

## Summary of AI Assistance

### 1. Project Scaffolding
- **Task**: Initial directory structure and file organization
- **AI Contribution**: Generated the modular Python package structure (`invoice_qc/`)
- **Human Review**: Approved structure with minor adjustments

### 2. Schema Design
- **Task**: Define Pydantic models for Invoice and LineItem
- **AI Contribution**: Designed 16 invoice-level fields + 6 line item fields
- **Validation**: Tested field types and constraints work correctly

### 3. Validation Rules
- **Task**: Implement 14 configurable validation rules
- **AI Contribution**: Wrote rule functions for completeness, format, business, and anomaly detection
- **Categories**:
  - 5 completeness rules (missing_field:*)
  - 2 format rules (format_error:*)
  - 4 business rules (business_rule:*)
  - 3 anomaly rules (anomaly:*)

### 4. PDF Extraction
- **Task**: Extract structured data from German invoice PDFs
- **AI Contribution**:
  - Initial regex patterns for dates, amounts, invoice numbers
  - European decimal format handling (comma as decimal separator)
  - German label detection (Gesamtwert, MwSt, Artikelbeschreibung)
  - Seller extraction from header format
- **Iterations**: 3 rounds of refinement for German formats

### 5. CLI & API
- **Task**: Build Typer CLI and FastAPI endpoints
- **AI Contribution**: Generated boilerplate and command structure
- **Human Review**: Tested all commands manually

### 6. Test Suite
- **Task**: Create pytest fixtures and test cases
- **AI Contribution**: 66 unit tests covering extractors and validators
- **Coverage**: All edge cases for number parsing, date formats, validation rules

### 7. Web Console (Bonus)
- **Task**: HTML/JS frontend for QC interface
- **AI Contribution**: Generated responsive UI with file upload and JSON paste features

---

## AI Limitations Encountered

### 1. Date Parsing Edge Cases
**Problem**: Initial regex patterns missed formats like "15th January 2024"  
**Solution**: Added `python-dateutil` as fallback parser

### 2. European Number Format (257,04)
**Problem**: AI initially treated comma as thousand separator (US format)  
**Solution**: Added logic to detect European format by checking comma position relative to period

### 3. Table Extraction Failure
**Problem**: pdfplumber didn't extract line item tables from German PDFs  
**Solution**: Implemented fallback text-based extraction with pattern matching

### 4. External Reference Bug
**Problem**: Regex matched "ration" from "Corporation"  
**Solution**: Added word boundary checks (`\b`) and validation of extracted values

### 5. Unicode Output on Windows
**Problem**: CLI crashed with UnicodeEncodeError when printing checkmarks  
**Solution**: Replaced Unicode `✓` with ASCII `[OK]`

---

## Key Design Decisions (AI-Influenced)

| Decision | Rationale |
|----------|-----------|
| Pydantic for schemas | Type safety + automatic validation |
| Rule registry pattern | Extensible and testable |
| Label-based extraction | More robust than fixed positions |
| Tolerance for float comparison | Prevent false positives (0.01 threshold) |
| Fallback defaults | Graceful degradation for missing data |

---

## Code Review Points

1. **extractor.py**: 700+ lines - consider splitting into modules
2. **parse_number()**: European format detection is heuristic-based
3. **Line item extraction**: Works for German VE format, may need extension for other formats

---

## Verification of AI Output

All AI-generated code was:
- [x] Reviewed manually before commit
- [x] Tested with 66 automated tests
- [x] Validated against 5 sample German invoices
- [x] Checked for security issues (no external API calls, no data leakage)

---

## Chat Export

The full conversation with the AI assistant is available upon request.
Key topics covered:
1. Schema design and field selection
2. German invoice format analysis
3. Validation rule implementation
4. Bug fixes and refinements
5. Test case design
