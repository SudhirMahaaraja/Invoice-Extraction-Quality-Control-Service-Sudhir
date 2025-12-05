# GitHub Repository Setup Guide

## Step 1: Create Repository

1. Go to https://github.com/new
2. **Repository name**: `invoice-qc-service-sudhir` (or your preferred name)
3. **Description**: "Invoice Extraction & Quality Control Service"
4. **Visibility**: Private (you'll share access with reviewers)
5. Click "Create repository"

---

## Step 2: Initialize Git Locally

Open terminal in the project directory:

```bash
# Navigate to project
cd "E:\Invoice-Extraction-Quality-Control-Service"

# Initialize git (if not already)
git init

# Add all files
git add .

# Verify what's being added (should exclude __pycache__, venv, etc.)
git status

# Create initial commit
git commit -m "Initial commit: Invoice QC Service with German invoice support"
```

---

## Step 3: Push to GitHub

```bash
# Add remote origin (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/invoice-qc-service-sudhir.git

# Push to main branch
git push -u origin main

# If your default branch is 'master':
git push -u origin master
```

---

## Step 4: Add Collaborators

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Click **Collaborators** in the left sidebar
4. Click **Add people**
5. Add these usernames:
   - `deeplogicaitech`
   - `csvinay`
6. Click **Add to this repository**

They will receive an email invitation to access your repository.

---

## Step 5: Verify Repository Contents

Ensure these files are in your repository:

```
✅ README.md                  # Main documentation
✅ pyproject.toml             # Python dependencies
✅ .gitignore                 # Git ignore rules
✅ invoice_qc/                # Main package
   ├── __init__.py
   ├── api.py
   ├── cli.py
   ├── config.py
   ├── extractor.py
   ├── rules.py
   ├── schemas.py
   └── validator.py
✅ frontend/                   # Web console
   ├── index.html
   ├── styles.css
   └── app.js
✅ samples/pdfs/              # Sample invoices
✅ tests/                      # Test suite
   ├── test_extractor.py
   └── test_validator.py
✅ ai-notes/                   # AI documentation
   ├── AI_USAGE_LOG.md
   └── PROMPTS_USED.md
✅ VIDEO_RECORDING_GUIDE.md   # Recording instructions
```

---

## Step 6: Final Submission Checklist

- [ ] Repository created and pushed
- [ ] Collaborators added (`deeplogicaitech`, `csvinay`)
- [ ] All code files present
- [ ] README.md complete
- [ ] ai-notes/ folder present
- [ ] Video recorded and link shared
- [ ] Tests pass locally (66 tests)

---

## Common Issues

### Issue: Permission denied
```bash
# Use HTTPS with token or SSH key
git remote set-url origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/YOUR_USERNAME/repo.git
```

### Issue: Branch name mismatch
```bash
# Rename branch to main
git branch -M main
```

### Issue: Large files error
```bash
# If PDFs are too large, ensure they're in .gitignore or use Git LFS
```
