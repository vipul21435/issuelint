from __future__ import annotations

import random

import pytest

from issuelint.checks import CHECKS, Thresholds, run_checks
from issuelint.records import TaskRecord
from issuelint.text import code_blocks

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
    hidden = f.metrics["unmentioned"] + f.metrics["tests_use_new_names"] - 1
    assert f.evidence[1] == f"... {hidden} more"


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


def test_scope_gap_reports_new_names_the_tests_rely_on():
    from issuelint.records import TaskRecord

    patch = (
        "--- a/pkg/core.py\n+++ b/pkg/core.py\n@@ -1,2 +1,4 @@ def load(path):\n"
        "-    def old_helper():\n+    def parse_header(raw):\n+        return raw\n"
    )
    test_patch = (
        "--- a/tests/test_core.py\n+++ b/tests/test_core.py\n@@ -1 +1,2 @@\n"
        "+def test_header():\n+    assert parse_header(b'x') == b'x'\n"
    )
    record = TaskRecord(
        id="t",
        issue="load(path) crashes on files with a header",
        patch=patch,
        test_patch=test_patch,
    )
    f = run_checks(record).finding("scope_gap")
    assert f.metrics["tests_use_new_names"] == 1
    assert f.evidence[0].startswith("tests use parse_header")
    assert f.metrics["identifiers"] == 3
    assert f.metrics["unmentioned"] == 2


def test_tests_use_new_names_skips_keywords_and_builtins():
    patch = (
        "--- a/pkg/core.py\n+++ b/pkg/core.py\n@@ -1,1 +1,6 @@\n"
        " import os\n"
        "+from pkg.io import read_block\n"
        "+class Reader:\n"
        "+    def parse_header(self, raw):\n"
        "+        if raw is None or not isinstance(raw, bytes):\n"
        "+            return read_block(raw)\n"
    )
    test_patch = (
        "--- a/tests/test_core.py\n+++ b/tests/test_core.py\n@@ -1 +1,6 @@\n"
        "+from pkg.core import Reader\n"
        "+class TestReader:\n"
        "+    def test_header(self):\n"
        "+        if True:\n"
        "+            return None\n"
        "+        assert Reader().parse_header(bytes()) is not None\n"
    )
    issue = "Reading a file with pkg fails."
    record = TaskRecord(id="t", issue=issue, patch=patch, test_patch=test_patch)
    f = run_checks(record).finding("scope_gap")
    used = [e.split()[2].rstrip(",") for e in f.evidence if e.startswith("tests use ")]
    assert used == ["Reader", "parse_header"]
    assert f.metrics["tests_use_new_names"] == 2


def test_tests_use_new_names_skips_go_keywords():
    patch = (
        "--- a/conv/conv.go\n+++ b/conv/conv.go\n@@ -1,1 +1,7 @@\n"
        " package conv\n"
        "+func ParseUnit(s string) (Unit, error) {\n"
        "+\tvar err error\n"
        '+\tif s == "" {\n'
        "+\t\treturn nil, err\n"
        "+\t}\n"
        "+}\n"
    )
    test_patch = (
        "--- a/conv/conv_test.go\n+++ b/conv/conv_test.go\n@@ -1,1 +1,6 @@\n"
        " package conv\n"
        "+func TestParseUnit(t *testing.T) {\n"
        '+\tif _, err := ParseUnit(""); err != nil {\n'
        "+\t\treturn\n"
        "+\t}\n"
        "+}\n"
    )
    record = TaskRecord(id="t", issue="Empty unit text.", patch=patch, test_patch=test_patch)
    f = run_checks(record).finding("scope_gap")
    used = [e.split()[2].rstrip(",") for e in f.evidence if e.startswith("tests use ")]
    assert used == ["ParseUnit"]


def test_moved_code_quoted_in_a_traceback_is_not_leakage():
    from issuelint.records import TaskRecord

    patch = (
        "--- a/pkg/svm.py\n+++ b/pkg/svm.py\n@@ -1,3 +1,5 @@ def fit(self):\n"
        "-        self.dual_coef_ = sp.csr_matrix((data, indices, indptr), shape=shape)\n"
        "+        if n_sv == 0:\n+            self.dual_coef_ = sp.csr_matrix([])\n+        else:\n"
        "+            self.dual_coef_ = sp.csr_matrix((data, indices, indptr), shape=shape)\n"
    )
    issue = (
        "fit fails on empty support vectors:\n```\nTraceback (most recent call last):\n"
        '  File "svm.py", line 3, in fit\n'
        "    self.dual_coef_ = sp.csr_matrix((data, indices, indptr), shape=shape)\n"
        "ZeroDivisionError: float division by zero\n```\n"
    )
    f = run_checks(TaskRecord(id="t", issue=issue, patch=patch)).finding("solution_leakage")
    assert f.metrics["shared_ngrams"] == 0
    assert not f.flagged


