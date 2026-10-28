from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from utils.io_utils import write_json, write_text


class ReportGenerator:
    def __init__(self, reports_dir: Path) -> None:
        self.reports_dir = reports_dir

    def generate(self, comparison_results: List[Dict[str, Any]], schema_results: List[Dict[str, Any]]) -> Dict[str, Path]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        json_path = self.reports_dir / "comparison_report.json"
        html_path = self.reports_dir / "comparison_report.html"
        xlsx_path = self.reports_dir / "comparison_report.xlsx"

        summary = self._summary(comparison_results)
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": summary,
            "comparison_results": comparison_results,
            "schema_results": schema_results,
        }
        write_json(json_path, payload)

        html = self._build_html(summary, comparison_results, schema_results)
        write_text(html_path, html)

        self._build_excel(xlsx_path, comparison_results, schema_results, summary)

        return {"json": json_path, "html": html_path, "xlsx": xlsx_path}

    @staticmethod
    def _summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(results)
        passed = sum(1 for r in results if r.get("result") == "PASS")
        failed = total - passed
        pass_pct = round((passed / total) * 100, 2) if total else 0.0
        fail_pct = round((failed / total) * 100, 2) if total else 0.0
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_percentage": pass_pct,
            "fail_percentage": fail_pct,
            "endpoint_coverage": total,
        }

    def _build_html(self, summary: Dict[str, Any], comparisons: List[Dict[str, Any]], schema_results: List[Dict[str, Any]]) -> str:
        rows = []
        for item in comparisons:
            rows.append(
                "<tr>"
                f"<td>{item['method']}</td>"
                f"<td>{item['endpoint']}</td>"
                f"<td>{item['result']}</td>"
                f"<td><pre>{item.get('differences', {})}</pre></td>"
                "</tr>"
            )

        schema_rows = []
        for row in schema_results:
            schema_rows.append(
                "<tr>"
                f"<td>{row['environment']}</td>"
                f"<td>{row['method']}</td>"
                f"<td>{row['endpoint']}</td>"
                f"<td>{row['status']}</td>"
                f"<td>{row['message']}</td>"
                "</tr>"
            )

        return f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <title>API Comparison Report</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 24px; background: #f5f7fb; color: #132238; }}
    .card {{ background: #ffffff; border-radius: 10px; padding: 16px; margin-bottom: 18px; box-shadow: 0 8px 24px rgba(17, 39, 70, 0.08); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #d7dfeb; padding: 8px; vertical-align: top; }}
    th {{ background: #eaf0fa; text-align: left; }}
    .fail {{ color: #b00020; font-weight: 700; }}
    .pass {{ color: #127a3d; font-weight: 700; }}
    pre {{ white-space: pre-wrap; word-break: break-word; margin: 0; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h2>Summary</h2>
    <p>Total: {summary['total']} | Passed: <span class=\"pass\">{summary['passed']}</span> | Failed: <span class=\"fail\">{summary['failed']}</span></p>
    <p>Pass %: {summary['pass_percentage']} | Fail %: {summary['fail_percentage']} | Endpoint Coverage: {summary['endpoint_coverage']}</p>
  </div>

  <div class=\"card\">
    <h2>Comparison Details</h2>
    <table>
      <thead>
        <tr><th>Method</th><th>Endpoint</th><th>Status</th><th>Differences</th></tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>

  <div class=\"card\">
    <h2>Schema Validation</h2>
    <table>
      <thead>
        <tr><th>Environment</th><th>Method</th><th>Endpoint</th><th>Status</th><th>Message</th></tr>
      </thead>
      <tbody>
        {''.join(schema_rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    def _build_excel(self, xlsx_path: Path, comparison_results: List[Dict[str, Any]], schema_results: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
        comparison_flat = [
            {
                "method": item.get("method"),
                "endpoint": item.get("endpoint"),
                "operation_id": item.get("operation_id"),
                "result": item.get("result"),
                "status_match": item.get("status_match"),
                "header_match": item.get("header_match"),
                "body_match": item.get("body_match"),
                "differences": str(item.get("differences")),
            }
            for item in comparison_results
        ]

        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            pd.DataFrame([summary]).to_excel(writer, sheet_name="summary", index=False)
            pd.DataFrame(comparison_flat).to_excel(writer, sheet_name="comparison", index=False)
            pd.DataFrame(schema_results).to_excel(writer, sheet_name="schema_validation", index=False)
