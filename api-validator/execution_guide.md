# Execution Guide

## Full Workflow Run
- python main.py --config config.yaml

## Workflow Steps Executed
1. Parse Swagger MHTML -> generated/apis.json
2. Generate WireMock mappings -> wiremock/mappings + wiremock/__files__
3. Generate test payloads -> test-data/
4. Execute legacy API calls -> baseline/
5. Execute new app API calls -> actual/
6. Compare baseline vs actual -> reports/comparison_differences_only.json
7. Validate schema -> reports/schema_validation.json
8. Generate reports -> reports/comparison_report.{json,html,xlsx}

## Pytest + Allure
- pytest -q tests --alluredir reports/allure-results
- allure serve reports/allure-results
