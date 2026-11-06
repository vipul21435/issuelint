"""Run every check on the bundled sample records and print the flagged tasks with evidence.

    uv run python examples/run_sample.py
"""

from __future__ import annotations

from pathlib import Path

from issuelint.checks import run_all
from issuelint.records import load_records
from issuelint.report import explain, summary

records = load_records(Path(__file__).with_name("sample.jsonl"))
reports = run_all(records)
for report in reports:
    if report.flags:
        print(explain(report))
        print()
print(summary(reports))
