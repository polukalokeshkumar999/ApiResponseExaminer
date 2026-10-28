from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict

from legacy_executor import LegacyExecutor
from newapp_executor import NewAppExecutor
from report_generator import ReportGenerator
from response_comparator import ResponseComparator
from schema_validator import SchemaValidatorEngine
from swagger_parser import SwaggerParser
from test_data_generator import TestDataGenerator
from utils.io_utils import ensure_dir, load_yaml, write_json
from utils.logging_utils import configure_logging
from wiremock_generator import WireMockGenerator

LOGGER = logging.getLogger(__name__)


class ApiValidationAgent:
    def __init__(self, base_dir: Path, config: Dict[str, Any]) -> None:
        self.base_dir = base_dir
        self.config = config

        self.generated_dir = base_dir / "generated"
        self.wiremock_dir = base_dir / "wiremock"
        self.test_data_dir = base_dir / "test-data"
        self.baseline_dir = base_dir / "baseline"
        self.actual_dir = base_dir / "actual"
        self.reports_dir = base_dir / "reports"

        for folder in [
            self.generated_dir,
            self.wiremock_dir,
            self.test_data_dir,
            self.baseline_dir,
            self.actual_dir,
            self.reports_dir,
        ]:
            ensure_dir(folder)

    def run(self) -> None:
        swagger_path = Path(self.config["swagger_mhtml_path"]).resolve()
        apis_path = self.generated_dir / "apis.json"
        openapi_path = self.generated_dir / "openapi_extracted.json"

        LOGGER.info("Step 1: Parsing Swagger MHTML from %s", swagger_path)
        parser = SwaggerParser(swagger_path, apis_path)
        openapi, apis = parser.parse()
        if openapi:
            write_json(openapi_path, openapi)

        LOGGER.info("Discovered %s API operations.", len(apis))

        if self.config.get("run_wiremock_generation", True):
            LOGGER.info("Step 2: Generating WireMock mappings")
            WireMockGenerator(self.wiremock_dir, openapi).generate_wiremock_stubs(apis)

        if self.config.get("run_test_data_generation", True):
            LOGGER.info("Step 3: Generating test data")
            TestDataGenerator(self.test_data_dir, openapi).generate(apis)

        if self.config.get("run_legacy_capture", True):
            LOGGER.info("Step 4: Capturing legacy responses")
            LegacyExecutor(
                base_url=self.config["legacy_base_url"],
                config=self.config,
                output_dir=self.baseline_dir,
                openapi=openapi,
            ).execute_all(apis)

        if self.config.get("run_newapp_capture", True):
            LOGGER.info("Step 5: Capturing new app responses")
            NewAppExecutor(
                base_url=self.config["new_base_url"],
                config=self.config,
                output_dir=self.actual_dir,
                openapi=openapi,
            ).execute_all(apis)

        comparison_results = []
        if self.config.get("run_comparison", True):
            LOGGER.info("Step 6: Comparing responses")
            comparison_results = ResponseComparator(
                baseline_dir=self.baseline_dir,
                actual_dir=self.actual_dir,
                ignored_fields=self.config.get("ignored_fields", []),
                report_json_path=self.reports_dir / "comparison_differences_only.json",
            ).compare_all(apis)

        schema_results = []
        if self.config.get("run_schema_validation", True):
            LOGGER.info("Step 7: Running schema validation")
            schema_results = SchemaValidatorEngine(
                openapi=openapi,
                baseline_dir=self.baseline_dir,
                actual_dir=self.actual_dir,
                output_path=self.reports_dir / "schema_validation.json",
            ).validate_all(apis)

        LOGGER.info("Step 8: Building reports")
        report_paths = ReportGenerator(self.reports_dir).generate(comparison_results, schema_results)
        LOGGER.info("Report generated: %s", report_paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enterprise API Validation Framework")
    parser.add_argument("--config", default="config.yaml", help="Path to config yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    config_path = (base_dir / args.config).resolve()
    config = load_yaml(config_path)

    log_path = base_dir / "reports" / "run.log"
    configure_logging(log_path)

    # Resolve relative swagger path against framework directory.
    swagger_path = Path(config.get("swagger_mhtml_path", ""))
    if not swagger_path.is_absolute():
        config["swagger_mhtml_path"] = str((base_dir / swagger_path).resolve())

    agent = ApiValidationAgent(base_dir=base_dir, config=config)
    agent.run()


if __name__ == "__main__":
    main()
