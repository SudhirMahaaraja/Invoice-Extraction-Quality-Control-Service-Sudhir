"""
PDF extraction module for converting invoice PDFs to structured data.

This module provides functionality to:
- Extract raw text from PDF files using pdfplumber
- Parse extracted text to identify invoice fields
- Handle various invoice layouts and formats
- Output structured Invoice objects
"""

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pdfplumber

from .config import (
    DATE_FORMATS,
    INVOICE_NUMBER_LABELS,
    SELLER_LABELS,
    BUYER_LABELS,
    SUPPORTED_CURRENCIES,
    logger,
)
from .schemas import Invoice, LineItem


# ============================================================================
# Text Extraction
# ============================================================================

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract all text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Concatenated text from all pages
    """
    text_parts = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
        return ""
    
    return "\n".join(text_parts)


def extract_tables_from_pdf(pdf_path: Path) -> list[list[list[str]]]:
    """
    Extract table data from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of tables, where each table is a list of rows (list of cell strings)
    """
    tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception as e:
        logger.error(f"Error extracting tables from {pdf_path}: {e}")
    
    return tables


# ============================================================================
# Field Extraction Helpers
# ============================================================================

def extract_invoice_number(text: str) -> Optional[str]:
    """
    Extract invoice number from text using label search and patterns.
    
    Looks for common invoice number labels and extracts the value following them.
    Also tries to match common invoice number patterns.
    """
    text_lower = text.lower()
    
    # Try label-based extraction
    for label in INVOICE_NUMBER_LABELS:
        pattern = rf"{re.escape(label)}\s*[:\s]*([A-Za-z0-9\-_/]+)"
        match = re.search(pattern, text_lower)
        if match:
            # Get the actual case from original text
            start = match.start(1)
            end = match.end(1)
            # Find the position in original text (approximate)
            original_match = re.search(
                rf"(?i){re.escape(label)}\s*[:\s]*([A-Za-z0-9\-_/]+)", 
                text
            )
            if original_match:
                return original_match.group(1).strip()
    
    # Try pattern-based extraction (INV-XXXX, Invoice-XXXX, etc.)
    patterns = [
        r'\b(INV[-_]?\d{4,}[-\w]*)\b',
        r'\b(INVOICE[-_]?\d{4,}[-\w]*)\b',
        r'\b([A-Z]{2,4}[-_]\d{6,})\b',
        r'#\s*(\d{5,})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None


def extract_dates(text: str) -> tuple[Optional[date], Optional[date]]:
    """
    Extract invoice date and due date from text.
    
    Returns:
        Tuple of (invoice_date, due_date), either may be None
    """
    invoice_date = None
    due_date = None
    
    # Look for labeled dates
    date_patterns = [
        (r'(?:invoice\s+date|date\s+of\s+invoice|dated?)\s*[:\s]*(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4})', 'invoice'),
        (r'(?:due\s+date|payment\s+due|pay\s+by)\s*[:\s]*(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4})', 'due'),
        (r'(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})', 'generic'),
        (r'(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})', 'generic'),
        (r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', 'generic'),
        (r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})', 'generic'),
    ]
    
    found_dates = []
    
    for pattern, date_type in date_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            date_str = match.group(1)
            parsed_date = parse_date(date_str)
            if parsed_date:
                if date_type == 'invoice' and invoice_date is None:
                    invoice_date = parsed_date
                elif date_type == 'due' and due_date is None:
                    due_date = parsed_date
                elif date_type == 'generic':
                    found_dates.append(parsed_date)
    
    # If we didn't find labeled dates, use generic ones
    if invoice_date is None and found_dates:
        # Assume first date is invoice date
        invoice_date = min(found_dates)
    if due_date is None and len(found_dates) > 1:
        # Assume last date is due date
        due_date = max(found_dates)
    
    return invoice_date, due_date


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse a date string using multiple format patterns.
    """
    # Clean the date string
    date_str = date_str.strip()
    
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    # Try additional formats
    try:
        # Handle formats like "15 January 2024" or "January 15, 2024"
        from dateutil import parser as date_parser
        return date_parser.parse(date_str).date()
    except:
        pass
    
    return None


