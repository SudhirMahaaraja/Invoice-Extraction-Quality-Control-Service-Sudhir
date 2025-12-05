# Invoice QC Console - Frontend

A minimal web-based Quality Control console for validating B2B invoices.

## Features

- **PDF Upload**: Drag-and-drop or select PDF invoice files for extraction and validation
- **JSON Validation**: Paste invoice JSON directly for validation
- **Results Dashboard**: View validation results with summary cards and detailed table
- **Error Filtering**: Filter to show only invalid invoices
- **Error Distribution**: Visual breakdown of error types

## Usage

### Option 1: Direct File Access

Simply open `index.html` in a modern web browser. Make sure the API server is running at `http://localhost:8000`.

### Option 2: With a Local Server (Recommended)

Using Python:
```bash
cd frontend
python -m http.server 8080
```

Then open: http://localhost:8080

### Option 3: With Node.js

```bash
npx serve frontend
```

## Configuration

The API URL can be configured directly in the interface. By default, it connects to `http://localhost:8000`. The setting is saved in localStorage for persistence.

## API Endpoints Used

- `GET /health` - Check API connection status
- `POST /validate-json` - Validate JSON invoice data
- `POST /extract-and-validate-pdfs` - Upload and validate PDF files

## Browser Compatibility

Works in all modern browsers (Chrome, Firefox, Safari, Edge).
