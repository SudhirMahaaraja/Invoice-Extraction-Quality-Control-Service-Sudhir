# Key Prompts Used with AI Assistant

## 1. Initial Project Setup
```
Create an Invoice Extraction & Quality Control Service with:
- PDF extraction using pdfplumber
- Validation against configurable rules
- CLI and REST API interfaces
- Web-based QC console (bonus)
```

## 2. Schema Design
```
Design a Pydantic schema with 8-10 invoice fields plus line items.
Include: invoice_number, seller/buyer info, dates, currency, totals, line_items
```

## 3. Validation Rules
```
Implement 14 validation rules across 4 categories:
- Completeness: Required fields check
- Format: Currency codes, numeric types
- Business: Totals consistency, due date after invoice date
- Anomaly: Duplicates, zero values, negative amounts
```

## 4. German Invoice Support
```
Fix extraction for German invoices:
- Parse dates like "02.05.2022"
- Handle amounts like "257,04" (European decimal format)
- Extract from labels like "Gesamtwert EUR 216,00"
- Get line items from "1 LED-Monitore 12' 4 VE ... 64,00"
```

## 5. Bug Fixes
```
Fix the external_reference extraction - it's picking up "ration" from "Corporation"
```

```
Fix Unicode errors when printing checkmarks on Windows
```

## 6. Testing
```
Create pytest fixtures and test cases for:
- Number parsing (US and European formats)
- Date extraction
- Validation rules (all 14)
- Batch processing
```

---

## Prompt Engineering Tips Used

1. **Be specific**: "Parse dates like 02.05.2022" not just "handle dates"
2. **Provide examples**: Include actual text from PDFs
3. **Iterate**: Multiple rounds of refinement worked better than one big prompt
4. **Ask for edge cases**: "What about negative amounts? Zero values?"
