# Medical Document Ingestion Skill for Hermes Agent

A Hermes Agent skill that ingests medical documents (PDF, images) via Mistral AI OCR, classifies content, extracts structured data, and stores it in a local SQLite database.

## Pipeline

```
Attachment → Mistral OCR → Classify → Extract → SQLite
```

## Install

```bash
hermes skills tap add quacklark/medical-ingestion
hermes skills install quacklark/medical-ingestion/ingestion
```

Hermes will prompt for `MISTRAL_API_KEY` on first use.

To reduce approval prompts, add the ingestion scripts to your allowlist once:

```bash
hermes config set command_allowlist '["scripts/ocr_mistral.py", "scripts/init_db.py", "scripts/insert_results.py"]'
hermes config set delegation.subagent_auto_approve true
```

## Structure

```
skills/ingestion/
├── SKILL.md                    # Agent instructions
├── scripts/
│   ├── ocr_mistral.py          # Mistral OCR API → markdown
│   ├── insert_results.py       # Parameterized SQLite insertion
│   └── init_db.py              # Create tables (once)
├── references/
│   └── schemas.md              # Classification + extraction schemas
└── templates/
    └── extraction_format.json  # JSON template
```

## Supported Documents

- **Lab results**: blood biochemistry, CBC, urinalysis, serology, lipid panel, hormones, coagulation
- **Medical reports**: certificates (Форма №075/у), discharge summaries, examination reports, consultations

## Database Schema

Four tables in `data/ingestion.db`. Initialized with `python scripts/init_db.py`.

### `ingested_documents` — one row per processed file

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| source_type | TEXT | telegram, whatsapp, manual |
| category | TEXT | lab_result or medical_report |
| original_filename | TEXT | |
| mime_type | TEXT | |
| ocr_raw_markdown | TEXT | Verbatim Mistral OCR output |
| created_at | TEXT | Auto-set |

### `patient_info` — patient identity per document

| Column | Type | Description |
|--------|------|-------------|
| document_id | TEXT PK/FK | Links to ingested_documents |
| iin | TEXT | Individual Identification Number |
| full_name | TEXT | |
| birth_date | TEXT | |
| sex | TEXT | |

### `lab_results` — EAV model for test parameters

One row per measured parameter. Extensible — new test types add rows with new Показатель names, no schema changes needed.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| document_id | TEXT FK | Links to ingested_documents |
| material | TEXT | Венозная кровь, Моча |
| collection_date | TEXT | |
| lab_name | TEXT | |
| section | TEXT | Parameter group: Серология, Физико-химические свойства мочи... |
| Показатель | TEXT NOT NULL | Parameter name |
| value | TEXT | Always text — numeric (6.00) or qualitative (отрицательно, не обнаружено) |
| unit | TEXT | May be empty for qualitative results |
| reference_range | TEXT | "5.00 - 7.00", "(отрицательный)" |
| is_abnormal | INTEGER | 1/0/NULL from lab's own flag |
| source_text | TEXT | Verbatim OCR snippet for audit |
| created_at | TEXT | Auto-set |

### `medical_reports` — examination forms and narrative reports

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| document_id | TEXT FK | Links to ingested_documents |
| report_type | TEXT | medical_certificate_form075, discharge_summary... |
| issue_date | TEXT | |
| issuing_facility | TEXT | |
| issuing_doctor | TEXT | |
| conclusion | TEXT | Overall conclusion (Годен / specific finding) |
| specialist_examinations | TEXT | JSON array of specialist consultations |
| diagnostic_tests | TEXT | JSON object of summarized test results |
| created_at | TEXT | Auto-set |

## License

MIT