def test_fail_to_pass_ids_add_test_names():
    from issuelint.checks import names_from_test_ids
    from issuelint.records import RecordError, record_from_dict

    ids = [
        "lib/pkg/tests/test_fig.py::test_invalid_size[0-1]",
        "tests/test_a.py::TestCase::test_map[2-2]",
        "test_issue_10228",
        "test_squash (migrations.test_commands.SquashTests)",
        "--squashed-name specifies the new migration's name.",
    ]
    assert names_from_test_ids(ids) == [
        "test_invalid_size",
        "test_map",
        "test_issue_10228",
        "test_squash",
    ]
    row = {
        "instance_id": "a",
        "problem_statement": "test_issue_10228 fails",
        "patch": "",
        "FAIL_TO_PASS": '["test_issue_10228"]',
    }
    record = record_from_dict(row)
    assert record.fail_to_pass == ("test_issue_10228",)
    f = run_checks(record).finding("test_leakage")
    assert f.score == 1.0
    assert record_from_dict({**row, "FAIL_TO_PASS": ["test_x"]}).fail_to_pass == ("test_x",)
    with pytest.raises(RecordError, match="JSON"):
        record_from_dict({**row, "FAIL_TO_PASS": "not json"})
    with pytest.raises(RecordError, match="list"):
        record_from_dict({**row, "FAIL_TO_PASS": "{}"})


def test_test_names_match_whole_words_and_title_phrases():
    from issuelint.records import TaskRecord

    test_patch = (
        "--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1 +1,3 @@\n"
        "+def test_map():\n+    pass\n"
        "--- a/web/a.test.js\n+++ b/web/a.test.js\n@@ -1 +1,2 @@\n"
        "+it('renders the header', () => {});\n"
    )
    record = TaskRecord(id="t", issue="test_mapping fails", patch="", test_patch=test_patch)
    assert run_checks(record).finding("test_leakage").score == 0.0
    record = TaskRecord(
        id="t", issue="it no longer renders the header", patch="", test_patch=test_patch
    )
    assert run_checks(record).finding("test_leakage").score == 0.5


def test_assertions_shorter_than_an_ngram_stay_out_of_the_total():
    test_patch = (
        "--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1 +1,4 @@\n"
        " import a\n+    assert result\n+    self.assertEqual(\n"
        "+    assert a.parse('1 2') == [1, 2]\n"
    )
    issue = "Running `assert result` and then:\n\n    assert a.parse('1 2') == [1, 2]\n    boom\n"
    f = run_checks(TaskRecord(id="t", issue=issue, patch="", test_patch=test_patch)).finding(
        "test_leakage"
    )
    assert f.metrics["assertions"] == 1
    assert f.score == 1.0
    assert f.evidence == ["issue contains the added assertion: assert a.parse('1 2') == [1, 2]"]


# The shape of a pytest task whose issue reproduction is pasted into a
# pytester source string inside the real test.
PYTESTER_TEST_PATCH = '''diff --git a/testing/test_skipping.py b/testing/test_skipping.py
--- a/testing/test_skipping.py
+++ b/testing/test_skipping.py
@@ -1,3 +1,14 @@
+def test_reevaluate_dynamic_expr(pytester):
+    pytester.makepyfile(
+        """
+        import pytest
+
+        skip = True
+
+        @pytest.mark.skipif("skip")
+        def test_should_skip():
+            assert False
+        """
+    )
'''
PYTESTER_ISSUE = (
    "Caching of skipif string conditions gives wrong results.\n\n"
    '```py\nimport pytest\n\nskip = True\n\n@pytest.mark.skipif("skip")\n'
    "def test_should_skip():\n    assert False\n```\n"
)


def test_test_defs_inside_a_pytester_string_are_not_test_names():
    record = TaskRecord(id="t", issue=PYTESTER_ISSUE, patch="", test_patch=PYTESTER_TEST_PATCH)
    f = run_checks(record).finding("test_leakage")
    assert f.metrics["test_names"] == 1
    assert f.score == 0.0
    assert not f.flagged


def test_fail_to_pass_alone_names_the_tests_when_present():
    record = TaskRecord(
        id="t",
        issue=PYTESTER_ISSUE,
        patch="",
        test_patch=PYTESTER_TEST_PATCH.replace("+def test_reevaluate", "+def test_reeval"),
        fail_to_pass=("testing/test_skipping.py::test_reevaluate_dynamic_expr",),
    )
    f = run_checks(record).finding("test_leakage")
    assert f.metrics["test_names"] == 1
    assert f.score == 0.0


SAVE_PATCH = """diff --git a/db/creation.py b/db/creation.py
--- a/db/creation.py
+++ b/db/creation.py
@@ -1,4 +1,5 @@ class BaseDatabaseCreation:
     def deserialize_db_from_string(self, data):
         data = StringIO(data)
-        for obj in serializers.deserialize("json", data, using=self.connection.alias):
-            obj.save()
+        with transaction.atomic(using=self.connection.alias):
+            for obj in serializers.deserialize("json", data, using=self.connection.alias):
+                obj.save()
"""


