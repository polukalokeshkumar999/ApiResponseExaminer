from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

from utils.io_utils import ensure_dir, write_json
from utils.schema_utils import generate_sample_from_schema

LOGGER = logging.getLogger(__name__)


class LegacyExecutor:
    def __init__(self, base_url: str, config: Dict[str, Any], output_dir: Path, openapi: Dict[str, Any]) -> None:
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.output_dir = output_dir
        self.openapi = openapi
        self.session = requests.Session()

    def execute_all(self, apis: List[Dict[str, Any]]) -> List[Path]:
        ensure_dir(self.output_dir)
        records: List[Path] = []
        for api in apis:
            record = self._execute_single(api)
            output_file = self.output_dir / f"{self._safe_name(api['operation_id'])}.json"
            write_json(output_file, record)
            records.append(output_file)
        LOGGER.info("Legacy execution completed for %s endpoints.", len(records))
        return records

    def _execute_single(self, api: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = self._resolve_path_params(api["endpoint"], api.get("path_params", []))
        url = f"{self.base_url}{endpoint}"
        query = self._build_query(api.get("query_params", []))
        headers = self._build_headers(api.get("headers", []))
        method = api["method"].upper()

        request_body = None
        if method in {"POST", "PUT", "PATCH"}:
            request_schema = ((api.get("request_body") or {}).get("schema")) or {}
            request_body = generate_sample_from_schema(request_schema, self.openapi)

        start = time.perf_counter()
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=query,
                json=request_body,
                headers=headers,
                timeout=self.config.get("timeout", 30),
                verify=self.config.get("verify_ssl", False),
            )
            response_time_ms = int((time.perf_counter() - start) * 1000)
            body = self._safe_response_body(response)
            return {
                "endpoint": api["endpoint"],
                "method": method,
                "operation_id": api["operation_id"],
                "request_url": url,
                "request_query_params": query,
                "request_headers": headers,
                "request_body": request_body,
                "status_code": response.status_code,
                "response_headers": dict(response.headers),
                "response_body": body,
                "response_time_ms": response_time_ms,
            }
        except Exception as exc:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            LOGGER.exception("Legacy call failed for %s %s", method, url)
            return {
                "endpoint": api["endpoint"],
                "method": method,
                "operation_id": api["operation_id"],
                "request_url": url,
                "request_query_params": query,
                "request_headers": headers,
                "request_body": request_body,
                "status_code": 0,
                "response_headers": {},
                "response_body": {"error": str(exc)},
                "response_time_ms": response_time_ms,
            }

    def _build_headers(self, endpoint_headers: List[Dict[str, Any]]) -> Dict[str, str]:
        headers = {k: str(v) for k, v in (self.config.get("custom_headers") or {}).items()}

        auth_type = (self.config.get("auth_type") or "none").lower()
        if auth_type == "bearer" and self.config.get("bearer_token"):
            headers["Authorization"] = f"Bearer {self.config['bearer_token']}"
        elif auth_type == "apikey":
            api_key = self.config.get("api_key") or {}
            if api_key.get("header_name") and api_key.get("value"):
                headers[api_key["header_name"]] = api_key["value"]

        for header in endpoint_headers:
            name = header.get("name")
            if name and name not in headers:
                headers[name] = "sample"

        headers.setdefault("Content-Type", "application/json")
        return headers

    @staticmethod
    def _build_query(query_params: List[Dict[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for item in query_params:
            schema = item.get("schema", {})
            if schema.get("type") == "integer":
                result[item["name"]] = 1
            elif schema.get("type") == "boolean":
                result[item["name"]] = True
            else:
                result[item["name"]] = "sample"
        return result

    @staticmethod
    def _resolve_path_params(endpoint: str, path_params: List[Dict[str, Any]]) -> str:
        result = endpoint
        for item in path_params:
            placeholder = "{" + item.get("name", "") + "}"
            if placeholder in result:
                schema = item.get("schema", {})
                value = "1" if schema.get("type") in {"integer", "number"} else "sample"
                result = result.replace(placeholder, str(value))
        result = re.sub(r"\{[^/]+\}", "sample", result)
        return result

    @staticmethod
    def _safe_response_body(response: requests.Response) -> Any:
        try:
            return response.json()
        except Exception:
            text = response.text
            try:
                return json.loads(text)
            except Exception:
                return text

    @staticmethod
    def _safe_name(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", name)
