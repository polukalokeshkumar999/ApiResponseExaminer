from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any, Dict, List

from jsonschema import Draft7Validator, ValidationError

from utils.io_utils import read_json, write_json
from utils.schema_utils import resolve_ref

LOGGER = logging.getLogger(__name__)


class SchemaValidatorEngine:
    def __init__(self, openapi: Dict[str, Any], baseline_dir: Path, actual_dir: Path, output_path: Path) -> None:
        self.openapi = openapi
        self.baseline_dir = baseline_dir
        self.actual_dir = actual_dir
        self.output_path = output_path

    def validate_all(self, apis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for api in apis:
            response_schema = self._pick_schema(api)
            if not response_schema:
                results.append(self._build_result(api, "legacy", "SKIP", "No schema found"))
                results.append(self._build_result(api, "new", "SKIP", "No schema found"))
                continue

            resolved_schema = resolve_ref(response_schema, self.openapi)
            safe_name = self._safe_name(api["operation_id"])
            legacy_data = self._load_response_body(self.baseline_dir / f"{safe_name}.json")
            new_data = self._load_response_body(self.actual_dir / f"{safe_name}.json")

            results.append(self._validate_payload(api, "legacy", legacy_data, resolved_schema))
            results.append(self._validate_payload(api, "new", new_data, resolved_schema))

        write_json(self.output_path, results)
        LOGGER.info("Schema validation completed with %s records.", len(results))
        return results

    def _validate_payload(self, api: Dict[str, Any], environment: str, payload: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        try:
            Draft7Validator(schema).validate(payload)
            return self._build_result(api, environment, "PASS", "Schema valid")
        except ValidationError as err:
            return self._build_result(api, environment, "FAIL", err.message)
        except Exception as exc:
            return self._build_result(api, environment, "FAIL", str(exc))

    @staticmethod
    def _load_response_body(path: Path) -> Any:
        if not path.exists():
            return {}
        payload = read_json(path)
        return payload.get("response_body", {})

    @staticmethod
    def _pick_schema(api: Dict[str, Any]) -> Dict[str, Any]:
        responses = api.get("responses", [])
        preference = ["200", "201", "202", "204", "default"]
        for code in preference:
            for item in responses:
                if item.get("status_code") == code:
                    return item.get("schema", {})
        return responses[0].get("schema", {}) if responses else {}

    @staticmethod
    def _build_result(api: Dict[str, Any], environment: str, status: str, message: str) -> Dict[str, Any]:
        return {
            "endpoint": api["endpoint"],
            "method": api["method"],
            "operation_id": api["operation_id"],
            "environment": environment,
            "status": status,
            "message": message,
        }

    @staticmethod
    def _safe_name(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", name)
