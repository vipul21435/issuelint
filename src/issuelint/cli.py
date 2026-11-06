"""Command line entry point: ``issuelint check FILE [options]``."""

from __future__ import annotations

import argparse
import math
import os
import sys
from collections.abc import Callable
from pathlib import Path

from issuelint import __version__
from issuelint.agreement import agreement, format_agreement, load_findings, load_labels
from issuelint.checks import Thresholds, run_all
from issuelint.records import RecordError, load_records
from issuelint.report import explain, summary, table, to_csv, to_json, to_markdown


def _count(minimum: int) -> Callable[[str], int]:
    """An argparse type for whole numbers of at least ``minimum`` (bad values exit 2)."""

    def parse(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected a whole number, got {text!r}") from None
        if value < minimum:
            raise argparse.ArgumentTypeError(f"must be at least {minimum}, got {value}")
        return value

    return parse


def _finite(text: str) -> float:
    """An argparse type for finite numbers; NaN and infinities exit 2."""
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a number, got {text!r}") from None
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError(f"must be a finite number, got {text!r}")
    return value


def _share(text: str) -> float:
    """An argparse type for a share threshold: a finite number from 0 to 1."""
    value = _finite(text)
    if not 0.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, got {text!r}")
    return value


def _unwritable(path: Path) -> str | None:
    """Why ``path`` cannot be written, checked before any work is done; None if it can."""
    parent = path.parent
    if path.is_dir():
        return "is a directory"
    if not parent.is_dir():
        return f"directory {parent} does not exist"
    if not os.access(parent, os.W_OK):
        return f"directory {parent} is not writable"
    return None


def build_parser() -> argparse.ArgumentParser:
    """The argument parser for the ``check`` and ``agree`` subcommands."""
    parser = argparse.ArgumentParser(
        prog="issuelint",
        description="Check issue-to-fix task records for leaks and gaps.",
    )
    parser.add_argument("--version", action="version", version=f"issuelint {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser(
        "check", help="run every check on a .jsonl, .json or .parquet file of records"
    )
    check.add_argument("input", type=Path, help=".jsonl, .json or .parquet file of task records")
    check.add_argument("--limit", type=_count(0), help="check only the first N records")
    check.add_argument(
        "--with-hints",
        action="store_true",
        help="read the hints (hints_text) together with the issue text",
    )
    check.add_argument("--explain", action="store_true", help="print evidence for every task")
    check.add_argument(
        "--flagged-only",
        action="store_true",
        help="with --explain, print only tasks flagged by a check other than location_hints",
    )
    check.add_argument("--json", type=Path, metavar="FILE", help="write findings as JSON")
    check.add_argument("--csv", type=Path, metavar="FILE", help="write scores and flags as CSV")
    check.add_argument(
        "--markdown", type=Path, metavar="FILE", help="write the per-check shares as Markdown"
    )
    check.add_argument(
        "--examples",
        type=_count(0),
        default=0,
        metavar="N",
        help="list up to N example ids per check in the summary (0)",
    )
    check.add_argument("--quiet", action="store_true", help="no table, only the summary")
    check.add_argument(
        "--fail-on-flag",
        action="store_true",
        help="exit 1 when any task is flagged by a check other than location_hints",
    )
    d = Thresholds()
    check.add_argument(
        "--ngram", type=_count(1), default=d.ngram, help=f"token n-gram size ({d.ngram})"
    )
    check.add_argument(
        "--solution-leakage",
        type=_share,
        default=d.solution_leakage,
        help=f"flag at this share of added-code n-grams found in the issue ({d.solution_leakage})",
    )
    check.add_argument(
        "--test-leakage",
        type=_share,
        default=d.test_leakage,
        help=f"flag at this share of added tests and assertions in the issue ({d.test_leakage})",
    )
    check.add_argument(
        "--underspecification",
        type=_share,
        default=d.underspecification,
        help=f"flag at this share of missing specification signals ({d.underspecification})",
    )
    check.add_argument(
        "--scope-gap",
        type=_share,
        default=d.scope_gap,
        help=f"flag at this share of changed identifiers the issue never names ({d.scope_gap})",
    )
    check.add_argument(
        "--min-issue-tokens",
        type=_count(0),
        default=d.min_issue_tokens,
        help=f"an issue with fewer tokens counts as short ({d.min_issue_tokens})",
    )
    check.add_argument(
        "--max-evidence",
        type=_count(0),
        default=d.max_evidence,
        help=f"evidence lines kept per finding ({d.max_evidence})",
    )
    agree = sub.add_parser(
        "agree", help="compare scores from 'check --json' with human labels in a CSV"
    )
    agree.add_argument("findings", type=Path, help="JSON written by issuelint check --json")
    agree.add_argument("labels", type=Path, help="CSV with one row per task")
    agree.add_argument("--label", required=True, help="numeric label column")
    agree.add_argument(
        "--positive-at",
        type=_finite,
        default=1.0,
        help="a task is positive when its label is at least this (1)",
    )
    agree.add_argument("--id-column", default="instance_id", help="id column (instance_id)")
    agree.add_argument(
        "--resamples", type=_count(1), default=1000, help="bootstrap resamples (1000)"
    )
    agree.add_argument("--seed", type=int, default=0, help="bootstrap seed (0)")
    return parser


def _agree(args: argparse.Namespace) -> int:
    try:
        reports = load_findings(args.findings)
        labels = load_labels(args.labels, args.label, args.id_column)
    except (ValueError, OSError) as exc:
        print(f"issuelint: {exc}", file=sys.stderr)
        return 2
    if not {str(r["id"]) for r in reports} & set(labels):
        print(
            f"issuelint: no task id in {args.findings} matches column "
            f"{args.id_column} of {args.labels}",
            file=sys.stderr,
        )
        return 2
    rows = agreement(reports, labels, args.positive_at, args.resamples, args.seed)
    print(format_agreement(rows, args.label, args.positive_at))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the command line; returns 0, 1 with ``--fail-on-flag`` and a flag, 2 on bad input."""
    args = build_parser().parse_args(argv)
    if args.command == "agree":
        return _agree(args)
    thresholds = Thresholds(
        ngram=args.ngram,
        solution_leakage=args.solution_leakage,
        test_leakage=args.test_leakage,
        underspecification=args.underspecification,
        scope_gap=args.scope_gap,
        min_issue_tokens=args.min_issue_tokens,
        max_evidence=args.max_evidence,
        with_hints=args.with_hints,
    )
    outputs = [p for p in (args.markdown, args.json, args.csv) if p is not None]
    for path in outputs:
        problem = _unwritable(path)
        if problem:
            print(f"issuelint: cannot write {path}: {problem}", file=sys.stderr)
            return 2
    try:
        records = load_records(args.input, limit=args.limit)
    except (RecordError, OSError) as exc:
        print(f"issuelint: {exc}", file=sys.stderr)
        return 2
    reports = run_all(records, thresholds)
    if not args.quiet:
        print(table(reports))
        print()
    if args.explain:
        for r in reports:
            if args.flagged_only and not [f for f in r.flags if f != "location_hints"]:
                continue
            print(explain(r))
            print()
    print(summary(reports, examples=args.examples))
    writes = [
        (args.markdown, lambda: to_markdown(reports, max(args.examples, 3))),
        (args.json, lambda: to_json(reports)),
        (args.csv, lambda: to_csv(reports)),
    ]
    for path, render in writes:
        if path is None:
            continue
        try:
            path.write_text(render(), encoding="utf-8")
        except OSError as exc:
            print(f"issuelint: cannot write {path}: {exc.strerror or exc}", file=sys.stderr)
            return 2
    if args.fail_on_flag and any(f for r in reports for f in r.flags if f != "location_hints"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
