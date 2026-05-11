# factura-processor

Automation that **reads PDF invoices from Gmail** and exports them to **Google Sheets**, using xAI (Grok) for structured data extraction.

## Flow

```
Gmail (PDF attachment)
    │
    ▼
pypdfium2 — extracts text locally (no API cost)
    │
    ▼
xAI (Grok) — parses the text into structured JSON
    │
    ▼
Google Sheets — single batchUpdate call
<img width="1438" height="487" alt="image" src="https://github.com/user-attachments/assets/913c0766-b5f0-41e6-ab9e-2c5be55b24d7" />

    │
    ▼
Email marked as processed (label applied + UNREAD removed)
```

## Extracted fields

| Field              | Type    | Description                          |
|--------------------|---------|--------------------------------------|
| `numero_factura`   | string  | Invoice number / series              |
| `fecha_factura`    | string  | Issue date (YYYY-MM-DD)              |
| `emisor`           | string  | Supplier name                        |
| `nif_cif`          | string  | Tax ID of the issuer                 |
| `importe_neto`     | float   | Net amount (taxable base)            |
| `iva`              | float   | VAT amount                           |
| `total`            | float   | Grand total                          |
| `fecha_vencimiento`| string  | Due date (YYYY-MM-DD)                |
| `descripcion`      | string  | Short summary of the invoice         |
| `clave_unica`      | string  | `numero_factura + "\|" + emisor`     |
| `fecha_procesado`  | string  | Date the email was processed         |

---

## Requirements

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — package manager
- A **Google** account with Gmail and Google Sheets
- An **xAI** account with an API key

---

## Installation

### 1. Install uv (if you don't have it)

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install project dependencies

```bash
cd factura-processor
uv sync
```

---

## Google OAuth setup

### Step 1: Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `factura-processor`)
3. Enable the required APIs:
   - **Gmail API** → search "Gmail API" → Enable
   - **Google Sheets API** → search "Google Sheets API" → Enable

### Step 2: Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. If you're asked to configure the consent screen:
   - User Type: **External**
   - Fill in an app name (e.g. `factura-processor`)
   - Add your own email as a test user
4. Application type: **Desktop app**
5. Download the JSON and save it as `credentials/credentials.json`

### Step 3: First run (authorisation)

The first run opens your browser automatically. Authorise access to Gmail and Sheets — the resulting token is saved to `credentials/token.json` so subsequent runs are non-interactive.

---

## Google Sheet setup

1. Create a new spreadsheet at [sheets.google.com](https://sheets.google.com)
2. Copy the **ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
   ```
3. The first run writes the header row automatically.

---

## Environment configuration

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your values:

```env
XAI_API_KEY=xai-...
SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms

# Optional: tweak the email search
GMAIL_QUERY=has:attachment filename:pdf is:unread

# Optional: change the Grok model
AI_MODEL=grok-3-latest
```

---

## Running it

```bash
# Standard run
uv run main.py

# Verbose logging
LOG_LEVEL=DEBUG uv run main.py
```

---

## Project layout

```
factura-processor/
├── main.py                              # Entry point (uv run main.py)
├── pyproject.toml                       # Project config and dependencies
├── .env                                 # Environment variables (do NOT commit)
├── .env.example                         # Configuration template
├── .gitignore
├── credentials/
│   ├── credentials.json                 # OAuth client secrets (do NOT commit)
│   └── token.json                       # Access token (auto-generated)
└── src/
    └── factura_processor/
        ├── __init__.py
        ├── __main__.py                  # python -m factura_processor
        ├── main.py                      # Pipeline orchestrator
        ├── config/
        │   ├── __init__.py
        │   └── settings.py              # pydantic-settings config
        ├── models/
        │   ├── __init__.py
        │   └── factura.py               # Pydantic Factura model
        ├── utils/
        │   ├── __init__.py
        │   └── google_auth.py           # Shared OAuth helper (Gmail + Sheets)
        ├── tools/
        │   ├── __init__.py
        │   └── pdf_extractor.py         # Local PDF text extraction (pypdfium2)
        └── clients/
            ├── __init__.py
            ├── gmail/
            │   ├── __init__.py
            │   ├── client.py            # Gmail search + attachment download
            │   └── messages.py          # Email / Attachment dataclasses
            ├── claude/
            │   ├── __init__.py
            │   ├── client.py            # xAI (Grok) call → structured JSON
            │   └── prompts.py           # System prompt
            └── sheets/
                ├── __init__.py
                └── client.py            # Google Sheets sync
```

---

## Optimisations

| Optimisation | Detail |
|---|---|
| **Local extraction** | `pypdfium2` reads the text on-device, no API call required |
| **Structured outputs** | `response_format=json_object` guarantees valid JSON, no post-processing |
| **Single batchUpdate** | Every invoice is flushed to Sheets in one API call |
| **Unique key** | `numero_factura\|emisor` lets us upsert existing rows without duplicates |
