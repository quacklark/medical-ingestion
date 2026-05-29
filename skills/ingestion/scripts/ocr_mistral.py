#!/usr/bin/env python3
"""
Mistral OCR — send a PDF or image URL to Mistral OCR API, return markdown.

Usage:
    python scripts/ocr_mistral.py <file_path_or_url> [--model mistral-ocr-latest]

Authentication: Reads MISTRAL_API_KEY from environment.
Output: JSON with {success, pages, markdown, html_tables, usage_info}
"""
from __future__ import annotations

import json
import os
import sys
import base64
import mimetypes
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"
DEFAULT_MODEL = "mistral-ocr-latest"


def _is_url(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")


def _file_to_base64(file_path: str) -> tuple[str, str]:
    """Read a local file and return (base64_data_url, mime_type)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{data}", mime_type


def run_ocr(source: str, model: str = DEFAULT_MODEL) -> dict:
    """
    Call Mistral OCR API.

    Args:
        source: URL (https://...) or local file path.
        model: Mistral OCR model ID.

    Returns:
        Dict with success, pages array, concatenated markdown, html_tables, usage_info.
    """
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return {"success": False, "error": "MISTRAL_API_KEY not set in environment"}

    if _is_url(source):
        # File is already accessible via URL
        document = {"type": "document_url", "document_url": source}
    else:
        # Local file — base64 encode
        data_url, mime = _file_to_base64(source)
        if mime.startswith("image/"):
            document = {"type": "image_url", "image_url": data_url}
        else:
            document = {"type": "document_url", "document_url": data_url}

    body = json.dumps({
        "model": model,
        "document": document,
        "include_image_base64": False,
    }).encode("utf-8")

    req = Request(
        MISTRAL_OCR_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: request failed"}
    except URLError as e:
        return {"success": False, "error": f"Connection failed: {e.reason}"}

    pages = result.get("pages", [])
    markdown_parts = []

    for page in pages:
        md = page.get("markdown", "")
        markdown_parts.append(md)

    full_markdown = "\n\n--- PAGE BREAK ---\n\n".join(markdown_parts)

    return {
        "success": True,
        "model": model,
        "pages_count": len(pages),
        "pages": pages,
        "markdown": full_markdown,
        "usage_info": result.get("usage_info", {}),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Usage: ocr_mistral.py <file_path_or_url> [--model model_id]"}, ensure_ascii=False))
        sys.exit(1)

    source = sys.argv[1]
    model = DEFAULT_MODEL

    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            break

    result = run_ocr(source, model)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
