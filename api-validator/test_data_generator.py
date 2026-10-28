from __future__ import annotations

import copy
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from utils.io_utils import ensure_dir, write_json
from utils.schema_utils import generate_sample_from_schema

LOGGER = logging.getLogger(__name__)


class TestDataGenerator:
    def __init__(self, output_dir: Path, openapi: Dict[str, Any]) -> None:
        self.output_dir = output_dir
        self.openapi = openapi

    def generate(self, apis: List[Dict[str, Any]]) -> List[Path]:
        ensure_dir(self.output_dir)
        files: List[Path] = []

        for api in apis:
            request_schema = ((api.get("request_body") or {}).get("schema")) or {}
            positive = generate_sample_from_schema(request_schema, self.openapi) if request_schema else {}
            negative = self._build_negative(positive)
            boundary = self._build_boundary(positive)

            payload = {
                "endpoint": api["endpoint"],
                "method": api["method"],
                "operation_id": api["operation_id"],
                "positive": positive,
                "negative": negative,
                "boundary": boundary,
            }

            path = self.output_dir / f"{self._safe_name(api['operation_id'])}.json"
            write_json(path, payload)
            files.append(path)

        LOGGER.info("Generated %s test-data files.", len(files))
        return files

    def _build_negative(self, payload: Any) -> Any:
        data = copy.deepcopy(payload)
        if isinstance(data, dict) and data:
            first_key = next(iter(data.keys()))
            del data[first_key]
            return data
        if isinstance(data, list):
            return []
        if isinstance(data, str):
            return 123
        if isinstance(data, (int, float)):
            return "invalid"
        return None

    def _build_boundary(self, payload: Any) -> Any:
        data = copy.deepcopy(payload)
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = value[:1]
                elif isinstance(value, int):
                    data[key] = 0
                elif isinstance(value, float):
                    data[key] = 0.0
                elif isinstance(value, list):
                    data[key] = value[:1]
            return data
        if isinstance(data, list):
            return data[:1]
        return data

    @staticmethod
    def _safe_name(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", name)
