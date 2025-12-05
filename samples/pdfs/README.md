# Sample PDFs Directory

Place your invoice PDF files in this directory for testing.

## Expected PDF Format

The extractor works best with PDFs that have:

1. **Clear text content** (not scanned images)
2. **Standard invoice labels** like:
   - "Invoice No", "Invoice Number", "Invoice #"
   - "Date", "Invoice Date"
   - "From", "Seller", "Vendor"
   - "To", "Bill To", "Buyer"
   - "Subtotal", "Net Total"
   - "Tax", "VAT", "GST"
   - "Total", "Grand Total", "Amount Due"

3. **Tabular line items** with columns for:
   - Description
   - Quantity
   - Unit Price
   - Amount/Total

## Testing

Run the extraction on this directory:

```bash
python -m invoice_qc.cli extract --pdf-dir ./samples/pdfs --output test_output.json
```

## Sample Invoice Structure

A typical invoice might look like:

```
INVOICE

Invoice No: INV-2024-001234
Date: January 15, 2024
Due Date: February 14, 2024

From:                           To:
Acme Software Solutions         Global Enterprises Inc
123 Tech Park, London           456 Business Ave, NYC
VAT: GB123456789               Tax ID: US-87654321

Description              Qty    Unit Price    Amount
Software Development     40     $150.00       $6,000.00
Cloud Setup              1      $4,000.00     $4,000.00

                         Subtotal:            $10,000.00
                         Tax (18%):           $1,800.00
                         Total:               $11,800.00

Payment Terms: Net 30
```
