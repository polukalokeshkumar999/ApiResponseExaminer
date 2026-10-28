from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any, Dict, List

from deepdiff import DeepDiff

from utils.io_utils import read_json, write_json
from utils.schema_utils import strip_ignored_fields

LOGGER = logging.getLogger(__name__)


class ResponseComparator:
    def __init__(self, baseline_dir: Path, actual_dir: Path, ignored_fields: List[str], report_json_path: Path) -> None:
        self.baseline_dir = baseline_dir
        self.actual_dir = actual_dir
        self.ignored_fields = set(ignored_fields)
        self.report_json_path = report_json_path

    def compare_all(self, apis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for api in apis:
            op_id = api["operation_id"]
            safe_name = self._safe_name(op_id)
            baseline_file = self.baseline_dir / f"{safe_name}.json"
            actual_file = self.actual_dir / f"{safe_name}.json"

            if not baseline_file.exists() or not actual_file.exists():
                results.append(
                    {
                        "endpoint": api["endpoint"],
                        "method": api["method"],
                        "operation_id": op_id,
                        "result": "FAIL",
                        "status_match": False,
                        "header_match": False,
                        "body_match": False,
                        "differences": {"error": "Missing baseline or actual file"},
                    }
                )
                continue

            baseline = read_json(baseline_file)
            actual = read_json(actual_file)

            status_match = baseline.get("status_code") == actual.get("status_code")
            header_diff = self._compare_headers(baseline.get("response_headers", {}), actual.get("response_headers", {}))

            baseline_body = strip_ignored_fields(baseline.get("response_body"), self.ignored_fields)
            actual_body = strip_ignored_fields(actual.get("response_body"), self.ignored_fields)
            body_diff = DeepDiff(baseline_body, actual_body, ignore_order=True).to_dict()

            body_match = not body_diff
            header_match = not header_diff
            result = "PASS" if status_match and header_match and body_match else "FAIL"

            results.append(
                {
                    "endpoint": api["endpoint"],
                    "method": api["method"],
                    "operation_id": op_id,
                    "result": result,
                    "status_match": status_match,
                    "header_match": header_match,
                    "body_match": body_match,
                    "differences": {
                        "status": {
                            "legacy": baseline.get("status_code"),
                            "new": actual.get("status_code"),
                        } if not status_match else {},
                        "headers": header_diff,
                        "body": body_diff,
                    },
                }
            )

        write_json(self.report_json_path, results)
        LOGGER.info("Comparison completed for %s endpoints.", len(results))
        return results

    @staticmethod
    def _compare_headers(legacy_headers: Dict[str, Any], new_headers: Dict[str, Any]) -> Dict[str, Any]:
        ignore = {"date", "server", "content-length", "connection", "keep-alive", "transfer-encoding"}

        norm_legacy = {k.lower(): v for k, v in legacy_headers.items() if k.lower() not in ignore}
        norm_new = {k.lower(): v for k, v in new_headers.items() if k.lower() not in ignore}

        diff = DeepDiff(norm_legacy, norm_new, ignore_order=True).to_dict()
        return diff

    @staticmethod
    def _safe_name(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", name)
