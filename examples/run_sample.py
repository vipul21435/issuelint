"""Run every check on the bundled sample records and print the flagged tasks with evidence.

Usage: uv run python examples/run_sample.py
"""

from __future__ import annotations

from pathlib import Path

from issuelint.checks import run_all
from issuelint.records import load_records
from issuelint.report import explain, summary, to_markdown

records = load_records(Path(__file__).with_name("sample.jsonl"))
reports = run_all(records)
for report in reports:
    if report.flags:
        print(explain(report))
        print()
print(summary(reports, examples=2))
print()
print(to_markdown(reports, examples=2))
