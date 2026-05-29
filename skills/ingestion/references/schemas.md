# Document Processing Schemas

## Step 1 — Classification

Classify the OCR'd document into one of two categories.

### `lab_result`

A structured test result with a parameter table. The key indicator: the document contains a table with columns like `Отк | Показатель | Результат | Ед.изм. | Реф.интервал`.

Examples: blood biochemistry, CBC, urinalysis, serology, lipid panel, hormone panel, coagulation.

### `medical_report`

A clinical document describing a patient encounter or examination. Two sub-forms:

- **Form-based** (e.g. medical certificate Форма №075/у): contains a checklist of specialist examinations, each with findings and a conclusion. Structured, not narrative.
- **Narrative** (e.g. discharge summary, consultation): prose description of patient history, findings, and recommendations.

---

## Step 2 — Extraction Format

Return ONLY valid JSON. The structure depends on classification.

### 2A: Lab Result

```json
{
  "classification": {
    "category": "lab_result",
    "subtype": "urinalysis"
  },
  "patient": {
    "full_name": "Жанабаев Рустам Истаевич",
    "iin": "030713551059",
    "birth_date": "13.07.2003",
    "sex": "Мужской"
  },
  "lab_meta": {
    "lab_name": "UMC Medical Center",
    "material": "Моча",
    "collection_date": "01.02.2023",
    "lab_ids": ["10285046"]
  },
  "lab_results": [
    {
      "section": "Физико-химические свойства мочи",
      "Показатель": "pH(реакция мочи)",
      "value": "6.00",
      "unit": "",
      "reference_range": "5.00 - 7.00",
      "is_abnormal": false,
      "source_text": "pH(реакция мочи) | 6.00 | (5.00 - 7.00)"
    },
    {
      "section": "Микроскопия мочи",
      "Показатель": "бактерии",
      "value": "0.00",
      "unit": "в п/эр",
      "reference_range": "0.00",
      "is_abnormal": false,
      "source_text": "бактерии | 0.00 | в п/эр | (0.00)"
    }
  ],
  "extraction_stats": {
    "sections_found": 2,
    "parameters_total": 26,
    "parameters_extracted": 26
  }
}
```

### 2B: Medical Report

```json
{
  "classification": {
    "category": "medical_report",
    "subtype": "medical_certificate"
  },
  "patient": {
    "full_name": "Жанабаев Рустам Истаевич",
    "iin": "030713551059",
    "birth_date": "13.07.2003",
    "sex": "Мужской"
  },
  "report_meta": {
    "report_type": "medical_certificate_form075",
    "issue_date": "09.01.2026",
    "issuing_facility": "UMC University Medical Center",
    "issuing_doctor": "Капарова А.И."
  },
  "specialist_examinations": [
    {
      "specialist": "Офтальмолог",
      "date": "12.01.2026",
      "findings": "Фоновая ангиопатия сосудов сетчатки? Рек-но осмотр глазного дна при полной циклоплегии",
      "conclusion": "Необходимо До обследование",
      "is_healthy": false
    },
    {
      "specialist": "Невропатолог",
      "date": "12.01.2026",
      "doctor": "Даутова Асем Муратовна",
      "findings": null,
      "conclusion": "Здоров",
      "is_healthy": true
    }
  ],
  "diagnostic_tests": {
    "microreaction": "13.01.2026 — отрицательно",
    "oak": "13.01.2026 — б/о",
    "oam": "13.01.2026 — б/о"
  },
  "extraction_stats": {
    "sections_found": 2,
    "specialists_extracted": 5
  }
}
```

---

## Extraction Rules

1. **`value` is always TEXT** in lab results. Numeric values stay as strings. Qualitative results (отрицательно, не обнаружено, желтый, полная, < 1.00) stay verbatim — never convert or guess.

2. **`is_abnormal`** — use the `Отк` column from the original table. This is the lab's own abnormality flag (e.g., `!` = abnormal). If the `Отк` column is absent from the document or empty for a row, leave `is_abnormal: null`. Never compute this yourself.

3. **`section`** — lab reports group parameters into named sections (e.g., "Серология", "Физико-химические свойства мочи", "Микроскопия мочи"). Preserve these — they provide context for what the Показатель means.

4. **Every row MUST have `source_text`** — a verbatim snippet from the OCR proving the value exists. Minimum: `"parameter_name | value"`. Without this, the extraction is invalid.

5. **Medical certificates** — the `specialist_examinations` array captures each specialist's section. The `diagnostic_tests` object captures summarized lab/instrumental results. Fields that don't exist in the document are `null`, never invented.

6. **Never fabricate** — reference ranges, patient names, diagnosis codes, and unit values must come from the document. If absent, `null`.

7. **Unit is often empty** for qualitative parameters. In the source data, `Ед.изм.` may be blank for rows like "белок (качественный)" or "нитриты". Preserve the emptiness — don't invent a unit.

---

## Step 3 — Database Schema (Local SQLite)

Four tables. Initialize with `python scripts/init_db.py`.

### `ingested_documents` — one row per processed file

| Column | Type | Purpose |
|--------|------|---------|
| id | TEXT PK | UUID |
| source_type | TEXT | telegram, whatsapp, manual |
| category | TEXT | lab_result or medical_report |
| original_filename | TEXT | |
| mime_type | TEXT | |
| ocr_raw_markdown | TEXT | Verbatim Mistral OCR output |
| created_at | TEXT | Auto-set |

### `patient_info` — patient identity

| Column | Type | Purpose |
|--------|------|---------|
| document_id | TEXT PK FK | One patient record per document |
| iin | TEXT | Individual Identification Number |
| full_name | TEXT | |
| birth_date | TEXT | |
| sex | TEXT | |

### `lab_results` — EAV: one row per measured parameter

| Column | Type | Purpose |
|--------|------|---------|
| id | TEXT PK | UUID |
| document_id | TEXT FK → ingested_documents.id | |
| material | TEXT | Венозная кровь, Моча |
| collection_date | TEXT | When the sample was taken |
| lab_name | TEXT | |
| section | TEXT | Серология, Физико-химические свойства мочи |
| Показатель | TEXT NOT NULL | The parameter name |
| value | TEXT | Always text — numeric or qualitative |
| unit | TEXT | May be empty for qualitative results |
| reference_range | TEXT | "5.00 - 7.00", "(отрицательный)" |
| is_abnormal | INTEGER | From the lab's own Отк flag (1/0/NULL) |
| source_text | TEXT | Original OCR snippet for audit |
| created_at | TEXT | Auto-set |

### `medical_reports` — examination forms and narrative reports

| Column | Type | Purpose |
|--------|------|---------|
| id | TEXT PK | UUID |
| document_id | TEXT FK → ingested_documents.id | |
| report_type | TEXT | medical_certificate_form075, discharge_summary... |
| issue_date | TEXT | |
| issuing_facility | TEXT | |
| issuing_doctor | TEXT | |
| conclusion | TEXT | Overall conclusion (Годен / specific finding) |
| specialist_examinations | TEXT | JSON array of specialist consultation objects |
| diagnostic_tests | TEXT | JSON object of summarized test results |
| created_at | TEXT | Auto-set |
