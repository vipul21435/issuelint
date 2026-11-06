"""Task records and their loaders.

A task record is an issue text, the gold patch that fixes it and the test patch
that detects the fix. Two input layouts are accepted:

* plain JSONL with the keys ``id``, ``issue``, ``patch``, ``test_patch``;
* the SWE-bench layout with ``instance_id``, ``problem_statement``, ``patch``,
  ``test_patch`` and ``hints_text``.

Both layouts may be mixed line by line. Missing ``test_patch`` is treated as an
empty patch. Files are read as JSONL, JSON, or Parquet (the format the SWE-bench
datasets are published in on Hugging Face; needs the optional ``pyarrow``).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ID_KEYS = ("id", "instance_id", "task_id")
ISSUE_KEYS = ("issue", "problem_statement", "issue_text", "text")
PATCH_KEYS = ("patch", "gold_patch", "fix_patch")
TEST_PATCH_KEYS = ("test_patch", "tests_patch")
HINTS_KEYS = ("hints", "hints_text")
FAIL_TO_PASS_KEYS = ("fail_to_pass", "FAIL_TO_PASS")


@dataclass(frozen=True)
class TaskRecord:
    """One issue-to-fix task."""

    id: str
    issue: str
    patch: str
    test_patch: str = ""
    hints: str = ""
    fail_to_pass: tuple[str, ...] = ()

    def issue_text(self, *, with_hints: bool = False) -> str:
        """The text the checks read: the issue, plus the hints when asked for."""
        if with_hints and self.hints.strip():
            return f"{self.issue}\n\n{self.hints}"
        return self.issue


class RecordError(ValueError):
    """Raised when a row cannot be read as a task record."""


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value)
    return None


def _test_ids(value: Any) -> tuple[str, ...]:
    """A list of test ids, given as a list or as a JSON-encoded list (the SWE-bench form)."""
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RecordError(f"FAIL_TO_PASS is not a JSON list: {exc.msg}") from exc
    if not isinstance(value, list):
        raise RecordError("FAIL_TO_PASS must be a list of test ids")
    return tuple(str(v) for v in value)


def record_from_dict(row: dict[str, Any], default_id: str | None = None) -> TaskRecord:
    """Build a record from a dictionary in either accepted layout."""
    issue = _first(row, ISSUE_KEYS)
    patch = _first(row, PATCH_KEYS)
    if issue is None or patch is None:
        raise RecordError(
            f"row needs an issue ({'/'.join(ISSUE_KEYS)}) and a patch "
            f"({'/'.join(PATCH_KEYS)}); got keys {sorted(row)}"
        )
    task_id = _first(row, ID_KEYS) or default_id
    if task_id is None:
        raise RecordError("row has no id field and no default id was given")
    return TaskRecord(
        id=task_id,
        issue=issue,
        patch=patch,
        test_patch=_first(row, TEST_PATCH_KEYS) or "",
        hints=_first(row, HINTS_KEYS) or "",
        fail_to_pass=_test_ids(next((row[k] for k in FAIL_TO_PASS_KEYS if k in row), None)),
    )


def iter_jsonl(lines: Iterable[str]) -> Iterator[TaskRecord]:
    """Yield records from JSONL lines; blank lines are skipped."""
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RecordError(f"line {number}: not JSON ({exc.msg})") from exc
        if not isinstance(row, dict):
            raise RecordError(f"line {number}: expected an object, got {type(row).__name__}")
        yield record_from_dict(row, default_id=f"row-{number}")


def load_jsonl(path: str | Path) -> list[TaskRecord]:
    """Read every record of a JSONL file."""
    with Path(path).open(encoding="utf-8") as handle:
        return list(iter_jsonl(handle))


def load_json(path: str | Path) -> list[TaskRecord]:
    """Read a JSON file holding one record or a list of records."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else [data]
    return [record_from_dict(row, default_id=f"row-{i}") for i, row in enumerate(rows, start=1)]


def load_parquet(path: str | Path) -> list[TaskRecord]:
    """Read a Parquet file such as a SWE-bench split downloaded from Hugging Face."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RecordError(
            "reading .parquet needs pyarrow: pip install 'issuelint[parquet]'"
        ) from exc
    rows = pq.read_table(Path(path)).to_pylist()
    return [record_from_dict(row, default_id=f"row-{i}") for i, row in enumerate(rows, start=1)]


def load_records(path: str | Path, limit: int | None = None) -> list[TaskRecord]:
    """Pick the loader from the file suffix (``.jsonl``, ``.json`` or ``.parquet``).

    ``limit`` keeps the first records only; ids must be unique across the file.
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".jsonl":
        records = load_jsonl(path)
    elif suffix == ".json":
        records = load_json(path)
    elif suffix == ".parquet":
        records = load_parquet(path)
    else:
        raise RecordError(f"unsupported input {path}: expected .jsonl, .json or .parquet")
    seen: set[str] = set()
    for record in records:
        if record.id in seen:
            raise RecordError(f"duplicate id {record.id!r}")
        seen.add(record.id)
    return records if limit is None else records[:limit]
