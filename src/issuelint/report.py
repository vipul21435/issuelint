"""Output: a text table, per-task explanations, JSON and CSV."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from dataclasses import dataclass

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


@dataclass(frozen=True)
class CheckStats:
    """How often one check fired across a set of tasks."""

    check: str
    tasks: int
    flagged: int
    nonzero: int
    mean_score: float
    examples: list[str]

    @property
    def flagged_share(self) -> float:
        return self.flagged / self.tasks if self.tasks else 0.0

    @property
    def nonzero_share(self) -> float:
        return self.nonzero / self.tasks if self.tasks else 0.0


def check_stats(reports: Iterable[TaskReport], examples: int = 3) -> list[CheckStats]:
    """Per check: tasks flagged, tasks with a score above 0, mean score, example ids.

    Examples are the highest-scoring tasks, flagged ones first; ties keep input order.
    For ``location_hints``, which never flags, examples are the highest scores.
    """
    rows = list(reports)
    out = []
    for c in CHECKS:
        found = [(r.id, r.finding(c)) for r in rows]
        ranked = sorted(found, key=lambda item: (not item[1].flagged, -item[1].score))
        picks = [i for i, f in ranked if f.score > 0 and (f.flagged or c == "location_hints")]
        out.append(
            CheckStats(
                check=c,
                tasks=len(rows),
                flagged=sum(1 for _, f in found if f.flagged),
                nonzero=sum(1 for _, f in found if f.score > 0),
                mean_score=sum(f.score for _, f in found) / len(rows) if rows else 0.0,
                examples=picks[:examples],
            )
        )
    return out


def summary(reports: Iterable[TaskReport], examples: int = 0) -> str:
    """Share of tasks flagged by each check, optionally with example ids."""
    rows = list(reports)
    if not rows:
        return "no tasks"
    out = [f"{len(rows)} task(s)"]
    for st in check_stats(rows, examples):
        out.append(
            f"  {st.check:<20} flagged {st.flagged:>4} ({100 * st.flagged_share:5.1f}%)"
            f"  nonzero {st.nonzero:>4} ({100 * st.nonzero_share:5.1f}%)"
            f"  mean score {st.mean_score:.3f}"
        )
        if st.examples:
            out.append(f"  {'':<20} e.g. {', '.join(st.examples)}")
    return "\n".join(out)


def to_markdown(reports: Iterable[TaskReport], examples: int = 3) -> str:
    """A Markdown table of the per-check shares with example ids."""
    rows = list(reports)
    lines = [
        f"{len(rows)} tasks.",
        "",
        "| check | flagged | share flagged | score > 0 | mean score | examples |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for st in check_stats(rows, examples):
        flagged = "never flagged" if st.check == "location_hints" else str(st.flagged)
        share = "" if st.check == "location_hints" else f"{100 * st.flagged_share:.1f} %"
        ids = ", ".join(f"`{i}`" for i in st.examples)
        lines.append(
            f"| `{st.check}` | {flagged} | {share} | {100 * st.nonzero_share:.1f} % "
            f"| {st.mean_score:.3f} | {ids} |"
        )
    return "\n".join(lines) + "\n"


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