def extract_party_info(text: str, labels: list[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract party information (name, tax_id, address) from text.
    
    Args:
        text: Full invoice text
        labels: List of labels to search for (e.g., SELLER_LABELS or BUYER_LABELS)
        
    Returns:
        Tuple of (name, tax_id, address)
    """
    name = None
    tax_id = None
    address = None
    
    text_lower = text.lower()
    lines = text.split('\n')
    
    # Find the section for this party
    start_idx = -1
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        for label in labels:
            if label in line_lower:
                start_idx = i
                # Try to extract info from the same line or following lines
                remaining = line_lower.split(label, 1)[-1].strip()
                if remaining and remaining not in [':', '']:
                    name = line.split(label.title(), 1)[-1].strip() if label.title() in line else remaining
                    name = name.lstrip(':').strip()
                break
        if start_idx >= 0:
            break
    
    # Look at following lines for additional info
    if start_idx >= 0:
        for i in range(start_idx + 1, min(start_idx + 6, len(lines))):
            line = lines[i].strip()
            if not line:
                continue
            
            # Check if we've hit another section
            if any(stop in line.lower() for stop in ['invoice', 'date', 'total', 'item', 'description', 'qty']):
                break
            
            # First non-empty line after label is likely the name
            if name is None and line:
                name = line
            # Look for tax ID patterns
            elif re.search(r'\b(tax\s*id|vat|gst|tin|ein)\s*[:\s]*([A-Z0-9\-]+)', line, re.IGNORECASE):
                match = re.search(r'[:\s]*([A-Z0-9\-]{5,})', line)
                if match:
                    tax_id = match.group(1)
            # Collect potential address lines
            elif address is None and len(line) > 10:
                address = line
    
    return name, tax_id, address


def extract_seller_from_header(text: str) -> Optional[str]:
    """
    Extract seller name from German invoice header format.
    
    German invoices often start with: "Company Name Bestellung AUFNR..."
    """
    lines = text.split('\n')
    
    for line in lines[:5]:  # Check first 5 lines
        # Pattern: "CompanyName Bestellung AUFNRxxxxx" or "CompanyName Lieferschein..."
        match = re.search(r'^([A-Za-z][A-Za-z0-9\s&\.\-]+?)\s+(?:Bestellung|Lieferschein|Rechnung)\s+(?:AUFNR|Nr\.?|#)', line, re.IGNORECASE)
        if match:
            seller = match.group(1).strip()
            # Clean up - remove trailing special chars
            seller = re.sub(r'\s+$', '', seller)
            if len(seller) >= 3:
                return seller
    
    return None


def extract_amounts(text: str) -> tuple[Optional[str], Optional[float], Optional[float], Optional[float]]:
    """
    Extract currency and financial amounts from text.
    
    Returns:
        Tuple of (currency, net_total, tax_amount, gross_total)
    """
    currency = None
    net_total = None
    tax_amount = None
    gross_total = None
    
    # Extract currency
    for curr in SUPPORTED_CURRENCIES:
        if curr in text.upper():
            currency = curr
            break
    
    # Also check for currency symbols
    currency_symbols = {
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        '₹': 'INR',
        '¥': 'JPY',
    }
    for symbol, curr_code in currency_symbols.items():
        if symbol in text:
            currency = curr_code
            break
    
    # Extract amounts with labels (English + German)
    # Note: More specific patterns must come first to avoid partial matches
    amount_patterns = [
        # English patterns
        (r'(?:sub\s*total|net\s*(?:total|amount))\s*[:\s]*[\$€£₹¥]?\s*([\d.,]+)', 'net'),
        (r'(?:tax|vat|gst)\s*(?:amount)?\s*[:\s]*[\$€£₹¥]?\s*([\d.,]+)', 'tax'),
        (r'(?:total|grand\s*total|amount\s*due|balance\s*due)\s*[:\s]*[\$€£₹¥]?\s*([\d.,]+)', 'gross'),
        # German patterns - handle "Gesamtwert EUR 216,00" format
        # IMPORTANT: "inkl. MwSt." pattern must come BEFORE plain "Gesamtwert" to match gross correctly
        (r'gesamtwert\s+inkl\.?\s*mwst\.?\s*(?:EUR|€)\s*([\d.,]+)', 'gross'),
        (r'(?:mwst\.?|mehrwertsteuer|ust\.?|umsatzsteuer)\s*[\d.,]*\s*%?\s*(?:EUR|€)\s*([\d.,]+)', 'tax'),
        (r'gesamtwert\s*(?:EUR|€)\s*([\d.,]+)', 'net'),  # Plain Gesamtwert = net
    ]
    
    for pattern, amount_type in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Use parse_number for consistent European format handling
            amount = parse_number(match.group(1))
            if amount is not None and amount > 0:
                if amount_type == 'net' and net_total is None:
                    net_total = amount
                elif amount_type == 'tax' and tax_amount is None:
                    tax_amount = amount
                elif amount_type == 'gross' and gross_total is None:
                    gross_total = amount
    
    # If we have gross and net but not tax, calculate tax
    if gross_total is not None and net_total is not None and tax_amount is None:
        tax_amount = gross_total - net_total
    
    # If we have gross and tax but not net, calculate net
    if gross_total is not None and tax_amount is not None and net_total is None:
        net_total = gross_total - tax_amount
    
    # If we only have one total, use it as gross and set others to 0
    if gross_total is None and net_total is not None:
        gross_total = net_total
        if tax_amount is None:
            tax_amount = 0.0
    
    return currency, net_total, tax_amount, gross_total


def extract_line_items(text: str, tables: list[list[list[str]]]) -> list[LineItem]:
    """
    Extract line items from invoice text and tables.
    
    Attempts to identify a table-like section and parse rows into line items.
    """
    line_items = []
    
    # First, try to extract from tables
    for table in tables:
        if not table or len(table) < 2:
            continue
        
        # Look for header row with relevant columns
        header_row = None
        data_start = 0
        
        for i, row in enumerate(table):
            if row is None:
                continue
            row_text = ' '.join(str(cell or '').lower() for cell in row)
            # English + German header keywords
            if any(kw in row_text for kw in [
                'description', 'item', 'qty', 'quantity', 'price', 'amount', 'total',
                'artikelbeschreibung', 'menge', 'preis', 'bestellwert', 'einheit', 'pos'
            ]):
                header_row = row
                data_start = i + 1
                break
        
        if header_row is None:
            continue
        
        # Identify column indices (English + German)
        header_lower = [str(h or '').lower() for h in header_row]
        
        # Description column
        desc_idx = next((i for i, h in enumerate(header_lower) 
                        if any(k in h for k in ['desc', 'item', 'particular', 'artikelbeschreibung', 'artikel'])), None)
        
        # Quantity column
        qty_idx = next((i for i, h in enumerate(header_lower) 
                       if any(k in h for k in ['qty', 'quantity', 'menge'])), None)
        
        # Price column
        price_idx = next((i for i, h in enumerate(header_lower) 
                         if any(k in h for k in ['price', 'rate', 'unit', 'preis']) and 'bestellwert' not in h), None)
        
        # Total column (line total)
        total_idx = next((i for i, h in enumerate(header_lower) 
                         if any(k in h for k in ['total', 'amount', 'bestellwert'])), None)
        
        # Parse data rows
        for row in table[data_start:]:
            if row is None or all(cell is None or str(cell).strip() == '' for cell in row):
                continue
            
            # Skip rows that look like subtotals (Gesamtwert, MwSt)
            row_text = ' '.join(str(cell or '').lower() for cell in row)
            if any(k in row_text for k in ['gesamtwert', 'mwst', 'summe', 'total']):
                continue
            
            try:
                # Get description - try index, fallback to first non-empty cell
                if desc_idx is not None and desc_idx < len(row):
                    description = str(row[desc_idx] or '').strip()
                else:
                    # Find first non-empty, non-numeric cell
                    description = ''
                    for cell in row:
                        cell_str = str(cell or '').strip()
                        if cell_str and not re.match(r'^[\d.,€$]+$', cell_str):
                            description = cell_str
                            break
                
                if not description or len(description) < 2:
                    continue
                
                # Get quantity
                quantity = 1.0
                if qty_idx is not None and qty_idx < len(row):
                    quantity = parse_number(row[qty_idx]) or 1.0
                
                # Get unit price
                unit_price = 0.0
                if price_idx is not None and price_idx < len(row):
                    unit_price = parse_number(row[price_idx]) or 0.0
                
                # Get line total - often last numeric column
                line_total = None
                if total_idx is not None and total_idx < len(row):
                    line_total = parse_number(row[total_idx])
                
                # If no line total found, try last cell
                if line_total is None:
                    for cell in reversed(row):
                        parsed = parse_number(cell)
                        if parsed is not None and parsed > 0:
                            line_total = parsed
                            break
                
                if line_total is None:
                    line_total = quantity * unit_price
                
                # Only add if we have meaningful data
                if line_total > 0 or unit_price > 0:
                    line_items.append(LineItem(
                        description=description[:200],  # Limit length
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=line_total,
                    ))
            except Exception as e:
                logger.debug(f"Error parsing line item row: {e}")
                continue
    
    # If no items from tables, try text-based extraction
    if not line_items:
        line_items = extract_line_items_from_text(text)
    
    return line_items


def extract_line_items_from_text(text: str) -> list[LineItem]:
    """
    Fallback line item extraction from raw text.
    
    Handles formats like:
    - "1 LED-Monitore 12' 4 VE 1 VE=20 Stück 64,00"
    - "Description ... Qty ... Price ... Total"
    """
    line_items = []
    lines = text.split('\n')
    
    # Pattern for German numbered line items: "1 Description ... amount"
    # Example: "1 LED-Monitore 12' 4 VE 1 VE=20 Stück 64,00"
    # Capture: pos_number, description, final_amount
    german_pattern = r'^(\d+)\s+(.+?)\s+\d+\s+VE.+?([\d,]+)\s*$'
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        
        # Skip header and footer lines
        skip_keywords = ['description', 'subtotal', 'grand', 'gesamtwert', 
                         'mwst', 'artikelbeschreibung', 'pos.', 'kostenstelle', 
                         'lief.art', 'interne mat']
        if any(kw in line.lower() for kw in skip_keywords):
            continue
        
        # Try German VE pattern: "1 Description 4 VE ... 64,00"
        match = re.match(german_pattern, line, re.IGNORECASE)
        if match:
            description = match.group(2).strip()
            amount_str = match.group(3)
            
            line_total = parse_number(amount_str)
            if line_total and line_total > 0 and len(description) >= 3:
                line_items.append(LineItem(
                    description=description[:200],
                    quantity=1.0,
                    unit_price=line_total,
                    line_total=line_total,
                ))
                continue
        
        # Fallback: Look for lines ending with amounts (European format)
        amount_pattern = r'[\d.,]+\s*$'
        if re.search(amount_pattern, line):
            # Try to parse as: description, quantity, price, total
            parts = re.split(r'\s{2,}|\t', line)
            if len(parts) >= 2:
                description = parts[0].strip()
                # Filter out position numbers
                if re.match(r'^\d+$', description):
                    description = parts[1].strip() if len(parts) > 1 else ''
                
                amounts = [parse_number(p) for p in parts[1:] if parse_number(p) is not None]
                
                if amounts and description and len(description) >= 3:
                    line_total = amounts[-1] if amounts else 0.0
                    unit_price = amounts[-2] if len(amounts) >= 2 else line_total
                    quantity = amounts[0] if len(amounts) >= 3 else 1.0
                    
                    if line_total > 0:
                        line_items.append(LineItem(
                            description=description[:200],
                            quantity=quantity,
                            unit_price=unit_price,
                            line_total=line_total,
                        ))
    
    return line_items[:20]  # Limit to reasonable number of items


def parse_number(value) -> Optional[float]:
    """
    Parse a numeric value from various formats.
    
    Handles both:
    - US/UK format: 1,234.56 (comma = thousand separator, period = decimal)
    - European format: 1.234,56 (period = thousand separator, comma = decimal)
    """
    if value is None:
        return None
    
    value_str = str(value).strip()
    if not value_str:
        return None
    
    # Remove currency symbols and whitespace
    value_str = re.sub(r'[\$€£₹¥\s]', '', value_str)
    
    # Detect and handle European format (e.g., 1.234,56 or 257,04)
    # If there's a comma and it comes after any periods, it's European format
    if ',' in value_str:
        comma_pos = value_str.rfind(',')
        period_pos = value_str.rfind('.')
        
        if period_pos < comma_pos:
            # European format: periods are thousand separators, comma is decimal
            # e.g., "1.234,56" -> "1234.56" or "257,04" -> "257.04"
            value_str = value_str.replace('.', '')  # Remove thousand separators
            value_str = value_str.replace(',', '.')  # Convert decimal comma to period
        else:
            # US format: commas are thousand separators, period is decimal
            # e.g., "1,234.56" -> "1234.56"
            value_str = value_str.replace(',', '')
    
    try:
        return float(value_str)
    except ValueError:
        return None


def extract_payment_terms(text: str) -> Optional[str]:
    """
    Extract payment terms from invoice text.
    """
    patterns = [
        r'(?:payment\s+terms?|terms?)\s*[:\s]*([^\n]{5,50})',
        r'(net\s+\d+\s*(?:days?)?)',
        r'(\d+/\d+\s+net\s+\d+)',
        r'(due\s+(?:on|upon)\s+receipt)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None


def extract_external_reference(text: str) -> Optional[str]:
    """
    Extract external references like PO numbers, order references.
    """
    patterns = [
        # English patterns - require word boundary before the label
        r'\b(?:p\.?o\.?\s*(?:number|no\.?|#)?|purchase\s+order)\s*[:\s]*([A-Za-z0-9\-_/]+)',
        r'\b(?:your\s+)?(?:reference|ref\.?)\s*[:\s]*([A-Za-z0-9\-_/]+)',
        r'\border\s*(?:number|no\.?|#)?\s*[:\s]*([A-Za-z0-9\-_/]+)',
        # German patterns
        r'\bim\s+Auftrag\s+von\s+(\d+)',  # "im Auftrag von 0293479054"
        r'\bAuftragsnummer\s*[:\s]*([A-Za-z0-9\-_/]+)',
        r'\bBestellnummer\s*[:\s]*([A-Za-z0-9\-_/]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            # Validate: must be at least 3 chars and not a common word fragment
            if len(result) >= 3 and result.lower() not in ['the', 'and', 'for', 'tion', 'ration']:
                return result
    
    return None


# ============================================================================
# Main Extraction Functions
# ============================================================================

def extract_invoice_from_pdf(pdf_path: Path) -> Invoice:
    """
    Extract a structured Invoice object from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Invoice object with extracted data (fields may be None if extraction failed)
        
    Raises:
        ValueError: If the PDF cannot be read or essential data cannot be extracted
    """
    logger.info(f"Extracting invoice from: {pdf_path.name}")
    
    # Extract text and tables
    text = extract_text_from_pdf(pdf_path)
    if not text:
        raise ValueError(f"Could not extract text from PDF: {pdf_path}")
    
    tables = extract_tables_from_pdf(pdf_path)
    
    # Extract individual fields
    invoice_number = extract_invoice_number(text)
    if not invoice_number:
        # Generate a fallback based on filename
        invoice_number = f"UNKNOWN-{pdf_path.stem}"
    
    invoice_date, due_date = extract_dates(text)
    if not invoice_date:
        # Use today as fallback
        invoice_date = date.today()
    
    seller_name, seller_tax_id, seller_address = extract_party_info(text, SELLER_LABELS)
    buyer_name, buyer_tax_id, buyer_address = extract_party_info(text, BUYER_LABELS)
    
    # Try German header format as fallback for seller name
    if not seller_name:
        seller_name = extract_seller_from_header(text)
    
    # Use placeholder if names couldn't be extracted
    if not seller_name:
        seller_name = "Unknown Seller"
    if not buyer_name:
        buyer_name = "Unknown Buyer"
    
    currency, net_total, tax_amount, gross_total = extract_amounts(text)
    
    # Defaults for missing amounts
    currency = currency or "USD"
    net_total = net_total or 0.0
    tax_amount = tax_amount or 0.0
    gross_total = gross_total or net_total + tax_amount
    
    line_items = extract_line_items(text, tables)
    payment_terms = extract_payment_terms(text)
    external_reference = extract_external_reference(text)
    
    invoice = Invoice(
        invoice_number=invoice_number,
        external_reference=external_reference,
        seller_name=seller_name,
        seller_tax_id=seller_tax_id,
        seller_address=seller_address,
        buyer_name=buyer_name,
        buyer_tax_id=buyer_tax_id,
        buyer_address=buyer_address,
        invoice_date=invoice_date,
        due_date=due_date,
        currency=currency,
        net_total=net_total,
        tax_amount=tax_amount,
        gross_total=gross_total,
        payment_terms=payment_terms,
        line_items=line_items,
    )
    
    logger.info(f"Extracted invoice: {invoice.invoice_number}")
    return invoice


def extract_invoices_from_dir(pdf_dir: Path) -> list[Invoice]:
    """
    Extract invoices from all PDF files in a directory.
    
    Args:
        pdf_dir: Path to directory containing PDF files
        
    Returns:
        List of extracted Invoice objects
    """
    if not pdf_dir.exists():
        raise FileNotFoundError(f"Directory not found: {pdf_dir}")
    
    pdf_files = list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.PDF"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in: {pdf_dir}")
        return []
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    invoices = []
    for pdf_path in pdf_files:
        try:
            invoice = extract_invoice_from_pdf(pdf_path)
            invoices.append(invoice)
        except Exception as e:
            logger.error(f"Failed to extract invoice from {pdf_path}: {e}")
    
    logger.info(f"Successfully extracted {len(invoices)} invoices")
    return invoices


def write_extracted_invoices(invoices: list[Invoice], output_path: Path) -> None:
    """
    Write extracted invoices to a JSON file.
    
    Args:
        invoices: List of Invoice objects
        output_path: Path to output JSON file
    """
    output_data = [invoice.model_dump(mode='json') for invoice in invoices]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    logger.info(f"Wrote {len(invoices)} invoices to: {output_path}")


def extract_invoice_from_bytes(pdf_bytes: bytes, filename: str = "uploaded.pdf") -> Invoice:
    """
    Extract an invoice from PDF bytes (for API uploads).
    
    Args:
        pdf_bytes: Raw PDF file content
        filename: Original filename for logging/identification
        
    Returns:
        Extracted Invoice object
    """
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)
    
    try:
        return extract_invoice_from_pdf(tmp_path)
    finally:
        tmp_path.unlink()
