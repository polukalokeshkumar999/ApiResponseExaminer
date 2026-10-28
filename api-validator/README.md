# Enterprise Python API Validation Framework

Production-grade API validation framework to compare Legacy and New applications using Swagger/OpenAPI as the contract and WireMock for mock environment generation.

## Features
- Swagger UI MHTML parsing with embedded OpenAPI extraction.
- Fallback HTML endpoint parsing when JSON is absent.
- Automated WireMock mapping and response generation.
- Positive/negative/boundary test-data generation.
- Legacy baseline and New app execution capture.
- Deep response comparison with configurable ignored fields.
- Schema contract validation using JSON Schema.
- Multi-format reporting: JSON, HTML, XLSX.
- Pytest and Allure integration support.
- Agent-style orchestrator from a single command.

## Project Structure
- main.py
- config.yaml
- swagger_parser.py
- wiremock_generator.py
- test_data_generator.py
- legacy_executor.py
- newapp_executor.py
- response_comparator.py
- schema_validator.py
- report_generator.py
- models.py
- requirements.txt
- run.bat
- architecture.md
- setup_guide.md
- execution_guide.md
- swagger/
- generated/
- baseline/
- actual/
- reports/
- wiremock/mappings/
- wiremock/__files__/
- test-data/
- tests/

## Quick Start
1. Configure base URLs and auth in config.yaml.
2. Keep Swagger UI .mhtml path in config.yaml.
3. Run:
   - python main.py --config config.yaml
4. Open reports/comparison_report.html.

## Dependency Install via whl Folder
If internet access to public PyPI is blocked, install using local wheel files.

1. Create/download wheels into whl:
   - build_whl_bundle.bat
2. Install from local wheels only:
   - install_from_whl.bat

If wheel download is blocked by corporate policy, use your approved internal PyPI mirror or copy wheel files from a machine that can access the packages.

## WireMock
If wiremock standalone jar is at C:\wiremock, start with:
- java -jar C:\wiremock\wiremock-standalone.jar --port 9090 --root-dir wiremock

## Allure
- pytest -q tests --alluredir reports/allure-results
- allure serve reports/allure-results
