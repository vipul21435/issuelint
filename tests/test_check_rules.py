"""One test per documented rule and boundary of the checks."""

from __future__ import annotations

from dataclasses import replace

from issuelint.checks import Thresholds, run_checks
from issuelint.records import TaskRecord

SOURCE = (
    "--- a/pkg/conv.py\n+++ b/pkg/conv.py\n@@ -1,1 +1,3 @@ def to_celsius(value, unit):\n"
    "     pass\n"
    '+    if unit == "K" and value is not None:\n'
    "+        return round(value - 273.15, ndigits)\n"
)


def _finding(check: str, issue: str, patch: str = SOURCE, test_patch: str = "", **kw):
    t = replace(Thresholds(), **kw)
    record = TaskRecord(id="t", issue=issue, patch=patch, test_patch=test_patch)
    return run_checks(record, t).finding(check)


def test_default_thresholds():
    assert Thresholds() == Thresholds(6, 0.2, 0.34, 0.5, 0.5, 40, 8, False)


def test_evidence_names_only_the_added_lines_found_in_the_issue():
    issue = 'Fix:\n```python\nif unit == "K" and value is not None:\n```'
    f = _finding("solution_leakage", issue)
    assert f.evidence == ['added line present in issue code: if unit == "K" and value is not None:']
    assert f.metrics["lines_in_issue"] == 1
    assert 0 < f.score < 1


def test_test_files_in_the_gold_patch_are_not_solution_code():
    test_file = (
        "--- a/tests/test_conv.py\n+++ b/tests/test_conv.py\n@@ -1,0 +1,1 @@\n"
        "+    assert to_celsius(273.15, unit_name) == expected_value\n"
    )
    issue = "```python\nassert to_celsius(273.15, unit_name) == expected_value\n```"
    f = _finding("solution_leakage", issue, patch=SOURCE + test_file)
    assert f.score == 0.0
    assert not f.flagged


def test_a_line_removed_from_a_gold_patch_test_file_does_not_hide_new_code():
    # The source line is new code even though a test file of the gold patch
    # removes a line with the same tokens.
    test_file = (
        "--- a/tests/test_conv.py\n+++ b/tests/test_conv.py\n@@ -1,1 +1,0 @@\n"
        '-    if unit == "K" and value is not None:\n'
    )
    issue = '```python\nif unit == "K" and value is not None:\n```'
    alone = _finding("solution_leakage", issue)
    f = _finding("solution_leakage", issue, patch=SOURCE + test_file)
    assert f.score == alone.score > 0


def test_solution_leakage_flags_at_exactly_the_threshold():
    issue = 'Fix:\n```python\nif unit == "K" and value is not None:\n```'
    score = _finding("solution_leakage", issue).score
    assert _finding("solution_leakage", issue, solution_leakage=score).flagged
    assert not _finding("solution_leakage", issue, solution_leakage=score + 1e-9).flagged


def test_test_leakage_flags_at_exactly_the_threshold():
    test_patch = (
        "--- a/tests/test_conv.py\n+++ b/tests/test_conv.py\n@@ -1,0 +1,3 @@\n"
        "+def test_kelvin():\n+    pass\n+def test_rankine():\n"
    )
    f = _finding("test_leakage", "test_kelvin fails", test_patch=test_patch, test_leakage=0.5)
    assert f.score == 0.5
    assert f.flagged
    assert not _finding(
        "test_leakage", "test_kelvin fails", test_patch=test_patch, test_leakage=0.51
    ).flagged


def test_should_without_an_actual_side_is_not_expected_against_actual():
    f = _finding("underspecification", "Kelvin input should be accepted.")
    assert f.metrics["has_expected_actual"] == 0
    f = _finding("underspecification", "Kelvin input returns zero.")
    assert f.metrics["has_expected_actual"] == 0
    f = _finding("underspecification", "Kelvin input should be accepted, but it returns zero.")
    assert f.metrics["has_expected_actual"] == 1


def test_forty_tokens_is_long_enough_and_thirty_nine_is_short():
    words = " ".join(f"w{i}" for i in range(40))
    assert _finding("underspecification", words).metrics["tokens"] == 40
    assert not any(m.startswith("short") for m in _finding("underspecification", words).evidence)
    short = " ".join(f"w{i}" for i in range(39))
    assert any(
        m.startswith("short: 39 tokens") for m in _finding("underspecification", short).evidence
    )


def test_underspecification_flags_at_exactly_half():
    # A reproduction and an error, no expected-against-actual wording, short.
    issue = "Steps to reproduce: call it.\nValueError: bad unit"
    f = _finding("underspecification", issue)
    assert f.score == 0.5
    assert f.flagged


def test_links_beside_a_code_block_score_one_half():
    issue = "See https://example.org/log for details.\n```python\nto_celsius(1, 'K')\n```"
    f = _finding("external_links", issue)
    assert f.score == 0.5
    assert not f.flagged


def test_links_beside_error_text_score_one_half_and_links_alone_one():
    f = _finding("external_links", "See https://example.org/log\nValueError: bad unit")
    assert f.score == 0.5
    f = _finding("external_links", "See https://example.org/log for details.")
    assert f.score == 1.0
    assert f.flagged


def test_scope_gap_flags_at_exactly_half():
    patch = (
        "--- a/pkg/conv.py\n+++ b/pkg/conv.py\n@@ -1,0 +1,2 @@\n"
        "+def to_kelvin(value):\n+def to_rankine(value):\n"
    )
    f = _finding("scope_gap", "to_kelvin is missing", patch=patch)
    assert f.score == 0.5
    assert f.flagged


def test_test_definitions_more_than_four_columns_deeper_are_skipped():
    test_patch = (
        "--- a/tests/test_conv.py\n+++ b/tests/test_conv.py\n@@ -1,0 +1,9 @@\n"
        "+def test_top():\n"
        "+    pass\n"
        "+class TestConv:\n"
        "+    def test_method(self):\n"
        '+        src = """\n'
        "+     def test_five():\n"
        "+        def test_eight():\n"
        "+            pass\n"
        '+        """\n'
    )
    issue = "test_top test_method test_five test_eight"
    f = _finding("test_leakage", issue, test_patch=test_patch)
    assert f.evidence == [
        "issue names the added test: test_top",
        "issue names the added test: test_method",
    ]
    assert f.metrics["test_names"] == 2
