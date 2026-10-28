from pathlib import Path

from response_comparator import ResponseComparator
from utils.io_utils import write_json


def test_comparator_ignores_dynamic_fields(tmp_path: Path):
    baseline = tmp_path / "baseline"
    actual = tmp_path / "actual"
    baseline.mkdir(parents=True, exist_ok=True)
    actual.mkdir(parents=True, exist_ok=True)

    write_json(
        baseline / "get_customer.json",
        {
            "status_code": 200,
            "response_headers": {"Content-Type": "application/json"},
            "response_body": {"id": 1, "timestamp": "2026-01-01T00:00:00Z"},
        },
    )
    write_json(
        actual / "get_customer.json",
        {
            "status_code": 200,
            "response_headers": {"Content-Type": "application/json"},
            "response_body": {"id": 1, "timestamp": "2026-02-01T00:00:00Z"},
        },
    )

    apis = [{"endpoint": "/customer/1", "method": "GET", "operation_id": "get_customer"}]
    comparator = ResponseComparator(baseline, actual, ["timestamp"], tmp_path / "comparison.json")
    results = comparator.compare_all(apis)

    assert results[0]["result"] == "PASS"
