from __future__ import annotations

import json
import logging
import quopri
import re
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin
from urllib.request import urlopen

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency fallback
    BeautifulSoup = None

from models import ApiMeta, ParameterMeta, RequestBodyMeta, ResponseMeta
from utils.io_utils import write_json

LOGGER = logging.getLogger(__name__)


class SwaggerParser:
    def __init__(self, mhtml_path: Path, output_path: Path) -> None:
        self.mhtml_path = mhtml_path
        self.output_path = output_path

    def parse(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        html_parts, json_parts = self._extract_mhtml_parts()

        openapi = self._find_openapi_in_json_parts(json_parts)
        if not openapi:
            openapi = self._find_openapi_in_html_parts(html_parts)
        if not openapi:
            openapi = self._fetch_openapi_from_mhtml_hint()

        if not openapi:
            LOGGER.warning("No embedded OpenAPI JSON found. Falling back to HTML metadata extraction.")
            apis = self._extract_from_html_only(html_parts)
            write_json(self.output_path, apis)
            return {}, apis

        apis = self._extract_apis_from_openapi(openapi)
        write_json(self.output_path, apis)
        return openapi, apis

    def _fetch_openapi_from_mhtml_hint(self) -> Dict[str, Any]:
        text = self.mhtml_path.read_text(encoding="utf-8", errors="ignore")
        snapshot_match = re.search(r"Snapshot-Content-Location:\s*([^\r\n]+)", text, flags=re.IGNORECASE)
        base_url = snapshot_match.group(1).strip() if snapshot_match else ""

        doc_match = re.search(r"id=3D\"download-url-input\"\s+value=3D\"([^\"]+)\"", text)
        if not doc_match:
            doc_match = re.search(r"id=\"download-url-input\"\s+value=\"([^\"]+)\"", text)
        if not doc_match:
            return {}

        doc_path = doc_match.group(1).strip()
        if not base_url:
            return {}

        openapi_url = urljoin(base_url, doc_path)
        try:
            with urlopen(openapi_url, timeout=10) as response:
                raw = response.read().decode("utf-8", errors="ignore")
                payload = self._safe_json_load(raw)
                if self._looks_like_openapi(payload):
                    LOGGER.info("OpenAPI JSON fetched from Swagger URL hint: %s", openapi_url)
                    return payload
        except Exception as exc:
            LOGGER.warning("Failed to fetch OpenAPI from %s: %s", openapi_url, exc)

        return {}

    def _extract_mhtml_parts(self) -> Tuple[List[str], List[str]]:
        raw = self.mhtml_path.read_bytes()
        message = BytesParser(policy=policy.default).parsebytes(raw)

        html_parts: List[str] = []
        json_parts: List[str] = []

        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type().lower()
                payload_bytes = part.get_payload(decode=True)
                if payload_bytes is None:
                    continue

                transfer_encoding = (part.get("Content-Transfer-Encoding") or "").lower()
                if "quoted-printable" in transfer_encoding:
                    payload_bytes = quopri.decodestring(payload_bytes)

                payload = payload_bytes.decode(part.get_content_charset() or "utf-8", errors="ignore")

                if "json" in content_type:
                    json_parts.append(payload)
                elif "html" in content_type:
                    html_parts.append(payload)
                else:
                    if payload.strip().startswith("{") and "openapi" in payload:
                        json_parts.append(payload)
        else:
            body = raw.decode("utf-8", errors="ignore")
            html_parts.append(body)

        return html_parts, json_parts

    def _find_openapi_in_json_parts(self, json_parts: List[str]) -> Dict[str, Any]:
        for candidate in json_parts:
            obj = self._safe_json_load(candidate)
            if self._looks_like_openapi(obj):
                LOGGER.info("OpenAPI JSON found in MHTML JSON part.")
                return obj
        return {}

    def _find_openapi_in_html_parts(self, html_parts: List[str]) -> Dict[str, Any]:
        for html in html_parts:
            from_script = self._extract_json_from_script(html)
            if from_script:
                return from_script
        return {}

    def _extract_json_from_script(self, html: str) -> Dict[str, Any]:
        patterns = [
            r"swaggerDoc\s*[:=]\s*(\{.*?\})\s*[;,]",
            r"spec\s*[:=]\s*(\{.*?\})\s*[;,]",
            r"window\.ui\s*=\s*SwaggerUIBundle\(\s*(\{.*\})\s*\)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, html, flags=re.DOTALL):
                candidate = match.group(1)
                obj = self._safe_json_load(candidate)
                if self._looks_like_openapi(obj):
                    LOGGER.info("OpenAPI JSON found in embedded script.")
                    return obj
        return {}

    def _extract_from_html_only(self, html_parts: List[str]) -> List[Dict[str, Any]]:
        apis: List[Dict[str, Any]] = []
        for html in html_parts:
            if BeautifulSoup is not None:
                soup = BeautifulSoup(html, "lxml")
                blocks = soup.select("div.opblock")
                for block in blocks:
                    method_node = block.select_one("span.opblock-summary-method")
                    path_node = block.select_one("span.opblock-summary-path")
                    if not method_node or not path_node:
                        continue
                    apis.append(
                        ApiMeta(
                            endpoint=path_node.text.strip(),
                            method=method_node.text.strip().upper(),
                            operation_id=self._build_operation_id(method_node.text.strip(), path_node.text.strip()),
                            responses=[],
                        ).to_dict()
                    )
            else:
                for method, path in re.findall(r"\b(GET|POST|PUT|PATCH|DELETE)\b\s*([^\s\"'<>]+/[^\s\"'<>]+)", html, flags=re.IGNORECASE):
                    clean_method = method.upper()
                    clean_path = path.split("?")[0]
                    if not clean_path.startswith("/"):
                        continue
                    apis.append(
                        ApiMeta(
                            endpoint=clean_path,
                            method=clean_method,
                            operation_id=self._build_operation_id(clean_method, clean_path),
                            responses=[],
                        ).to_dict()
                    )

        unique: Dict[str, Dict[str, Any]] = {}
        for item in apis:
            unique[f"{item['method']}:{item['endpoint']}"] = item
        return list(unique.values())

    def _extract_apis_from_openapi(self, openapi: Dict[str, Any]) -> List[Dict[str, Any]]:
        paths = openapi.get("paths", {})
        apis: List[Dict[str, Any]] = []

        for endpoint, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue

                parameters = operation.get("parameters", [])
                headers: List[ParameterMeta] = []
                query_params: List[ParameterMeta] = []
                path_params: List[ParameterMeta] = []

                for param in parameters:
                    if not isinstance(param, dict):
                        continue
                    meta = ParameterMeta(
                        name=param.get("name", "unknown"),
                        location=param.get("in", "query"),
                        required=param.get("required", False),
                        schema=param.get("schema", {}),
                    )
                    if meta.location == "header":
                        headers.append(meta)
                    elif meta.location == "query":
                        query_params.append(meta)
                    elif meta.location == "path":
                        path_params.append(meta)

                request_body = self._extract_request_body(operation)
                responses = self._extract_responses(operation)

                api_meta = ApiMeta(
                    endpoint=endpoint,
                    method=method.upper(),
                    operation_id=operation.get("operationId") or self._build_operation_id(method, endpoint),
                    summary=operation.get("summary", ""),
                    tags=operation.get("tags", []),
                    headers=headers,
                    query_params=query_params,
                    path_params=path_params,
                    request_body=request_body,
                    responses=responses,
                )
                apis.append(api_meta.to_dict())
        return apis

    def _extract_request_body(self, operation: Dict[str, Any]) -> RequestBodyMeta | None:
        body = operation.get("requestBody")
        if not isinstance(body, dict):
            return None

        content = body.get("content", {})
        if not isinstance(content, dict) or not content:
            return None

        if "application/json" in content:
            media = content["application/json"]
            content_type = "application/json"
        else:
            content_type, media = next(iter(content.items()))

        return RequestBodyMeta(
            required=body.get("required", False),
            content_type=content_type,
            schema=media.get("schema", {}),
        )

    def _extract_responses(self, operation: Dict[str, Any]) -> List[ResponseMeta]:
        extracted: List[ResponseMeta] = []
        responses = operation.get("responses", {})
        for status_code, response in responses.items():
            content = response.get("content", {}) if isinstance(response, dict) else {}
            if isinstance(content, dict) and content:
                if "application/json" in content:
                    content_type = "application/json"
                    schema = content["application/json"].get("schema", {})
                else:
                    content_type, media = next(iter(content.items()))
                    schema = media.get("schema", {}) if isinstance(media, dict) else {}
            else:
                content_type = "application/json"
                schema = {}

            extracted.append(
                ResponseMeta(
                    status_code=str(status_code),
                    content_type=content_type,
                    schema=schema,
                )
            )
        return extracted

    @staticmethod
    def _safe_json_load(raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except Exception:
            return {}

    @staticmethod
    def _looks_like_openapi(obj: Dict[str, Any]) -> bool:
        return bool(obj) and isinstance(obj, dict) and ("openapi" in obj or "swagger" in obj) and "paths" in obj

    @staticmethod
    def _build_operation_id(method: str, endpoint: str) -> str:
        cleaned = endpoint.strip("/").replace("/", "_").replace("{", "").replace("}", "")
        return f"{method.lower()}_{cleaned or 'root'}"
