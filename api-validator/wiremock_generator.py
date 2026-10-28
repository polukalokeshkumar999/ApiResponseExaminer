from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from utils.io_utils import ensure_dir, write_json
from utils.schema_utils import generate_sample_from_schema

LOGGER = logging.getLogger(__name__)


class WireMockGenerator:
    def __init__(self, output_dir: Path, openapi: Dict[str, Any]) -> None:
        self.output_dir = output_dir
        self.mappings_dir = output_dir / "mappings"
        self.files_dir = output_dir / "__files__"
        self.openapi = openapi

    def generate_wiremock_stubs(self, apis: List[Dict[str, Any]]) -> List[Path]:
        ensure_dir(self.mappings_dir)
        ensure_dir(self.files_dir)

        generated: List[Path] = []
        for api in apis:
            mapping, response_payload = self._build_mapping(api)
            name = self._safe_name(api["operation_id"])

            response_file = self.files_dir / f"{name}-response.json"
            mapping_file = self.mappings_dir / f"{name}-mapping.json"

            write_json(response_file, response_payload)
            write_json(mapping_file, mapping)
            generated.append(mapping_file)

        LOGGER.info("Generated %s WireMock mappings.", len(generated))
        return generated

    def _build_mapping(self, api: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        method = api["method"].upper()
        endpoint = api["endpoint"]

        url_pattern = re.sub(r"\{[^/]+\}", "[^/]+", endpoint)
        request_section: Dict[str, Any] = {
            "method": method,
            "urlPathPattern": f"^{url_pattern}$",
        }

        if api.get("query_params"):
            request_section["queryParameters"] = {
                item["name"]: {"matches": ".*"}
                for item in api["query_params"]
            }

        if api.get("headers"):
            request_section["headers"] = {
                item["name"]: {"matches": ".+"}
                for item in api["headers"]
            }

        request_body_schema = ((api.get("request_body") or {}).get("schema")) or {}
        if method in {"POST", "PUT", "PATCH"} and request_body_schema:
            sample_request = generate_sample_from_schema(request_body_schema, self.openapi)
            request_section["bodyPatterns"] = [{"equalToJson": sample_request, "ignoreArrayOrder": True, "ignoreExtraElements": True}]

        response_meta = self._pick_response_meta(api)
        response_schema = response_meta.get("schema", {})
        response_payload = generate_sample_from_schema(response_schema, self.openapi)

        mapping = {
            "name": api["operation_id"],
            "request": request_section,
            "response": {
                "status": int(response_meta.get("status_code", "200")) if str(response_meta.get("status_code", "200")).isdigit() else 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": response_payload,
            },
        }
        return mapping, response_payload

    @staticmethod
    def _pick_response_meta(api: Dict[str, Any]) -> Dict[str, Any]:
        responses = api.get("responses", [])
        preferred = ["200", "201", "202", "204", "default"]
        for code in preferred:
            for item in responses:
                if item.get("status_code") == code:
                    return item
        return responses[0] if responses else {"status_code": "200", "schema": {"type": "object"}}

    @staticmethod
    def _safe_name(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", name)
