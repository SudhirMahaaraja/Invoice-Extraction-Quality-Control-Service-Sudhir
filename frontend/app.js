/**
 * Invoice QC Console - Application Logic
 * 
 * Handles API communication, file uploads, JSON validation,
 * and results display.
 */

// ============================================================
// Configuration
// ============================================================

let API_URL = 'http://localhost:8000';
let selectedFiles = [];
let validationResults = null;

// ============================================================
// Initialization
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Load saved API URL
    const savedUrl = localStorage.getItem('apiUrl');
    if (savedUrl) {
        document.getElementById('apiUrl').value = savedUrl;
        API_URL = savedUrl;
    }

    // Check API health on load
    checkApiHealth();

    // Setup file upload handlers
    setupFileUpload();
});

// ============================================================
// API Communication
// ============================================================

async function checkApiHealth() {
    const urlInput = document.getElementById('apiUrl');
    API_URL = urlInput.value.replace(/\/$/, ''); // Remove trailing slash
    localStorage.setItem('apiUrl', API_URL);

    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');

    try {
        const response = await fetch(`${API_URL}/health`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();
            statusDot.className = 'status-dot online';
            statusText.textContent = `Connected (v${data.version})`;
        } else {
            throw new Error('API returned non-OK status');
        }
    } catch (error) {
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Disconnected';
        console.error('API health check failed:', error);
    }
}

// ============================================================
// Tab Switching
// ============================================================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

// ============================================================
// File Upload
// ============================================================

function setupFileUpload() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    // Click to select files
    dropZone.addEventListener('click', () => fileInput.click());

    // File selection
    fileInput.addEventListener('change', (e) => {
        addFiles(e.target.files);
    });

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        addFiles(e.dataTransfer.files);
    });
}

function addFiles(files) {
    for (const file of files) {
        if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
            // Check for duplicates
            if (!selectedFiles.find(f => f.name === file.name)) {
                selectedFiles.push(file);
            }
        }
    }
    updateFileList();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
}

function updateFileList() {
    const fileList = document.getElementById('fileList');
    const uploadBtn = document.getElementById('uploadBtn');

    if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        uploadBtn.disabled = true;
        return;
    }

    fileList.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-item">
            <span class="file-name">📄 ${file.name}</span>
            <button class="remove-btn" onclick="removeFile(${index})">×</button>
        </div>
    `).join('');

    uploadBtn.disabled = false;
}

// ============================================================
// Validation Actions
// ============================================================

async function uploadAndValidate() {
    if (selectedFiles.length === 0) return;

    showLoading(true);
    hideError();

    try {
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        const response = await fetch(`${API_URL}/extract-and-validate-pdfs`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();
        displayResults(data.validation_summary, data.per_invoice_results);

    } catch (error) {
        showError(`Upload failed: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

