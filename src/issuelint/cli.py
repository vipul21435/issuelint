"""Command line entry point: ``issuelint check FILE [options]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from issuelint import __version__
from issuelint.checks import Thresholds, run_all
from issuelint.records import RecordError, load_records
from issuelint.report import explain, summary, table, to_csv, to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="issuelint",
        description="Check issue-to-fix task records for leaks and gaps.",
    )
    parser.add_argument("--version", action="version", version=f"issuelint {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="run every check on a JSONL or JSON file of records")
    check.add_argument("input", type=Path, help=".jsonl, .json or .parquet file of task records")
    check.add_argument("--limit", type=int, help="check only the first N records")
    check.add_argument(
        "--with-hints",
        action="store_true",
        help="read the hints (hints_text) together with the issue text",
    )
    check.add_argument("--explain", action="store_true", help="print evidence for every task")
    check.add_argument("--json", type=Path, metavar="FILE", help="write findings as JSON")
    check.add_argument("--csv", type=Path, metavar="FILE", help="write scores and flags as CSV")
    check.add_argument("--quiet", action="store_true", help="no table, only the summary")
    check.add_argument(
        "--fail-on-flag",
        action="store_true",
        help="exit 1 when any task is flagged by a check other than location_hints",
    )
    d = Thresholds()
    check.add_argument("--ngram", type=int, default=d.ngram, help=f"token n-gram size ({d.ngram})")
    check.add_argument(
        "--solution-leakage",
        type=float,
        default=d.solution_leakage,
        help=f"flag at this share of added-code n-grams found in the issue ({d.solution_leakage})",
    )
    check.add_argument(
        "--test-leakage",
        type=float,
        default=d.test_leakage,
        help=f"flag at this share of added tests and assertions in the issue ({d.test_leakage})",
    )
    check.add_argument(
        "--underspecification",
        type=float,
        default=d.underspecification,
        help=f"flag at this share of missing specification signals ({d.underspecification})",
    )
    check.add_argument(
        "--scope-gap",
        type=float,
        default=d.scope_gap,
        help=f"flag at this share of changed identifiers the issue never names ({d.scope_gap})",
    )
    check.add_argument(
        "--min-issue-tokens",
        type=int,
        default=d.min_issue_tokens,
        help=f"an issue with fewer tokens counts as short ({d.min_issue_tokens})",
    )
    check.add_argument(
        "--max-evidence",
        type=int,
        default=d.max_evidence,
        help=f"evidence lines kept per finding ({d.max_evidence})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
            print(explain(r))
            print()
    print(summary(reports))
    if args.json:
        args.json.write_text(to_json(reports), encoding="utf-8")
    if args.csv:
        args.csv.write_text(to_csv(reports), encoding="utf-8")
    if args.fail_on_flag and any(f for r in reports for f in r.flags if f != "location_hints"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
