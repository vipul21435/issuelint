"""Smoke tests for the example scripts on small fixtures built here."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

PATCH = (
    "--- a/pkg/conv.py\n+++ b/pkg/conv.py\n@@ -1,2 +1,3 @@ def to_celsius(value, unit):\n"
    '+    if unit == "K":\n+        return value - 273.15\n'
)
TEST_PATCH = (
    "--- a/tests/test_conv.py\n+++ b/tests/test_conv.py\n@@ -1 +1,2 @@\n"
    "+def test_kelvin():\n+    assert to_celsius(273.15, 'K') == 0\n"
)


def _rows(n: int) -> list[dict[str, str]]:
    rows = []
    for i in range(n):
        leaky = i % 2 == 0
        issue = (
            'to_celsius ignores kelvin. Fix:\n```\nif unit == "K":\n    return value - 273.15\n```'
            if leaky
            else "conversion looks wrong"
        )
        rows.append(
            {
                "instance_id": f"org__pkg-{i}",
                "problem_statement": issue,
                "hints_text": "see https://example.org/t" if i % 3 == 0 else "",
                "patch": PATCH,
                "test_patch": TEST_PATCH,
            }
        )
    return rows


def test_run_sample(capsys):
    runpy.run_path(str(EXAMPLES / "run_sample.py"), run_name="__main__")
    out = capsys.readouterr().out
    assert "FLAG solution_leakage" in out
    assert "| `solution_leakage` |" in out


def test_swebench_analysis_on_a_small_directory(tmp_path: Path, monkeypatch):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    rows = _rows(12)
    (tmp_path / "full").mkdir()
    pq.write_table(pa.Table.from_pylist(rows), tmp_path / "full" / "test.parquet")
    (tmp_path / "swebench_plus").mkdir()
    (tmp_path / "swebench_plus" / "data.json").write_text(json.dumps(rows[:4]), encoding="utf-8")
    labels = tmp_path / "annotations" / "results"
    labels.mkdir(parents=True)
    lines = ["instance_id,underspecified,false_negative"]
    lines += [f"org__pkg-{i},{0 if i % 2 == 0 else 3},{i % 4}" for i in range(12)]
    (labels / "ensembled_annotations_public.csv").write_text("\n".join(lines), encoding="utf-8")
    out = tmp_path / "results.md"
    argv = ["swebench_analysis.py", str(tmp_path), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    runpy.run_path(str(EXAMPLES / "swebench_analysis.py"), run_name="__main__")
    text = out.read_text(encoding="utf-8")
    assert "| check | SWE-bench test | SWE-Bench+ |" in text
    assert "| `solution_leakage` | 6 (50.0 %) | 2 (50.0 %) |" in text
    assert "Label `underspecified >= 2`: 12 annotated tasks, 6 positive" in text
    assert "| `underspecification` | 1.000" in text