async function validateJson() {
    const jsonInput = document.getElementById('jsonInput').value.trim();

    if (!jsonInput) {
        showError('Please enter JSON data');
        return;
    }

    showLoading(true);
    hideError();

    try {
        // Parse JSON to validate format
        let invoices;
        try {
            invoices = JSON.parse(jsonInput);
            if (!Array.isArray(invoices)) {
                invoices = [invoices];
            }
        } catch (e) {
            throw new Error('Invalid JSON format');
        }

        const response = await fetch(`${API_URL}/validate-json`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ invoices })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Validation failed');
        }

        const data = await response.json();
        displayResults(data.summary, data.per_invoice_results);

    } catch (error) {
        showError(`Validation failed: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

// ============================================================
// Results Display
// ============================================================

function displayResults(summary, results) {
    validationResults = results;

    // Show results section
    document.getElementById('resultsSection').style.display = 'block';

    // Update summary cards
    document.getElementById('totalCount').textContent = summary.total_invoices;
    document.getElementById('validCount').textContent = summary.valid_invoices;
    document.getElementById('invalidCount').textContent = summary.invalid_invoices;
    document.getElementById('duplicateCount').textContent = summary.duplicates_detected;

    // Display results table
    renderResultsTable(results);

    // Display error distribution
    renderErrorDistribution(summary.error_counts);

    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

function renderResultsTable(results) {
    const tbody = document.getElementById('resultsBody');
    const showInvalidOnly = document.getElementById('showInvalidOnly').checked;

    const filteredResults = showInvalidOnly
        ? results.filter(r => !r.is_valid)
        : results;

    // Update result count
    document.getElementById('resultCount').textContent =
        `Showing ${filteredResults.length} of ${results.length} invoices`;

    if (filteredResults.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: var(--color-text-muted);">
                    ${showInvalidOnly ? 'No invalid invoices found!' : 'No results to display'}
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filteredResults.map((result, index) => `
        <tr onclick="showInvoiceDetails(${index})">
            <td>
                <code style="font-family: var(--font-mono); font-weight: 600; color: var(--color-text);">${escapeHtml(result.invoice_id)}</code>
            </td>
            <td>
                <span class="badge ${result.is_valid ? 'badge-valid' : 'badge-invalid'}">
                    ${result.is_valid ? '✓ Valid' : '✗ Invalid'}
                </span>
            </td>
            <td>
                <div class="tag-list">
                    ${result.errors.length > 0
            ? result.errors.map(e => `<span class="tag error">${escapeHtml(e)}</span>`).join('')
            : '<span class="tag">None</span>'}
                </div>
            </td>
            <td>
                <div class="tag-list">
                    ${result.warnings.length > 0
            ? result.warnings.map(w => `<span class="tag warning">${escapeHtml(w)}</span>`).join('')
            : '<span class="tag">None</span>'}
                </div>
            </td>
        </tr>
    `).join('');
}

function renderErrorDistribution(errorCounts) {
    const container = document.getElementById('errorBars');

    if (!errorCounts || Object.keys(errorCounts).length === 0) {
        container.innerHTML = '<p style="color: var(--color-text-muted);">No errors detected</p>';
        return;
    }

    // Sort by count descending
    const sortedErrors = Object.entries(errorCounts)
        .sort((a, b) => b[1] - a[1]);

    const maxCount = sortedErrors[0][1];

    container.innerHTML = sortedErrors.map(([code, count]) => {
        const percentage = (count / maxCount) * 100;
        return `
            <div class="error-bar">
                <div class="error-bar-label">
                    <code>${escapeHtml(code)}</code>
                    <span>${count}</span>
                </div>
                <div class="error-bar-track">
                    <div class="error-bar-fill" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

function filterResults() {
    if (validationResults) {
        renderResultsTable(validationResults);
    }
}

// ============================================================
// Modal Logic
// ============================================================

function showInvoiceDetails(index) {
    const result = validationResults[index];
    if (!result) return;

    const invoice = result.invoice_data || {};
    const modal = document.getElementById('invoiceModal');
    const detailsContainer = document.getElementById('invoiceDetails');

    // Format currency
    const formatCurrency = (amount, currency) => {
        if (amount === null || amount === undefined) return '<span class="detail-value null">null</span>';
        return new Intl.NumberFormat('de-DE', { style: 'currency', currency: currency || 'EUR' }).format(amount);
    };

    // Helper for fields
    const renderField = (label, value, isAmount = false) => {
        let displayValue = value;
        if (value === null || value === undefined) {
            displayValue = '<span class="detail-value null">null</span>';
        } else if (isAmount) {
            displayValue = `<span class="detail-value amount">${formatCurrency(value, invoice.currency)}</span>`;
        } else {
            displayValue = escapeHtml(String(value));
        }

        return `
            <div class="detail-item">
                <div class="detail-label">${label}</div>
                <div class="detail-value">${displayValue}</div>
            </div>
        `;
    };

    // Build HTML
    let html = `
        <div class="invoice-details-grid">
            ${renderField('Invoice Number', invoice.invoice_number)}
            ${renderField('Date', invoice.invoice_date)}
            ${renderField('Seller', invoice.seller_name)}
            ${renderField('Buyer', invoice.buyer_name)}
            ${renderField('Net Total', invoice.net_total, true)}
            ${renderField('Tax Amount', invoice.tax_amount, true)}
            ${renderField('Gross Total', invoice.gross_total, true)}
            ${renderField('Currency', invoice.currency)}
            ${renderField('External Ref', invoice.external_reference)}
            ${renderField('Payment Terms', invoice.payment_terms)}
        </div>
        
        <div class="line-items-section">
            <h3>Line Items (${invoice.line_items ? invoice.line_items.length : 0})</h3>
            <table class="line-items-table">
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Qty</th>
                        <th>Unit Price</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
    `;

    if (invoice.line_items && invoice.line_items.length > 0) {
        html += invoice.line_items.map(item => `
            <tr>
                <td>${escapeHtml(item.description)}</td>
                <td>${item.quantity}</td>
                <td>${formatCurrency(item.unit_price, invoice.currency)}</td>
                <td>${formatCurrency(item.line_total, invoice.currency)}</td>
            </tr>
        `).join('');
    } else {
        html += `<tr><td colspan="4" style="text-align: center; color: var(--color-text-muted);">No line items found</td></tr>`;
    }

    html += `
                </tbody>
            </table>
        </div>
    `;

    detailsContainer.innerHTML = html;
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent scrolling
}

function closeModal(event) {
    // If event is provided, only close if clicking overlay
    if (event && event.target !== event.currentTarget) return;

    document.getElementById('invoiceModal').style.display = 'none';
    document.body.style.overflow = ''; // Restore scrolling
}

// ============================================================
// UI Helpers
// ============================================================

function showLoading(show) {
    const loading = document.getElementById('loading');
    loading.classList.toggle('active', show);
}

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    errorText.textContent = message;
    errorMessage.style.display = 'flex';
}

function hideError() {
    document.getElementById('errorMessage').style.display = 'none';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