def test_an_unfenced_diff_in_the_issue_is_read_as_code():
    issue = (
        "Restoring the test database can fail on foreign keys.\n\n"
        "I'm suggesting to fix it as follows:\n\n"
        "diff --git a/db/creation.py b/db/creation.py\n"
        "index bca8376..7bed2be 100644\n"
        "--- a/db/creation.py\n"
        "+++ b/db/creation.py\n"
        "@@ -1,4 +1,5 @@\n"
        "\t\tdata = StringIO(data)\n"
        '-        for obj in serializers.deserialize("json", data, using=self.connection.alias):\n'
        "-            obj.save()\n"
        "+        with transaction.atomic(using=self.connection.alias):\n"
        '+            for obj in serializers.deserialize("json", data, '
        "using=self.connection.alias):\n"
        "+                obj.save()\n"
        "\nNote the loop is unchanged.\n"
    )
    f = run_checks(TaskRecord(id="t", issue=issue, patch=SAVE_PATCH)).finding("solution_leakage")
    assert f.flagged
    assert f.score == 1.0
    assert any("transaction.atomic" in e for e in f.evidence)


@pytest.mark.parametrize(
    "fix",
    [
        "Fix:\n~~~python\nreturn int(value.strip()) if value else default_value\n~~~\n",
        "Fix:\n```python\nreturn int(value.strip()) if value else default_value\n",
    ],
    ids=["tilde-fence", "unclosed-fence"],
)
def test_tilde_and_unclosed_fences_are_code(fix: str):
    patch = (
        "--- a/conf.py\n+++ b/conf.py\n@@ -1,2 +1,2 @@ def read(value, default_value):\n"
        "-    return int(value)\n"
        "+    return int(value.strip()) if value else default_value\n"
    )
    f = run_checks(TaskRecord(id="t", issue=fix, patch=patch)).finding("solution_leakage")
    assert f.score == 1.0


DATE_PATCH = (
    "--- a/src/date.js\n+++ b/src/date.js\n@@ -1,2 +1,2 @@ function parseDate(s) {\n"
    "-  return s;\n+  return new Date(s);\n"
)


def _js_test_patch(body: str) -> str:
    return "--- a/test/date.test.js\n+++ b/test/date.test.js\n@@ -0,0 +1,3 @@\n" + body


def test_describe_blocks_are_not_test_names():
    test_patch = _js_test_patch(
        "+describe('parseDate', () => {\n+  it('handles ISO', () => {});\n+});\n"
    )
    issue = "parseDate returns a string for ISO input instead of a Date."
    f = run_checks(TaskRecord(id="t", issue=issue, patch=DATE_PATCH, test_patch=test_patch))
    leak = f.finding("test_leakage")
    assert leak.metrics["test_names"] == 1
    assert leak.score == 0.0


@pytest.mark.parametrize(
    ("issue", "score"),
    [
        ("Nothing works after upgrading to 2.0.", 0.0),
        ("The test 'works' fails after upgrading to 2.0.", 1.0),
        ("The `works` test fails after upgrading.", 1.0),
    ],
)
def test_one_word_titles_count_only_when_quoted(issue: str, score: float):
    test_patch = _js_test_patch("+it('works', () => {\n+  run();\n+});\n")
    f = run_checks(TaskRecord(id="t", issue=issue, patch=DATE_PATCH, test_patch=test_patch))
    assert f.finding("test_leakage").score == score


def test_public_names_are_not_collected_by_pytest():
    import issuelint.checks as checks

    public = [n for n in dir(checks) if not n.startswith("_") and callable(getattr(checks, n))]
    assert "names_from_test_ids" in public
    assert [n for n in public if n.startswith("test")] == []


FIX_LINES = [
    '    if unit == "K":',
    "        return value - 273.15",
    '    if unit == "C":',
    "        return value",
]


@pytest.mark.parametrize(
    "block",
    [
        "```diff\n" + "".join(f"+{line}\n" for line in FIX_LINES) + "```\n",
        "```patch\n" + "".join(f"+{line}\n" for line in FIX_LINES) + "```\n",
        "```\n@@ -10,6 +10,9 @@\n" + "".join(f"+{line}\n" for line in FIX_LINES) + "```\n",
    ],
    ids=["diff-fence", "patch-fence", "hunk-header"],
)
def test_a_fenced_diff_scores_as_the_same_code_without_prefixes(block: str):
    plain = "Fix:\n```python\n" + "\n".join(FIX_LINES) + "\n```\n"
    as_code = run_checks(TaskRecord(id="t", issue=plain, patch=PATCH)).finding("solution_leakage")
    as_diff = run_checks(TaskRecord(id="t", issue="Fix:\n" + block, patch=PATCH))
    assert as_code.score == 1.0
    assert as_diff.finding("solution_leakage").score == as_code.score


def test_a_fenced_diff_drops_removed_lines_and_keeps_other_lines():
    issue = "```diff\n--- a/x.py\n+++ b/x.py\n-old_call()\n+new_call()\n same()\nnote here\n```"
    assert code_blocks(issue) == ["new_call()\nsame()\nnote here"]
    assert code_blocks("```python\n+x\n-y\n```") == ["+x\n-y"]
