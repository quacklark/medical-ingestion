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

## License

MIT
