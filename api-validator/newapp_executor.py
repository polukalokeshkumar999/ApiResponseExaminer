from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from legacy_executor import LegacyExecutor


class NewAppExecutor(LegacyExecutor):
    def __init__(self, base_url: str, config: Dict[str, Any], output_dir: Path, openapi: Dict[str, Any]) -> None:
        super().__init__(base_url=base_url, config=config, output_dir=output_dir, openapi=openapi)

    def execute_all(self, apis: List[Dict[str, Any]]):
        return super().execute_all(apis)
