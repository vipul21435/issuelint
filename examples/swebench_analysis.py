"""Run issuelint on public SWE-bench splits and compare its scores with human labels.

    uv run --with matplotlib python examples/swebench_analysis.py DATA_DIR \
        --out docs/results.md --chart docs/signal_shares.png

DATA_DIR holds files downloaded by hand (see the README, "Results on real public data"):

    lite/test.parquet        princeton-nlp/SWE-bench_Lite, test split
    verified/test.parquet    princeton-nlp/SWE-bench_Verified, test split
    full/test.parquet        princeton-nlp/SWE-bench, test split
    swebench_plus/data.json  SWE-Bench+ (Zenodo record 13879453)
    annotations/results/ensembled_annotations_public.csv
                             SWE-bench Verified annotation results

Missing files are skipped. Only counts, shares and instance ids are written out.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from issuelint.agreement import agreement, load_labels
from issuelint.checks import CHECKS, TaskReport, Thresholds, run_all
from issuelint.records import load_records
from issuelint.report import check_stats

DATASETS = (
    ("SWE-bench Lite", "lite/test.parquet"),
    ("SWE-bench Verified", "verified/test.parquet"),
    ("SWE-bench test", "full/test.parquet"),
    ("SWE-Bench+", "swebench_plus/data.json"),
)
ANNOTATIONS = "annotations/results/ensembled_annotations_public.csv"


def held_out(task_id: str) -> bool:
    """The half of the annotated tasks that no metric was designed on (odd SHA-256)."""
    return int(hashlib.sha256(task_id.encode()).hexdigest(), 16) % 2 == 1


def shares_table(runs: dict[str, list[TaskReport]], examples: int) -> list[str]:
    names = list(runs)
    lines = [
        "| check | " + " | ".join(names) + " |",
        "| --- |" + " ---: |" * len(names),
    ]
    stats = {name: {s.check: s for s in check_stats(r, examples)} for name, r in runs.items()}
    for c in CHECKS:
        cells = []
        for name in names:
            s = stats[name][c]
            if c == "location_hints":
                cells.append(f"{100 * s.nonzero_share:.1f} % (score > 0)")
            else:
                cells.append(f"{s.flagged} ({100 * s.flagged_share:.1f} %)")
        lines.append(f"| `{c}` | " + " | ".join(cells) + " |")
    lines.append("| tasks | " + " | ".join(str(len(r)) for r in runs.values()) + " |")
    lines.append("")
    lines.append("Examples (highest-scoring flagged tasks):")
    lines.append("")
    for name in names:
        for c in CHECKS:
            ids = stats[name][c].examples
            if ids:
                lines.append(f"- {name}, `{c}`: " + ", ".join(f"`{i}`" for i in ids))
    return lines


def agreement_table(
    reports: list[TaskReport], labels: dict[str, float], label: str, names: list[str]
) -> list[str]:
    rows_all = {r.name: r for r in agreement([r.as_dict() for r in reports], labels, 2)}
    held = {i: v for i, v in labels.items() if held_out(i)}
    rows_held = {r.name: r for r in agreement([r.as_dict() for r in reports], held, 2)}
    if not rows_all:
        return [f"Label `{label} >= 2`: no score varies on the annotated tasks."]
    first = next(iter(rows_all.values()))
    held_n = next(iter(rows_held.values())).tasks if rows_held else 0
    lines = [
        f"Label `{label} >= 2`: {first.tasks} annotated tasks, {first.positives} positive; "
        f"held-out half: {held_n} tasks.",
        "",
        "| score or metric | AUC, all (95 % interval) | AUC, held-out half "
        "| flagged among positives | flagged among negatives |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in names:
        a, h = rows_all.get(name), rows_held.get(name)
        if a is None:
            continue
        held_cell = "n/a" if h is None else f"{h.auc:.3f} ({h.low:.3f} to {h.high:.3f})"
        fp = "" if a.flagged_positive is None else f"{100 * a.flagged_positive:.1f} %"
        fn = "" if a.flagged_negative is None else f"{100 * a.flagged_negative:.1f} %"
        lines.append(
            f"| `{name}` | {a.auc:.3f} ({a.low:.3f} to {a.high:.3f}) | {held_cell} | {fp} | {fn} |"
        )
    return lines


def chart(runs: dict[str, list[TaskReport]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
    checks = [c for c in CHECKS if c != "location_hints"]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    width = 0.8 / len(runs)
    for k, (name, reports) in enumerate(runs.items()):
        stats = {s.check: s for s in check_stats(reports)}
        ys = [100 * stats[c].flagged_share for c in checks]
        xs = [i + (k - (len(runs) - 1) / 2) * width for i in range(len(checks))]
        ax.bar(xs, ys, width * 0.92, label=f"{name} (n={len(reports)})", color=colors[k])
    ax.set_xticks(range(len(checks)), checks, rotation=15, fontsize=8)
    ax.set_ylabel("tasks flagged (%)")
    ax.set_title("Share of tasks flagged by each issuelint check (default thresholds)", fontsize=10)
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--chart", type=Path)
    parser.add_argument("--examples", type=int, default=3)
    args = parser.parse_args()

    runs: dict[str, list[TaskReport]] = {}
    hinted: dict[str, list[TaskReport]] = {}
    for name, rel in DATASETS:
        path = args.data / rel
        if path.exists():
            records = load_records(path)
            runs[name] = run_all(records)
            hinted[name] = run_all(records, Thresholds(with_hints=True))

    out = ["# issuelint on public SWE-bench data", ""]
    out += ["## Tasks flagged per check, issue text only", ""]
    out += shares_table(runs, args.examples)
    out += ["", "## Tasks flagged per check, issue text plus hints_text", ""]
    out += shares_table(hinted, args.examples)

    labels_path = args.data / ANNOTATIONS
    if labels_path.exists() and "SWE-bench test" in runs:
        reports = runs["SWE-bench test"]
        under = load_labels(labels_path, "underspecified")
        tests = load_labels(labels_path, "false_negative")
        out += ["", "## Agreement with the SWE-bench Verified annotations", ""]
        out += agreement_table(
            reports,
            under,
            "underspecified",
            [
                "underspecification",
                "underspecification.has_reproduction",
                "underspecification.has_expected_actual",
                "underspecification.has_error_text",
                "underspecification.tokens",
                "external_links",
            ],
        )
        out += [""]
        out += agreement_table(
            reports,
            tests,
            "false_negative",
            [
                "scope_gap",
                "scope_gap.unmentioned",
                "scope_gap.tests_use_new_names",
                "location_hints",
                "test_leakage",
                "solution_leakage.added_ngrams",
            ],
        )
    text = "\n".join(out) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)
    if args.chart and runs:
        chart(runs, args.chart)


if __name__ == "__main__":
    main()
