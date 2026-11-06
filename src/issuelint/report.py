"""Output: a text table, per-task explanations, JSON and CSV."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable

from issuelint.checks import CHECKS, TaskReport

_SHORT = {
    "solution_leakage": "solution",
    "test_leakage": "tests",
    "location_hints": "location",
    "underspecification": "underspec",
    "external_links": "links",
    "scope_gap": "scope",
}


def table(reports: Iterable[TaskReport]) -> str:
    """One row per task; a score followed by ``*`` is a flagged check."""
    rows = list(reports)
    id_width = max([len("id"), *(len(r.id) for r in rows)])
    head = ["id".ljust(id_width), *(_SHORT[c].rjust(10) for c in CHECKS), "  flags"]
    lines = ["".join(head)]
    for r in rows:
        cells = [r.id.ljust(id_width)]
        for c in CHECKS:
            f = r.finding(c)
            mark = "*" if f.flagged else " "
            cells.append(f"{f.score:.2f}{mark}".rjust(10))
        cells.append(f"  {len(r.flags)}")
        lines.append("".join(cells))
    return "\n".join(lines)


def summary(reports: Iterable[TaskReport]) -> str:
    """Share of tasks flagged by each check."""
    rows = list(reports)
    if not rows:
        return "no tasks"
    out = [f"{len(rows)} task(s)"]
    for c in CHECKS:
        n = sum(1 for r in rows if r.finding(c).flagged)
        mean = sum(r.finding(c).score for r in rows) / len(rows)
        out.append(f"  {c:<20} flagged {n:>4} ({100 * n / len(rows):5.1f}%)  mean score {mean:.3f}")
    return "\n".join(out)


def explain(report: TaskReport) -> str:
    lines = [f"{report.id}"]
    for f in report.findings:
        mark = "FLAG" if f.flagged else "    "
        lines.append(f"  {mark} {f.check:<20} {f.score:.2f}  {f.summary}")
        lines.extend(f"         - {e}" for e in f.evidence)
    return "\n".join(lines)


def to_json(reports: Iterable[TaskReport]) -> str:
    return json.dumps([r.as_dict() for r in reports], indent=2)


def to_csv(reports: Iterable[TaskReport]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", *(f"{c}_score" for c in CHECKS), *(f"{c}_flag" for c in CHECKS)])
    for r in reports:
        writer.writerow(
            [
                r.id,
                *(f"{r.finding(c).score:.4f}" for c in CHECKS),
                *(int(r.finding(c).flagged) for c in CHECKS),
            ]
        )
    return buf.getvalue()
