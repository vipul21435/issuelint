"""Agreement between check scores and human labels.

Given the JSON written by ``issuelint check --json`` and a CSV of per-task human
labels (for example the SWE-bench Verified annotations, where each task has an
``underspecified`` severity from 0 to 3), this module measures how well each
score ranks the tasks a human marked as positive above the others.

The measure is the area under the ROC curve, computed as the Mann-Whitney
statistic: the probability that a randomly chosen positive task scores higher
than a randomly chosen negative one, ties counting one half. 0.5 is chance.
The interval is a percentile bootstrap over tasks.
"""

from __future__ import annotations

import csv
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mid = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mid
        i = j + 1
    return ranks


def auc(scores: Sequence[float], labels: Sequence[bool]) -> float:
    """Area under the ROC curve of ``scores`` for the boolean ``labels``.

    Raises ``ValueError`` when the labels hold only one class.
    """
    if len(scores) != len(labels):
        raise ValueError("scores and labels differ in length")
    n_pos = sum(1 for y in labels if y)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        raise ValueError("labels need at least one positive and one negative")
    ranks = _average_ranks(scores)
    rank_sum = sum(r for r, y in zip(ranks, labels, strict=True) if y)
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def bootstrap_auc(
    scores: Sequence[float],
    labels: Sequence[bool],
    resamples: int = 1000,
    level: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap interval for :func:`auc`, resampling tasks with replacement.

    Resamples that draw a single class are skipped.
    """
    rng = random.Random(seed)
    n = len(scores)
    values = []
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        ys = [labels[i] for i in idx]
        if all(ys) or not any(ys):
            continue
        values.append(auc([scores[i] for i in idx], ys))
    if not values:
        raise ValueError("no bootstrap resample held both classes")
    values.sort()
    lo = values[int((1 - level) / 2 * (len(values) - 1))]
    hi = values[int((1 + level) / 2 * (len(values) - 1))]
    return lo, hi


@dataclass(frozen=True)
class AgreementRow:
    """How one score or metric lines up with the binary label."""

    name: str
    tasks: int
    positives: int
    auc: float
    low: float
    high: float
    flagged_positive: float | None
    flagged_negative: float | None


def load_labels(path: str | Path, label: str, id_column: str = "instance_id") -> dict[str, float]:
    """Read ``id_column`` and the numeric column ``label`` of a CSV; blank labels are skipped."""
    out: dict[str, float] = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {id_column, label} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} has no column(s) {sorted(missing)}")
        for row in reader:
            value = (row.get(label) or "").strip()
            if value:
                out[row[id_column]] = float(value)
    return out


def load_findings(path: str | Path) -> list[dict[str, object]]:
    """Read the list written by ``issuelint check --json``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a list of task reports")
    return data


def _series(reports: list[dict[str, object]]) -> dict[str, dict[str, tuple[float, bool | None]]]:
    """name -> id -> (value, flagged); names are check scores and check.metric values."""
    series: dict[str, dict[str, tuple[float, bool | None]]] = {}
    for report in reports:
        task_id = str(report["id"])
        for finding in report["findings"]:  # type: ignore[union-attr]
            check = finding["check"]
            series.setdefault(check, {})[task_id] = (float(finding["score"]), finding["flagged"])
            for key, value in (finding.get("metrics") or {}).items():
                series.setdefault(f"{check}.{key}", {})[task_id] = (float(value), None)
    return series


def agreement(
    reports: list[dict[str, object]],
    labels: dict[str, float],
    positive_at: float,
    resamples: int = 1000,
    seed: int = 0,
) -> list[AgreementRow]:
    """AUC of every score and metric against ``label >= positive_at``, on the shared tasks.

    Scores or metrics that are constant on the shared tasks, or tasks sets with a
    single class, are left out.
    """
    rows = []
    for name, values in _series(reports).items():
        ids = [i for i in values if i in labels]
        if not ids:
            continue
        ys = [labels[i] >= positive_at for i in ids]
        xs = [values[i][0] for i in ids]
        if all(ys) or not any(ys) or len(set(xs)) < 2:
            continue
        lo, hi = bootstrap_auc(xs, ys, resamples=resamples, seed=seed)
        flags = [values[i][1] for i in ids]
        fp = fn = None
        if flags[0] is not None:
            pos = [bool(f) for f, y in zip(flags, ys, strict=True) if y]
            neg = [bool(f) for f, y in zip(flags, ys, strict=True) if not y]
            fp = sum(pos) / len(pos)
            fn = sum(neg) / len(neg)
        rows.append(AgreementRow(name, len(ids), sum(ys), auc(xs, ys), lo, hi, fp, fn))
    return rows


def format_agreement(rows: list[AgreementRow], label: str, positive_at: float) -> str:
    """A text table; the flag columns give the share flagged among positives and negatives."""
    if not rows:
        return "no score varies on the labelled tasks"
    head = (
        f"positive: {label} >= {positive_at:g}; {rows[0].tasks} tasks, {rows[0].positives} positive"
    )
    lines = [
        head,
        f"{'score or metric':<40} {'AUC':>6} {'95% interval':>15} {'flag|pos':>9} {'flag|neg':>9}",
    ]
    for r in rows:
        fp = "" if r.flagged_positive is None else f"{r.flagged_positive:.3f}"
        fn = "" if r.flagged_negative is None else f"{r.flagged_negative:.3f}"
        lines.append(
            f"{r.name:<40} {r.auc:6.3f} {f'[{r.low:.3f}, {r.high:.3f}]':>15} {fp:>9} {fn:>9}"
        )
    return "\n".join(lines)
