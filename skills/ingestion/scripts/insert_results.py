#!/usr/bin/env python3
"""
Insert extracted medical data into the local SQLite database.

Usage:
    python scripts/insert_results.py <extraction_json_file> [--db-path data/ingestion.db]

Reads the extraction JSON (as produced by the subagent following schemas.md),
inserts into all relevant tables in a single transaction.

Output: JSON with {success, document_id, rows_inserted} or {success: false, error: ...}
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from pathlib import Path


def _bool_to_int(value):
    """Convert JSON boolean/null to SQLite INTEGER: true→1, false→0, null→NULL."""
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def insert_results(json_path: str, db_path: str = "data/ingestion.db") -> dict:
    path = Path(json_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {json_path}"}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc_id = str(uuid.uuid4())
    classification = data.get("classification", {})
    category = classification.get("category", "unknown")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        # ── 1. ingested_documents ──────────────────────────────────────────
        conn.execute(
            """INSERT INTO ingested_documents (id, source_type, category, original_filename, mime_type, ocr_raw_markdown)
               VALUES (?, 'manual', ?, ?, ?, ?)""",
            (
                doc_id,
                category,
                data.get("original_filename"),
                data.get("mime_type"),
                data.get("ocr_raw_markdown"),
            ),
        )

        # ── 2. patient_info ────────────────────────────────────────────────
        patient = data.get("patient") or {}
        if patient:
            conn.execute(
                """INSERT INTO patient_info (document_id, iin, full_name, birth_date, sex)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    doc_id,
                    patient.get("iin"),
                    patient.get("full_name"),
                    patient.get("birth_date"),
                    patient.get("sex"),
                ),
            )

        rows_inserted = 0

        # ── 3. lab_results ─────────────────────────────────────────────────
        if category == "lab_result":
            lab_meta = data.get("lab_meta") or {}
            lab_results = data.get("lab_results") or []

            for row in lab_results:
                result_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO lab_results
                       (id, document_id, material, collection_date, lab_name,
                        section, "Показатель", value, unit, reference_range,
                        is_abnormal, source_text)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result_id,
                        doc_id,
                        lab_meta.get("material"),
                        lab_meta.get("collection_date"),
                        lab_meta.get("lab_name"),
                        row.get("section"),
                        row.get("Показатель"),
                        row.get("value"),
                        row.get("unit"),
                        row.get("reference_range"),
                        _bool_to_int(row.get("is_abnormal")),
                        row.get("source_text"),
                    ),
                )
                rows_inserted += 1

        # ── 4. medical_reports ─────────────────────────────────────────────
        elif category == "medical_report":
            report_meta = data.get("report_meta") or {}
            report_id = str(uuid.uuid4())

            conn.execute(
                """INSERT INTO medical_reports
                   (id, document_id, report_type, issue_date, issuing_facility,
                    issuing_doctor, conclusion, specialist_examinations, diagnostic_tests)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report_id,
                    doc_id,
                    report_meta.get("report_type"),
                    report_meta.get("issue_date"),
                    report_meta.get("issuing_facility"),
                    report_meta.get("issuing_doctor"),
                    data.get("conclusion"),
                    json.dumps(data.get("specialist_examinations"), ensure_ascii=False) if data.get("specialist_examinations") else None,
                    json.dumps(data.get("diagnostic_tests"), ensure_ascii=False) if data.get("diagnostic_tests") else None,
                ),
            )
            rows_inserted = 1

        conn.commit()

        stats = data.get("extraction_stats", {})
        return {
            "success": True,
            "document_id": doc_id,
            "category": category,
            "rows_inserted": rows_inserted,
            "extraction_stats": stats,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}

    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Usage: insert_results.py <extraction_json_file> [--db-path data/ingestion.db]"}, ensure_ascii=False))
        sys.exit(1)

    json_path = sys.argv[1]
    db_path = "data/ingestion.db"

    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--db-path" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            break

    result = insert_results(json_path, db_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
