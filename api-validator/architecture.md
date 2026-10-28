# API Validation Framework Architecture

## Objective
Compare Legacy vs New API behavior using Swagger/OpenAPI contract, with WireMock stubs for controlled test environments.

## Core Flow
1. SwaggerParser reads Swagger UI MHTML and extracts OpenAPI metadata.
2. Endpoint metadata is persisted into generated/apis.json.
3. WireMockGenerator creates mappings and sample bodies.
4. TestDataGenerator creates positive/negative/boundary payloads.
5. LegacyExecutor captures baseline responses.
6. NewAppExecutor captures actual responses.
7. ResponseComparator computes diffs (DeepDiff) with ignore rules.
8. SchemaValidator validates payloads against contract.
9. ReportGenerator emits JSON, HTML, and Excel outputs.

## Design Principles
- SOLID module boundaries with single-purpose classes.
- Open for extension through isolated classes and config-driven workflow flags.
- Dependency inversion by passing config/openapi objects into modules.
- Structured logging and fault-tolerant execution records.

## Folder Contracts
- generated/: parsed OpenAPI and endpoint catalog.
- wiremock/: mappings and sample response files.
- test-data/: request payload scenarios.
- baseline/: legacy execution artifacts.
- actual/: new app execution artifacts.
- reports/: comparison and schema validation outputs.
