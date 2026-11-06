"""The six checks. Each returns a Finding with a score in [0, 1], a flag and evidence lines.

Scores are plain ratios so that they can be read without the code:

* ``solution_leakage``: share of the gold patch's added-code token n-grams that
  also occur in the issue's code blocks.
* ``test_leakage``: share of test names and assertion lines the test patch adds
  that the issue already names.
* ``location_hints``: share of changed files and changed identifiers that the
  issue names. Reported, never flagged.
* ``underspecification``: share of four signals that are missing (reproduction,
  expected against actual, error text, minimum length).
* ``external_links``: 1.0 when the issue links out and carries no code or error
  text of its own, 0.5 when it links out beside its own evidence, 0 otherwise.
* ``scope_gap``: share of identifiers the gold patch changes that the issue
  never mentions.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from issuelint.patch import ParsedPatch, parse_patch
from issuelint.records import TaskRecord
from issuelint.text import (
    code_blocks,
    code_lines,
    code_ngrams,
    drop_traceback_source,
    inline_code,
    mentions,
    mentions_path,
    ngrams,
    tokens,
    urls,
    words,
)


@dataclass(frozen=True)
class Thresholds:
    """Flag cut-offs and sizes; every one is a CLI flag.

    ``with_hints`` appends the record's hints (in SWE-bench, issue comments made
    before the fix) to the issue text before the checks read it.
    """

    ngram: int = 6
    solution_leakage: float = 0.2
    test_leakage: float = 0.34
    underspecification: float = 0.5
    scope_gap: float = 0.5
    min_issue_tokens: int = 40
    max_evidence: int = 8
    with_hints: bool = False


@dataclass
class Finding:
    """Result of one check on one task."""

    check: str
    score: float
    flagged: bool
    summary: str
    evidence: list[str] = field(default_factory=list)
    metrics: dict[str, int | float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "check": self.check,
            "score": round(self.score, 4),
            "flagged": self.flagged,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "metrics": dict(self.metrics),
        }


@dataclass
class TaskReport:
    """Every finding for one task."""

    id: str
    findings: list[Finding]

    @property
    def flags(self) -> list[str]:
        return [f.check for f in self.findings if f.flagged]

    def finding(self, check: str) -> Finding:
        for f in self.findings:
            if f.check == check:
                return f
        raise KeyError(check)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "flags": self.flags,
            "findings": [f.as_dict() for f in self.findings],
        }


_TEST_NAME_RES = (
    re.compile(r"^\s*(?:async\s+)?def\s+(test\w*)"),
    re.compile(r"^\s*(?:it|test|describe)\s*\(\s*['\"`]([^'\"`]+)['\"`]"),
    re.compile(r"^\s*#\[test\]\s*$"),
    re.compile(r"^\s*(?:pub\s+)?fn\s+(test\w*)"),
    re.compile(r"^func\s+(Test\w*)"),
)
_ASSERT_RE = re.compile(
    r"^\s*(?:assert\b|assert_|expect\(|self\.assert|pytest\.raises|t\.Errorf|t\.Fatal)"
)
_ERROR_RE = re.compile(
    r"Traceback \(most recent call last\)"
    r"|\b\w*(?:Error|Exception|Panic|panic|FAILED|Failed|fatal)\b[: ]"
)
_REPRO_RE = re.compile(
    r"\b(?:reproduc\w*|steps?\s+to\b|minimal\s+example|MWE|MRE|to\s+trigger)\b", re.I
)
_EXPECTED_RE = re.compile(r"\b(?:expected|should|supposed to|ought to)\b", re.I)
_ACTUAL_RE = re.compile(
    r"\b(?:actual\w*|instead|but\s+(?:it|I|we|the)\b|got|returns?|gives?|outputs?)\b", re.I
)


def _cap(items: list[str], limit: int) -> list[str]:
    if len(items) <= limit:
        return items
    return [*items[:limit], f"... {len(items) - limit} more"]


def _issue_code_text(issue: str) -> str:
    return drop_traceback_source("\n".join([*code_blocks(issue), *inline_code(issue)]))


def check_solution_leakage(record: TaskRecord, patch: ParsedPatch, t: Thresholds) -> Finding:
    # An added line whose tokens equal a removed line's is moved or re-indented code,
    # not new code: an issue that quotes it (often in a traceback) shows the old code.
    removed = {tuple(tokens(line)) for line in patch.removed_lines(include_tests=False)}
    added = [
        line
        for line in code_lines(patch.added_lines(include_tests=False))
        if tuple(tokens(line)) not in removed
    ]
    patch_grams = code_ngrams(tokens("\n".join(added)), t.ngram)
    issue_grams = set(code_ngrams(tokens(_issue_code_text(record.issue)), t.ngram))
    if not patch_grams:
        return Finding("solution_leakage", 0.0, False, "no new added code of at least one n-gram")
    hits = [g for g in patch_grams if g in issue_grams]
    score = len(hits) / len(patch_grams)
    evidence: list[str] = []
    for line in added:
        grams = code_ngrams(tokens(line), t.ngram)
        if grams and all(g in issue_grams for g in grams):
            evidence.append(f"added line present in issue code: {line.strip()}")
    summary = (
        f"{len(hits)} of {len(patch_grams)} added-code {t.ngram}-grams appear in the issue's code"
    )
    return Finding(
        "solution_leakage",
        score,
        score >= t.solution_leakage,
        summary,
        _cap(evidence, t.max_evidence),
        {
            "shared_ngrams": len(hits),
            "added_ngrams": len(patch_grams),
            "lines_in_issue": len(evidence),
        },
    )


def _added_test_names(test_patch: ParsedPatch) -> list[str]:
    names: dict[str, None] = {}
    for line in test_patch.added_lines():
        for pattern in _TEST_NAME_RES:
            match = pattern.match(line)
            if match and match.groups():
                names.setdefault(match.group(1), None)
                break
    return list(names)


_TEST_ID_NAME_RE = re.compile(r"^(?:test\w*|Test\w*)$")


def test_names_from_ids(ids: tuple[str, ...] | list[str]) -> list[str]:
    """Test function names from test ids such as SWE-bench's FAIL_TO_PASS.

    ``path::Class::test_x[param]`` gives ``test_x``; ``test_x (module.Class)`` gives
    ``test_x``; ids that are not test names (docstring lines) are skipped.
    """
    names: dict[str, None] = {}
    for test_id in ids:
        head = test_id.split(" (", 1)[0].split("[", 1)[0]
        name = head.rsplit("::", 1)[-1].strip()
        if _TEST_ID_NAME_RE.match(name):
            names.setdefault(name, None)
    return list(names)


def check_test_leakage(record: TaskRecord, test_patch: ParsedPatch, t: Thresholds) -> Finding:
    names = list(
        dict.fromkeys([*_added_test_names(test_patch), *test_names_from_ids(record.fail_to_pass)])
    )
    asserts = [line.strip() for line in test_patch.added_lines() if _ASSERT_RE.match(line)]
    issue_words = words(record.issue)
    # Whole assertion lines are matched, so every gram counts here, not only informative ones.
    issue_grams = set(ngrams(tokens(record.issue), t.ngram))
    evidence: list[str] = []
    hit = 0
    for name in names:
        # Identifier names must appear as a whole word; titles such as it("renders
        # the header") contain spaces and are matched as a phrase.
        if mentions(issue_words, name) or (" " in name and name in record.issue):
            hit += 1
            evidence.append(f"issue names the added test: {name}")
    for line in asserts:
        grams = ngrams(tokens(line), t.ngram)
        if grams and all(g in issue_grams for g in grams):
            hit += 1
            evidence.append(f"issue contains the added assertion: {line}")
    total = len(names) + len(asserts)
    if total == 0:
        return Finding("test_leakage", 0.0, False, "test patch adds no test names or assertions")
    score = hit / total
    summary = (
        f"{hit} of {total} ({len(names)} test names, {len(asserts)} assertions) "
        "already in the issue"
    )
    return Finding(
        "test_leakage",
        score,
        score >= t.test_leakage,
        summary,
        _cap(evidence, t.max_evidence),
        {"hits": hit, "test_names": len(names), "assertions": len(asserts)},
    )


def check_location_hints(record: TaskRecord, patch: ParsedPatch, t: Thresholds) -> Finding:
    paths = [f.path for f in patch.files if not f.is_test]
    idents = patch.changed_identifiers()
    issue_words = words(record.issue)
    evidence: list[str] = []
    hit = 0
    for path in paths:
        form = mentions_path(record.issue, path)
        if form:
            hit += 1
            evidence.append(f"issue names changed file {path} as '{form}'")
    for name in idents:
        if mentions(issue_words, name):
            hit += 1
            evidence.append(f"issue names changed identifier {name}")
    total = len(paths) + len(idents)
    if total == 0:
        return Finding("location_hints", 0.0, False, "patch changes no non-test files")
    score = hit / total
    summary = f"{hit} of {total} ({len(paths)} files, {len(idents)} identifiers) named in the issue"
    return Finding(
        "location_hints",
        score,
        False,
        summary,
        _cap(evidence, t.max_evidence),
        {"hits": hit, "files": len(paths), "identifiers": len(idents)},
    )


def check_underspecification(record: TaskRecord, _patch: ParsedPatch, t: Thresholds) -> Finding:
    issue = record.issue
    has_repro = bool(code_blocks(issue)) or bool(_REPRO_RE.search(issue))
    has_expected = bool(_EXPECTED_RE.search(issue)) and bool(_ACTUAL_RE.search(issue))
    has_error = bool(_ERROR_RE.search(issue))
    length = len(tokens(issue))
    long_enough = length >= t.min_issue_tokens
    missing = []
    if not has_repro:
        missing.append("no reproduction (no code block, no 'reproduce' or 'steps to')")
    if not has_expected:
        missing.append("no expected-against-actual wording")
    if not has_error:
        missing.append("no error text (traceback, exception or error name)")
    if not long_enough:
        missing.append(f"short: {length} tokens, below {t.min_issue_tokens}")
    score = len(missing) / 4
    summary = f"{len(missing)} of 4 specification signals missing"
    metrics: dict[str, int | float] = {
        "has_reproduction": int(has_repro),
        "has_expected_actual": int(has_expected),
        "has_error_text": int(has_error),
        "tokens": length,
    }
    return Finding(
        "underspecification", score, score >= t.underspecification, summary, missing, metrics
    )


def check_external_links(record: TaskRecord, _patch: ParsedPatch, t: Thresholds) -> Finding:
    links = urls(record.issue)
    if not links:
        return Finding("external_links", 0.0, False, "no links")
    own_evidence = bool(code_blocks(record.issue)) or bool(_ERROR_RE.search(record.issue))
    score = 0.5 if own_evidence else 1.0
    summary = f"{len(links)} link(s); " + (
        "the issue also carries its own code or error text"
        if own_evidence
        else "no code or error text of its own"
    )
    return Finding(
        "external_links",
        score,
        score >= 1.0,
        summary,
        _cap([f"link: {u}" for u in links], t.max_evidence),
        {"links": len(links), "own_evidence": int(own_evidence)},
    )


def check_scope_gap(
    record: TaskRecord,
    patch: ParsedPatch,
    t: Thresholds,
    test_patch: ParsedPatch | None = None,
) -> Finding:
    """Changed identifiers the issue never names.

    Also reported, without changing the score: names that appear on the gold
    patch's added lines (and on none of its removed lines), on the test patch's
    added lines, and nowhere in the issue. The SWE-bench Verified annotation
    instructions name tests that rely on a new function, variable name or error
    message absent from the issue as the most common reason a test rejects a
    reasonable solution.
    """
    idents = patch.changed_identifiers()
    if not idents:
        return Finding("scope_gap", 0.0, False, "patch changes no named definitions")
    issue_words = words(record.issue)
    unmentioned = [name for name in idents if not mentions(issue_words, name)]
    test_words: set[str] = set()
    if test_patch:
        test_words = words("\n".join(code_lines(test_patch.added_lines())))
        test_words -= words("\n".join(test_patch.removed_lines()))
    needed = [
        name for name in patch.new_names() if name in test_words and not mentions(issue_words, name)
    ]
    score = len(unmentioned) / len(idents)
    summary = (
        f"{len(unmentioned)} of {len(idents)} changed identifiers never mentioned in the issue"
    )
    evidence = [
        *(f"tests use {name}, added by the gold patch, absent from the issue" for name in needed),
        *(f"changed but not mentioned: {name}" for name in unmentioned if name not in needed),
    ]
    return Finding(
        "scope_gap",
        score,
        score >= t.scope_gap,
        summary,
        _cap(evidence, t.max_evidence),
        {
            "unmentioned": len(unmentioned),
            "identifiers": len(idents),
            "tests_use_new_names": len(needed),
        },
    )


CHECKS: tuple[str, ...] = (
    "solution_leakage",
    "test_leakage",
    "location_hints",
    "underspecification",
    "external_links",
    "scope_gap",
)

_CheckFn = Callable[[TaskRecord, ParsedPatch, Thresholds], Finding]


def run_checks(record: TaskRecord, thresholds: Thresholds | None = None) -> TaskReport:
    """Run every check on one record."""
    t = thresholds or Thresholds()
    if t.with_hints and record.hints.strip():
        record = replace(record, issue=record.issue_text(with_hints=True))
    patch = parse_patch(record.patch)
    test_patch = parse_patch(record.test_patch)
    findings = [
        check_solution_leakage(record, patch, t),
        check_test_leakage(record, test_patch, t),
        check_location_hints(record, patch, t),
        check_underspecification(record, patch, t),
        check_external_links(record, patch, t),
        check_scope_gap(record, patch, t, test_patch),
    ]
    return TaskReport(id=record.id, findings=findings)


def run_all(records: list[TaskRecord], thresholds: Thresholds | None = None) -> list[TaskReport]:
    return [run_checks(r, thresholds) for r in records]
