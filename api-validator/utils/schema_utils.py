from __future__ import annotations

import copy
from typing import Any, Dict


def resolve_ref(schema: Dict[str, Any], openapi: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(schema, dict):
        return {}

    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return {}
        node: Any = openapi
        for token in ref[2:].split("/"):
            node = node.get(token, {}) if isinstance(node, dict) else {}
        return resolve_ref(copy.deepcopy(node), openapi)

    resolved = copy.deepcopy(schema)
    if "properties" in resolved:
        for key, child in list(resolved["properties"].items()):
            resolved["properties"][key] = resolve_ref(child, openapi)

    if "items" in resolved:
        resolved["items"] = resolve_ref(resolved["items"], openapi)

    if "allOf" in resolved:
        merged: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for part in resolved["allOf"]:
            sub = resolve_ref(part, openapi)
            merged["properties"].update(sub.get("properties", {}))
            merged["required"] = sorted(set(merged["required"] + sub.get("required", [])))
        return merged

    return resolved


def generate_sample_from_schema(schema: Dict[str, Any], openapi: Dict[str, Any] | None = None) -> Any:
    if not schema:
        return {}

    if "$ref" in schema and openapi:
        schema = resolve_ref(schema, openapi)

    schema_type = schema.get("type")

    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]

    if schema_type == "object" or "properties" in schema:
        result = {}
        for prop, prop_schema in schema.get("properties", {}).items():
            result[prop] = generate_sample_from_schema(prop_schema, openapi)
        return result

    if schema_type == "array":
        return [generate_sample_from_schema(schema.get("items", {}), openapi)]

    if schema_type == "string":
        if schema.get("format") == "date-time":
            return "2026-01-01T00:00:00Z"
        if schema.get("format") == "date":
            return "2026-01-01"
        if schema.get("format") == "uuid":
            return "11111111-1111-1111-1111-111111111111"
        min_len = schema.get("minLength", 1)
        return "x" * max(min_len, 1)

    if schema_type == "integer":
        minimum = schema.get("minimum", 1)
        maximum = schema.get("maximum", minimum + 10)
        return int(min(maximum, max(minimum, 1)))

    if schema_type == "number":
        minimum = schema.get("minimum", 1.0)
        return float(minimum)

    if schema_type == "boolean":
        return True

    return "sample"


def strip_ignored_fields(payload: Any, ignored_fields: set[str]) -> Any:
    if isinstance(payload, dict):
        cleaned = {}
        for key, value in payload.items():
            if key in ignored_fields:
                continue
            cleaned[key] = strip_ignored_fields(value, ignored_fields)
        return cleaned

    if isinstance(payload, list):
        return [strip_ignored_fields(item, ignored_fields) for item in payload]

    return payload
