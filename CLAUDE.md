# CLAUDE.md — DKEC 日報產出工具 (Daily Report Generator)

## Project Overview

A Flask-based web application for generating daily order reports from multiple e-commerce platforms. The tool allows users to upload Excel files containing transaction data from three platforms (官網/Official Website, 蝦皮/Shopee, MOMO), processes the data through platform-specific column mappings, and generates formatted HTML reports with order summaries and revenue totals.

**Target users:** E-commerce operations team managing orders across multiple sales channels.

## Repository Structure

```
DK_EC_Daily_report/
├── streamlit_app.py          # Main Flask application (single-file app, ~440 lines)
├── requirements.txt          # Flask-based dependencies (production)
├── requirements_streamlit.txt # Alternative Streamlit dependencies (legacy)
└── CLAUDE.md                 # This file
```

> **Note:** The main file is named `streamlit_app.py` but implements a Flask application. This is a historical naming artifact — the app was migrated from Streamlit to Flask.

## Tech Stack

- **Language:** Python 3 (UTF-8 encoding throughout)
- **Web framework:** Flask (runs on `http://127.0.0.1:5000`)
- **Data processing:** pandas, openpyxl (XLSX), xlrd (legacy XLS)
- **Templating:** Jinja2 (Flask default, used for `index.html`)
- **No database** — session data stored as temporary pickle files in `./uploads/`

## How to Run

```bash
pip install -r requirements.txt
python streamlit_app.py
# Opens at http://127.0.0.1:5000
```

## Architecture

### Single-File Application (`streamlit_app.py`)

The entire backend lives in one file, organized as:

1. **Configuration (lines 23-93):** `PLATFORM_CONFIG` dict defines per-platform settings:
   - `official` — 官網 (Official Website)
   - `shopee` — 蝦皮 (Shopee)
   - `momo` — MOMO
   - Each platform specifies: display name, date column, amount column, source Excel sheet name, output column order, and column mapping (source → output)

2. **Data Processing Functions (lines 96-198):**
   - `parse_date()` — Multi-format date parser, normalizes to `YYYY/MM/DD`
   - `process_official_data()`, `process_shopee_data()`, `process_momo_data()` — Platform-specific column mapping and date handling
   - `read_excel_file()` — Excel reader with openpyxl/xlrd fallback

3. **API Endpoints (lines 201-429):**
   - `GET /` — Serves the HTML frontend via `render_template('index.html')`
   - `POST /api/upload` — Accepts Excel file + platform selection, returns available dates and a session ID
   - `POST /api/generate` — Accepts session ID + selected dates + platform, returns HTML report
   - `DELETE /api/cleanup/<session_id>` — Removes temporary pickle files

4. **Report Generation (lines 349-417):**
   - `generate_html_report()` — Builds an HTML table with platform-specific title, data rows, and a total row

### Data Flow

```
Upload Excel → Read sheet → Map columns → Parse dates → Store as pickle
                                                              ↓
Select dates → Load pickle → Filter by date → Calculate totals → Generate HTML report
```

### Session Management

- Session IDs are timestamp-based (`YYYYMMDDHHMMSSffffff`)
- Processed data stored as pickle files in `./uploads/`
- Max upload size: 16MB
- No automatic cleanup — relies on explicit `DELETE /api/cleanup/<session_id>` calls

## Key Conventions

### Language

- **Code:** Python identifiers in English (snake_case functions, UPPER_CASE constants)
- **UI/Data:** All column names, labels, and user-facing strings are in Traditional Chinese (繁體中文)
- **Comments:** Mixed Chinese and English

### Platform Configuration Pattern

Each platform in `PLATFORM_CONFIG` follows the same structure:
```python
'platform_key': {
    'name': '顯示名稱',           # Display name (Chinese)
    'date_column': '...',         # Date column name in output schema
    'amount_column': '...',       # Revenue column name in output schema
    'source_sheet': '...',        # Expected Excel sheet name
    'output_columns': [...],      # Ordered list of output columns
    'column_mapping': {           # source_col → output_col
        '原始欄位名': '輸出欄位名',
    }
}
```

When adding a new platform, follow this exact pattern and add a corresponding `process_<platform>_data()` function.

### Date Handling

- All dates are normalized to `YYYY/MM/DD` format via `parse_date()`
- The parser tries multiple formats in sequence, then falls back to `pd.to_datetime()`
- Report titles use short date format `MM/DD`

### Error Responses

API errors return JSON with an `'error'` key and appropriate HTTP status codes (400, 500). Messages are in Chinese.

## Development Notes

- **No tests exist.** When adding tests, use `pytest` and consider testing the data processing functions (`process_*_data`, `parse_date`) as they are pure transformations.
- **No CI/CD pipeline.** No `.github/workflows` or similar.
- **No `.gitignore`.** Consider adding one to exclude `uploads/`, `__pycache__/`, `*.pkl`, and `.env`.
- **No frontend template** is committed — `render_template('index.html')` expects a `templates/index.html` file that may need to be created or is served from elsewhere.
- The `requirements_streamlit.txt` file is a legacy artifact from before the Flask migration.

## Common Tasks

### Adding a New E-Commerce Platform

1. Add a new entry to `PLATFORM_CONFIG` in `streamlit_app.py` following the existing pattern
2. Create a `process_<platform>_data(df)` function that maps columns and parses dates
3. Add the platform's branch to the `if/elif/else` chain in `upload_file()` (line 248)
4. The frontend will also need updating to include the new platform option

### Modifying Column Mappings

Update the `column_mapping` dict in the relevant platform's `PLATFORM_CONFIG` entry. Source column names must match the Excel file headers exactly.

### Changing Report Format

Modify `generate_html_report()` — it builds raw HTML strings (no template engine). The report structure is: title → table with header → data rows → total row.
