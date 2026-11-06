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
from dataclasses import dataclass, field

from issuelint.patch import ParsedPatch, parse_patch
from issuelint.records import TaskRecord
from issuelint.text import (
    code_blocks,
    code_lines,
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
    """Flag cut-offs and sizes; every one is a CLI flag."""

    ngram: int = 6
    solution_leakage: float = 0.2
    test_leakage: float = 0.34
    underspecification: float = 0.5
    scope_gap: float = 0.5
    min_issue_tokens: int = 40
    max_evidence: int = 8


@dataclass
class Finding:
    """Result of one check on one task."""

    check: str
    score: float
    flagged: bool
    summary: str
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "check": self.check,
            "score": round(self.score, 4),
            "flagged": self.flagged,
            "summary": self.summary,
            "evidence": list(self.evidence),
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
    return "\n".join([*code_blocks(issue), *inline_code(issue)])


def check_solution_leakage(record: TaskRecord, patch: ParsedPatch, t: Thresholds) -> Finding:
    added = code_lines(patch.added_lines(include_tests=False))
    added_tokens = tokens("\n".join(added))
    patch_grams = ngrams(added_tokens, t.ngram)
    issue_grams = set(ngrams(tokens(_issue_code_text(record.issue)), t.ngram))
    if not patch_grams:
        return Finding("solution_leakage", 0.0, False, "no added code of at least one n-gram")
    hits = [g for g in patch_grams if g in issue_grams]
    score = len(hits) / len(patch_grams)
    evidence: list[str] = []
    for line in added:
        grams = ngrams(tokens(line), t.ngram)
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


def check_test_leakage(record: TaskRecord, test_patch: ParsedPatch, t: Thresholds) -> Finding:
    names = _added_test_names(test_patch)
    asserts = [line.strip() for line in test_patch.added_lines() if _ASSERT_RE.match(line)]
    issue_words = words(record.issue)
    issue_grams = set(ngrams(tokens(record.issue), t.ngram))
    evidence: list[str] = []
    hit = 0
    for name in names:
        if name in record.issue or mentions(issue_words, name):
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
        "test_leakage", score, score >= t.test_leakage, summary, _cap(evidence, t.max_evidence)
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
    return Finding("location_hints", score, False, summary, _cap(evidence, t.max_evidence))


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
    return Finding("underspecification", score, score >= t.underspecification, summary, missing)


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
    )


def check_scope_gap(record: TaskRecord, patch: ParsedPatch, t: Thresholds) -> Finding:
    idents = patch.changed_identifiers()
    if not idents:
        return Finding("scope_gap", 0.0, False, "patch changes no named definitions")
    issue_words = words(record.issue)
    unmentioned = [name for name in idents if not mentions(issue_words, name)]
    score = len(unmentioned) / len(idents)
    summary = (
        f"{len(unmentioned)} of {len(idents)} changed identifiers never mentioned in the issue"
    )
    evidence = [f"changed but not mentioned: {name}" for name in unmentioned]
    return Finding(
        "scope_gap", score, score >= t.scope_gap, summary, _cap(evidence, t.max_evidence)
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
    patch = parse_patch(record.patch)
    test_patch = parse_patch(record.test_patch)
    findings = [
        check_solution_leakage(record, patch, t),
        check_test_leakage(record, test_patch, t),
        check_location_hints(record, patch, t),
        check_underspecification(record, patch, t),
        check_external_links(record, patch, t),
        check_scope_gap(record, patch, t),
    ]
    return TaskReport(id=record.id, findings=findings)


def run_all(records: list[TaskRecord], thresholds: Thresholds | None = None) -> list[TaskReport]:
    return [run_checks(r, thresholds) for r in records]
