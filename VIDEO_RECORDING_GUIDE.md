# Video Recording Guide

## Recording Requirements
- **Duration**: 10-20 minutes
- **Format**: Screen recording with audio narration

---

## Suggested Structure (15 min)

### Part 1: High-Level Overview (3 min)
1. Open `README.md` and show:
   - Project purpose
   - Architecture diagram (Mermaid flowchart)
   - Features table

2. Quick project structure tour:
   ```
   invoice_qc/       # Main package
   frontend/         # Web console
   samples/          # Test PDFs
   tests/            # pytest suite
   ai-notes/         # AI documentation
   ```

### Part 2: Schema & Validation Design (3 min)
1. Open `invoice_qc/schemas.py`:
   - Show Invoice model (16 fields)
   - Show LineItem model (6 fields)

2. Open `invoice_qc/rules.py`:
   - Show VALIDATION_RULES registry
   - Walk through one rule from each category:
     - Completeness: `check_required_field_invoice_number`
     - Business: `check_totals_consistency`
     - Anomaly: `check_duplicate_invoice`

### Part 3: Code Walkthrough (4 min)
1. Open `invoice_qc/extractor.py`:
   - Show `extract_invoice_from_pdf()` main function
   - Highlight `parse_number()` for European format
   - Show German label patterns

2. Open `invoice_qc/validator.py`:
   - Show `validate_batch()` function
   - Show how rules are applied and errors collected

3. Open `invoice_qc/cli.py`:
   - Show the three commands: extract, validate, full-run

### Part 4: Live Demo (5 min)
1. **Run extraction**:
   ```bash
   python -m invoice_qc.cli extract --pdf-dir ./samples/pdfs --output demo_extracted.json
   ```
   - Show extracted JSON

2. **Run validation**:
   ```bash
   python -m invoice_qc.cli validate --input demo_extracted.json --report demo_report.json
   ```
   - Show validation summary

3. **Start API** (optional):
   ```bash
   uvicorn invoice_qc.api:app --reload
   ```
   - Open http://localhost:8000/docs
   - Show Swagger UI

4. **Web Console** (optional):
   - Open `frontend/index.html`
   - Upload a PDF or paste JSON

5. **Run tests**:
   ```bash
   pytest tests/ -v
   ```
   - Show 66 tests passing

---

## Recording Tips

1. **Preparation**:
   - Close unnecessary applications
   - Set terminal font size to large
   - Pre-run commands once to avoid cold start delays

2. **Audio**:
   - Speak clearly and at moderate pace
   - Explain what you're showing, don't just read code

3. **Tools**:
   - OBS Studio (free): https://obsproject.com
   - Loom (easy): https://loom.com
   - Windows Game Bar: Win+G

4. **Save as**:
   - MP4 format recommended
   - Upload to Google Drive/YouTube unlisted
   - Share link in submission

---

## Key Points to Mention

1. "Schema has 16 invoice fields plus 6 line item fields"
2. "14 validation rules across 4 categories"
3. "Supports German invoice format with European decimals"
4. "Line items extracted from text patterns"
5. "All 66 tests pass"
6. "AI was used for code generation and debugging"
