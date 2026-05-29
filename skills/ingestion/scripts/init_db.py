#!/usr/bin/env python3
"""
Initialize local SQLite database for the ingestion pipeline.

Usage:
    python scripts/init_db.py [--db-path data/ingestion.db]

Creates four tables: ingested_documents, patient_info, lab_results, medical_reports.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


DDL = """
CREATE TABLE IF NOT EXISTS ingested_documents (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL DEFAULT 'manual',
    category TEXT NOT NULL,
    original_filename TEXT,
    mime_type TEXT,
    ocr_raw_markdown TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS patient_info (
    document_id TEXT PRIMARY KEY REFERENCES ingested_documents(id),
    iin TEXT,
    full_name TEXT,
    birth_date TEXT,
    sex TEXT
);

CREATE TABLE IF NOT EXISTS lab_results (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES ingested_documents(id),
    material TEXT,
    collection_date TEXT,
    lab_name TEXT,
    section TEXT,
    "Показатель" TEXT NOT NULL,
    value TEXT,
    unit TEXT,
    reference_range TEXT,
    is_abnormal INTEGER,
    source_text TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medical_reports (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES ingested_documents(id),
    report_type TEXT,
    issue_date TEXT,
    issuing_facility TEXT,
    issuing_doctor TEXT,
    conclusion TEXT,
    specialist_examinations TEXT,
    diagnostic_tests TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_lab_document ON lab_results(document_id);
CREATE INDEX IF NOT EXISTS idx_lab_section ON lab_results(section);
CREATE INDEX IF NOT EXISTS idx_lab_parameter ON lab_results("Показатель");
CREATE INDEX IF NOT EXISTS idx_lab_material ON lab_results(material);
CREATE INDEX IF NOT EXISTS idx_report_document ON medical_reports(document_id);
CREATE INDEX IF NOT EXISTS idx_report_type ON medical_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_patient_iin ON patient_info(iin);
"""


def init_db(db_path: str = "data/ingestion.db") -> str:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(DDL)
        conn.commit()
    finally:
        conn.close()
    return str(path.resolve())


def main():
    db_path = "data/ingestion.db"
    for i, arg in enumerate(sys.argv[1:], start=1):
        if arg == "--db-path" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            break

    resolved = init_db(db_path)
    print(json.dumps({"success": True, "db_path": resolved}))


if __name__ == "__main__":
    main()
