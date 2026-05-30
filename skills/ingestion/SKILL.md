---
name: ingestion
description: Medical document ingestion pipeline — OCR, classify, extract, store.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [medical, ocr, ingestion, documents, supabase]
    category: research
    related_skills: []
required_environment_variables:
  - name: MISTRAL_API_KEY
    prompt: Mistral API key
    help: Get at https://console.mistral.ai/api-keys
    required_for: OCR processing of PDF and image documents
---

# Ingestion Pipeline

Extracts structured medical data from PDF and image attachments. The pipeline: OCR via Mistral AI → classify → extract fields → store in local SQLite.

## When to Use

- User sends a medical document attachment (PDF, image) in any platform (Telegram, CLI, etc.)
- User asks to "ingest this report" or "process this lab result"
- Batch processing multiple medical files

## Prerequisites

- `MISTRAL_API_KEY` environment variable — sign up at https://console.mistral.ai
- Python 3.11+ (no additional packages needed — stdlib `urllib` and `sqlite3`)
- Local database initialised once: `python scripts/init_db.py`

## Procedure

**CRITICAL: Do NOT run any commands yourself.** Every `terminal`, `read_file`, or `skill_view` call you make triggers an approval prompt. Delegate the ENTIRE pipeline to ONE subagent. You make exactly ONE tool call: `delegate_task`.

### Single document

Do NOT run OCR or read files yourself. Delegate the ENTIRE pipeline to one subagent. This reduces approval prompts from 6 to 1.

```
delegate_task(
  goal: "Run the full ingestion pipeline on FILE_PATH.
         1. Run: python scripts/ocr_mistral.py FILE_PATH > /tmp/ocr_result.json
         2. Read /tmp/ocr_result.json
         3. Load schemas: skill_view('ingestion', 'references/schemas.md')
         4. Classify the document and extract all fields per the schemas
         5. Save the extraction JSON to /tmp/extraction_result.json (use write_file)
         6. Run: python scripts/init_db.py && python scripts/insert_results.py /tmp/extraction_result.json
         7. Return a summary of what was ingested",
  context: "FILE_PATH: <the exact file path>
            SCHEMAS_PATH: ingestion/references/schemas.md
            The database is at <skill_dir>/data/ingestion.db.
            Use --db-path <skill_dir>/data/ingestion.db with scripts.
            Every Показатель MUST include source_text.",
  toolsets: ["terminal", "skills", "file"]
)
```

The subagent returns only the summary. Your reply to the user should be just the summary — not a play-by-play of each step.

### Multiple documents (batch)

When the user sends multiple files, spawn one subagent per file in parallel:

```
delegate_task(
  tasks: [
    { goal: "Full ingestion pipeline for FILE_1", context: "FILE_PATH: FILE_1", toolsets: ["terminal", "skills", "file"] },
    { goal: "Full ingestion pipeline for FILE_2", context: "FILE_PATH: FILE_2", toolsets: ["terminal", "skills", "file"] },
    ...
  ]
)
```

### Database initialisation

Before the first ingestion, initialise the database once:

```
terminal: python scripts/init_db.py
```

This is idempotent — safe to run multiple times.

## Quick Reference

| Script | Purpose |
|--------|---------|
| `scripts/ocr_mistral.py <file>` | Send file to Mistral OCR, return markdown |
| `scripts/insert_results.py <json>` | Insert extraction JSON into SQLite (parameterized) |
| `scripts/init_db.py` | Create SQLite tables (run once, idempotent) |

| Reference | Content |
|-----------|---------|
| `references/schemas.md` | Classification taxonomy, extraction formats, DB schema |

## Pitfalls

- **Approval prompts** — always delegate the full pipeline to a subagent. The subagent runs all commands autonomously. If you run `terminal` or `read_file` yourself, you'll trigger one approval per call.
- **Large PDFs (>10MB)** — the OCR script base64-encodes local files. For very large files, upload to a temporary URL first.
- **Handwriting** — Mistral OCR handles printed text well; handwriting accuracy varies.
- **Qualitative values** — urine and feces tests often use qualitative scales ("отрицательно", "следы", "+++", "не обнаружено"). Store as TEXT, never convert to numeric.
- **Multi-page reports** — the OCR script concatenates all pages. If a single file contains multiple unrelated tests, the subagent should identify each one.
- **Context size** — raw OCR markdown can be 10-50K characters. The subagent handles this in its own context; the main agent never sees it.

## Verification

```bash
# Test OCR on an example PDF
python scripts/ocr_mistral.py /path/to/example.pdf | python -m json.tool | head -80

# Check the database
sqlite3 data/ingestion.db "SELECT category, Показатель, value, unit FROM lab_results LIMIT 20;"
sqlite3 data/ingestion.db "SELECT report_type, conclusion FROM medical_reports LIMIT 20;"
```
