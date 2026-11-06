from __future__ import annotations

import random

from issuelint.checks import CHECKS, Thresholds, run_checks
from issuelint.records import TaskRecord

PATCH = """diff --git a/src/units/convert.py b/src/units/convert.py
--- a/src/units/convert.py
+++ b/src/units/convert.py
@@ -10,6 +10,9 @@ def to_celsius(value, unit):
     if unit == "F":
         return (value - 32) * 5 / 9
+    if unit == "K":
+        return value - 273.15
+    if unit == "C":
+        return value
     raise ValueError(f"unknown unit {unit!r}")
"""

TEST_PATCH = """diff --git a/tests/test_convert.py b/tests/test_convert.py
--- a/tests/test_convert.py
+++ b/tests/test_convert.py
@@ -5,3 +5,8 @@ def test_fahrenheit():
     assert to_celsius(212, "F") == 100
+
+
+def test_kelvin_and_celsius():
+    assert to_celsius(273.15, "K") == 0
+    assert to_celsius(20, "C") == 20
"""

GOOD_ISSUE = (
    "to_celsius rejects kelvin input\n\nSteps to reproduce:\n\n"
    "```python\nfrom units import to_celsius\nto_celsius(273.15, 'K')\n```\n\n"
    "Expected: 0.0. Actual: it raises\n\n```\nValueError: unknown unit 'K'\n```\n"
    "Celsius input should pass through unchanged as well, with a few more words here."
)


def _record(issue: str, patch: str = PATCH, test_patch: str = TEST_PATCH) -> TaskRecord:
    return TaskRecord(id="t", issue=issue, patch=patch, test_patch=test_patch)


def test_every_check_runs_and_scores_are_in_range():
    report = run_checks(_record(GOOD_ISSUE))
    assert [f.check for f in report.findings] == list(CHECKS)
    for f in report.findings:
        assert 0.0 <= f.score <= 1.0
    assert report.flags == []


def test_solution_leakage_flags_an_issue_that_pastes_the_fix():
    issue = (
        GOOD_ISSUE
        + '\n\nFix:\n```python\n    if unit == "K":\n        return value - 273.15\n```\n'
    )
    f = run_checks(_record(issue)).finding("solution_leakage")
    assert f.flagged
    assert f.score > 0.3
    assert any('if unit == "K"' in e for e in f.evidence)


def test_solution_leakage_ignores_test_files_in_the_gold_patch():
    f = run_checks(_record(GOOD_ISSUE, patch=TEST_PATCH)).finding("solution_leakage")
    assert f.score == 0.0
    assert not f.flagged


def test_test_leakage_flags_a_named_test_and_pasted_assertions():
    issue = (
        GOOD_ISSUE
        + '\n\ntest_kelvin_and_celsius fails on\n```\nassert to_celsius(20, "C") == 20\n```'
    )
    f = run_checks(_record(issue)).finding("test_leakage")
    assert f.flagged
    assert f.score == 2 / 3
    assert any("test_kelvin_and_celsius" in e for e in f.evidence)


def test_test_leakage_is_zero_without_a_test_patch():
    f = run_checks(_record(GOOD_ISSUE, test_patch="")).finding("test_leakage")
    assert f.score == 0.0


def test_location_hints_are_reported_but_never_flagged():
    issue = GOOD_ISSUE + "\n\nThe bug is in src/units/convert.py."
    f = run_checks(_record(issue)).finding("location_hints")
    assert f.score == 1.0
    assert not f.flagged
    assert any("convert.py" in e for e in f.evidence)


def test_underspecification_counts_missing_signals():
    f = run_checks(_record("it is broken")).finding("underspecification")
    assert f.score == 1.0
    assert f.flagged
    assert len(f.evidence) == 4
    good = run_checks(_record(GOOD_ISSUE)).finding("underspecification")
    assert good.score == 0.0


def test_external_links_depend_on_own_evidence():
    only_link = run_checks(_record("See https://example.invalid/x/1")).finding("external_links")
    assert only_link.score == 1.0
    assert only_link.flagged
    with_code = run_checks(_record(GOOD_ISSUE + "\nhttps://example.invalid/x/1")).finding(
        "external_links"
    )
    assert with_code.score == 0.5
    assert not with_code.flagged
    none = run_checks(_record(GOOD_ISSUE)).finding("external_links")
    assert none.score == 0.0


def test_scope_gap_counts_unmentioned_identifiers():
    f = run_checks(_record("kelvin is wrong, expected zero but got an error")).finding("scope_gap")
    assert f.score == 1.0
    assert f.flagged
    assert f.evidence == ["changed but not mentioned: to_celsius"]
    assert run_checks(_record(GOOD_ISSUE)).finding("scope_gap").score == 0.0


def test_thresholds_change_flags_not_scores():
    strict = Thresholds(scope_gap=0.0, underspecification=0.0)
    report = run_checks(_record(GOOD_ISSUE), strict)
    assert report.finding("scope_gap").score == 0.0
    assert report.finding("scope_gap").flagged  # 0.0 >= 0.0
    loose = Thresholds(solution_leakage=1.1)
    issue = GOOD_ISSUE + '\n```python\n    if unit == "K":\n        return value - 273.15\n```\n'
    assert not run_checks(_record(issue), loose).finding("solution_leakage").flagged


def test_evidence_is_capped():
    t = Thresholds(max_evidence=1, scope_gap=0.0)
    patch = PATCH + "".join(
        f"diff --git a/src/m{i}.py b/src/m{i}.py\n--- a/src/m{i}.py\n+++ b/src/m{i}.py\n"
        f"@@ -1,1 +1,2 @@\n+def helper_{i}():\n+    pass\n"
        for i in range(4)
    )
    f = run_checks(_record("short text", patch=patch), t).finding("scope_gap")
    assert len(f.evidence) == 2
    assert f.evidence[1].startswith("... 4 more")


def test_leakage_score_is_monotone_in_the_pasted_share():
    """Property: pasting more of the patch's added lines never lowers the leakage score."""
    rng = random.Random(7)
    added = ['if unit == "K":', "return value - 273.15", 'if unit == "C":', "return value"]
    last = -1.0
    for k in range(len(added) + 1):
        lines = added[:k]
        rng.shuffle(lines)
        issue = GOOD_ISSUE + "\n```\n" + "\n".join(lines) + "\n```\n"
        score = run_checks(_record(issue), Thresholds(ngram=3)).finding("solution_leakage").score
        assert score >= last - 1e-9
        last = score
    assert last == 1.0


def test_report_dict_shape():
    d = run_checks(_record(GOOD_ISSUE)).as_dict()
    assert d["id"] == "t"
    assert d["flags"] == []
    assert {f["check"] for f in d["findings"]} == set(CHECKS)
    assert all({"score", "flagged", "summary", "evidence"} <= set(f) for f in d["findings"])


def test_findings_carry_counts_in_metrics():
    report = run_checks(_record(GOOD_ISSUE))
    for f in report.findings:
        assert "metrics" in f.as_dict()
    under = report.finding("underspecification").metrics
    assert set(under) == {"has_reproduction", "has_expected_actual", "has_error_text", "tokens"}
    sol = report.finding("solution_leakage").metrics
    assert sol["shared_ngrams"] <= sol["added_ngrams"]
