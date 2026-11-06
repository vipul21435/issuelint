"""Task records and their loaders.

A task record is an issue text, the gold patch that fixes it and the test patch
that detects the fix. Two input layouts are accepted:

* plain JSONL with the keys ``id``, ``issue``, ``patch``, ``test_patch``;
* the SWE-bench layout with ``instance_id``, ``problem_statement``, ``patch``,
  ``test_patch``.

Both layouts may be mixed line by line. Missing ``test_patch`` is treated as an
empty patch.
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


@dataclass(frozen=True)
class TaskRecord:
    """One issue-to-fix task."""

    id: str
    issue: str
    patch: str
    test_patch: str = ""


class RecordError(ValueError):
    """Raised when a row cannot be read as a task record."""


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value)
    return None


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


def load_records(path: str | Path) -> list[TaskRecord]:
    """Pick the loader from the file suffix (``.jsonl`` or ``.json``)."""
    suffix = Path(path).suffix.lower()
    if suffix == ".jsonl":
        return load_jsonl(path)
    if suffix == ".json":
        return load_json(path)
    raise RecordError(f"unsupported input {path}: expected a .jsonl or .json file")
