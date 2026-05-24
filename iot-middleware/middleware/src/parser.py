"""Utilities for converting incoming middleware messages to Python/JSON objects.

Supported conversions required by issue #2:
- CSV -> JSON-compatible list of dictionaries
- Text -> JSON-compatible object
- Binary -> Python object with metadata/content
"""

from __future__ import annotations

import base64
import csv
import io
import json
from typing import Any, Dict, List, Union

Payload = Union[str, bytes, bytearray]


class ParserError(ValueError):
    """Raised when a payload cannot be converted using the requested format."""


def _ensure_bytes(payload: Payload) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, bytearray):
        return bytes(payload)
    if isinstance(payload, str):
        return payload.encode("utf-8")
    raise ParserError(f"Unsupported payload type: {type(payload).__name__}")


def _ensure_text(payload: Payload) -> str:
    if isinstance(payload, str):
        return payload

    data = _ensure_bytes(payload)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParserError("Payload is not valid UTF-8 text.") from exc


def _coerce_value(value: str) -> Any:
    """Convert CSV string values to simple JSON values when it is safe."""
    cleaned = value.strip()

    if cleaned == "":
        return ""

    lower = cleaned.lower()
    if lower == "null":
        return None
    if lower == "true":
        return True
    if lower == "false":
        return False

    try:
        return int(cleaned)
    except ValueError:
        pass

    try:
        return float(cleaned)
    except ValueError:
        return cleaned


def csv_to_json(payload: Payload, delimiter: str = ",") -> List[Dict[str, Any]]:
    """Convert CSV content with a header row to a JSON-compatible list of dicts."""
    text = _ensure_text(payload).strip()

    if not text:
        return []

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ParserError("CSV payload must contain a header row.")

    rows: List[Dict[str, Any]] = []
    for row in reader:
        rows.append({key: _coerce_value(value or "") for key, value in row.items() if key is not None})

    return rows


def text_to_json(payload: Payload) -> Dict[str, Any]:
    """Convert plain text to a JSON-compatible object."""
    text = _ensure_text(payload)
    lines = text.splitlines()

    return {
        "content": text,
        "lines": lines,
        "line_count": len(lines),
        "word_count": len(text.split()),
    }


def json_to_object(payload: Payload) -> Any:
    """Convert a JSON payload to a Python object."""
    text = _ensure_text(payload).strip()
    if not text:
        raise ParserError("JSON payload cannot be empty.")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParserError(f"Invalid JSON payload: {exc.msg}") from exc


def binary_to_object(payload: Payload) -> Dict[str, Any]:
    """Convert binary data to a safe Python object representation.

    If the binary content is UTF-8 JSON, it returns the decoded object.
    If it is UTF-8 text, it returns a text object.
    Otherwise, it returns base64/hex metadata so the data can still be serialized.
    """
    data = _ensure_bytes(payload)

    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError:
        return {
            "encoding": "raw-bytes",
            "size_bytes": len(data),
            "base64": base64.b64encode(data).decode("ascii"),
            "hex": data.hex(),
        }

    stripped = decoded.strip()
    if stripped:
        try:
            return {
                "encoding": "utf-8-json",
                "size_bytes": len(data),
                "object": json.loads(stripped),
            }
        except json.JSONDecodeError:
            pass

    return {
        "encoding": "utf-8-text",
        "size_bytes": len(data),
        "object": text_to_json(decoded),
    }


def detect_payload_type(payload: Payload) -> str:
    """Best-effort detection for auto parsing."""
    data = _ensure_bytes(payload)

    try:
        text = data.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        return "binary"

    if not text:
        return "text"

    if text[0] in "[{":
        try:
            json.loads(text)
            return "json"
        except json.JSONDecodeError:
            pass

    first_line = text.splitlines()[0] if text.splitlines() else ""
    if "," in first_line and len(text.splitlines()) >= 2:
        return "csv"

    return "text"


def parse_message(payload: Payload, input_type: str = "auto") -> Dict[str, Any]:
    """Parse a message according to a format and return a JSON-compatible envelope.

    Accepted formats: auto, csv, text, json, binary.
    """
    normalized_type = input_type.lower().strip()
    if normalized_type == "auto":
        normalized_type = detect_payload_type(payload)

    if normalized_type == "csv":
        data: Any = csv_to_json(payload)
    elif normalized_type == "text":
        data = text_to_json(payload)
    elif normalized_type == "json":
        data = json_to_object(payload)
    elif normalized_type == "binary":
        data = binary_to_object(payload)
    else:
        raise ParserError(
            "Unsupported input type. Use one of: auto, csv, text, json, binary."
        )

    return {
        "format": normalized_type,
        "data": data,
    }


def to_json_string(value: Any, indent: int = 2) -> str:
    """Serialize any parsed value to a readable JSON string."""
    return json.dumps(value, ensure_ascii=False, indent=indent)