from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from issuelint.cli import main
from issuelint.patch import parse_patch
from issuelint.records import RecordError, load_records, record_from_dict
from issuelint.text import code_blocks, inline_code, mentions_path, ngrams, tokens, urls

PATCH = """diff --git a/pkg/a.py b/pkg/a.py
index 1..2 100644
--- a/pkg/a.py
+++ b/pkg/a.py
@@ -1,3 +1,4 @@ class Widget:
     def render(self):
-        return 1
+        # comment
+        return 2
diff --git a/tests/test_a.py b/tests/test_a.py
--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -1,0 +1,2 @@
+def test_render():
+    assert Widget().render() == 2
diff --git a/pkg/new.py b/pkg/new.py
new file mode 100644
--- /dev/null
+++ b/pkg/new.py
@@ -0,0 +1,2 @@
+def fresh():
+    return 3
"""


def test_parse_patch_files_lines_and_identifiers():
    p = parse_patch(PATCH)
    assert p.paths == ["pkg/a.py", "tests/test_a.py", "pkg/new.py"]
    assert [f.is_test for f in p.files] == [False, True, False]
    assert p.added_lines(include_tests=False) == [
        "        # comment",
        "        return 2",
        "def fresh():",
        "    return 3",
    ]
    assert p.removed_lines() == ["        return 1"]
    assert p.changed_identifiers() == ["Widget", "fresh"]
    assert p.changed_identifiers(include_tests=True) == ["Widget", "test_render", "fresh"]


def test_parse_patch_without_git_header():
    p = parse_patch(
        "--- a/x.js\n+++ b/x.js\n@@ -1 +1 @@\n-export function f() {}\n+export function g() {}\n"
    )
    assert p.paths == ["x.js"]
    assert p.changed_identifiers() == ["g", "f"]


PLAIN_DIFF = """--- a/pkg/one.py
+++ b/pkg/one.py
@@ -1,2 +1,2 @@
 def one():
-    return 1
+    return 2
--- a/pkg/two.py
+++ b/pkg/two.py
@@ -1 +1 @@
-    x = 1
+    x = 2
--- a/tests/test_two.py
+++ b/tests/test_two.py
@@ -1,0 +1,2 @@
+def test_two():
+    assert two() == 2
--- a/pkg/gone.py
+++ /dev/null
@@ -1 +0,0 @@
--- not a header
"""


def test_parse_plain_multi_file_diff_splits_files():
    p = parse_patch(PLAIN_DIFF)
    assert p.paths == ["pkg/one.py", "pkg/two.py", "tests/test_two.py", "pkg/gone.py"]
    assert [f.added for f in p.files] == [
        ["    return 2"],
        ["    x = 2"],
        ["def test_two():", "    assert two() == 2"],
        [],
    ]
    assert [f.removed for f in p.files] == [
        ["    return 1"],
        ["    x = 1"],
        [],
        ["-- not a header"],
    ]
    assert [f.is_test for f in p.files] == [False, False, True, False]
    assert p.added_lines(include_tests=False) == ["    return 2", "    x = 2"]


def test_parse_patch_hunk_with_wrong_count_ends_at_next_file():
    p = parse_patch(
        "--- a/a.py\n+++ b/a.py\n@@ -1 +1,3 @@\n+x = 1\n"
        "--- a/b.py\n+++ b/b.py\n@@ -1 +1 @@\n+y = 2\n"
    )
    assert p.paths == ["a.py", "b.py"]
    assert [f.added for f in p.files] == [["x = 1"], ["y = 2"]]
    assert [f.removed for f in p.files] == [[], []]


def test_parse_bare_hunk_with_no_newline_markers():
    p = parse_patch(
        "@@ -1 +1 @@\n-x = 1\n\\ No newline at end of file\n+x = 2\n\\ No newline at end of file\n"
    )
    assert p.paths == ["<unknown>"]
    assert p.files[0].removed == ["x = 1"]
    assert p.files[0].added == ["x = 2"]


def test_parse_patch_blank_context_line_without_space():
    p = parse_patch("--- a/a.py\n+++ b/a.py\n@@ -1,3 +1,3 @@\n x = 1\n\n-y = 1\n+y = 2\n")
    assert p.files[0].added == ["y = 2"]
    assert p.files[0].removed == ["y = 1"]


def test_parse_empty_patch():
    p = parse_patch("")
    assert p.files == []
    assert p.changed_identifiers() == []


def test_text_helpers():
    issue = (
        "Run `foo()`:\n\n```py\nx = 1\n```\n\n    y = 2\n    z = 3\n\nsee https://a.invalid/p, ok"
    )
    assert code_blocks(issue) == ["x = 1", "    y = 2\n    z = 3"]
    assert inline_code(issue) == ["foo()"]
    assert urls(issue) == ["https://a.invalid/p"]
    assert tokens("a.b(1) != c") == ["a", ".", "b", "(", "1", ")", "!=", "c"]
    assert ngrams(["a", "b", "c"], 2) == [("a", "b"), ("b", "c")]
    assert ngrams(["a"], 2) == []
    with pytest.raises(ValueError, match="positive"):
        ngrams(["a"], 0)
    assert mentions_path("bug in units/convert.py", "src/units/convert.py") == "units/convert.py"
    assert mentions_path("bug in convert.py", "src/units/convert.py") == "convert.py"
    assert mentions_path("bug somewhere", "src/units/convert.py") is None


def test_record_layouts():
    plain = record_from_dict({"id": "a", "issue": "i", "patch": "p", "test_patch": "t"})
    swe = record_from_dict(
        {"instance_id": "a", "problem_statement": "i", "patch": "p", "test_patch": "t"}
    )
    assert plain == swe
    assert record_from_dict({"issue": "i", "patch": "p"}, default_id="row-3").id == "row-3"
    assert record_from_dict({"issue": "i", "patch": "p"}, default_id="x").test_patch == ""
    with pytest.raises(RecordError, match="needs an issue"):
        record_from_dict({"id": "a", "patch": "p"})
    with pytest.raises(RecordError, match="no id"):
        record_from_dict({"issue": "i", "patch": "p"})


def test_load_jsonl_and_json(tmp_path: Path):
    rows = [{"id": "a", "issue": "i", "patch": "p"}, {"id": "b", "issue": "j", "patch": "q"}]
    jl = tmp_path / "r.jsonl"
    jl.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n")
    js = tmp_path / "r.json"
    js.write_text(json.dumps(rows))
    assert [r.id for r in load_records(jl)] == ["a", "b"]
    assert [r.id for r in load_records(js)] == ["a", "b"]
    single = tmp_path / "one.json"
    single.write_text(json.dumps(rows[0]))
    assert [r.id for r in load_records(single)] == ["a"]
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json}\n")
    with pytest.raises(RecordError, match="line 1"):
        load_records(bad)
    arr = tmp_path / "arr.jsonl"
    arr.write_text("[1]\n")
    with pytest.raises(RecordError, match="expected an object"):
        load_records(arr)
    with pytest.raises(RecordError, match="unsupported"):
        load_records(tmp_path / "r.txt")


SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample.jsonl"


def test_cli_table_json_csv_and_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    out_json = tmp_path / "o.json"
    out_csv = tmp_path / "o.csv"
    code = main(["check", str(SAMPLE), "--explain", "--json", str(out_json), "--csv", str(out_csv)])
    assert code == 0
    text = capsys.readouterr().out
    assert "leaky-solution" in text
    assert "FLAG solution_leakage" in text
    assert "4 task(s)" in text
    data = json.loads(out_json.read_text())
    assert [d["id"] for d in data] == ["clean-1", "leaky-solution", "leaky-tests", "vague-link"]
    assert data[0]["flags"] == []
    assert data[1]["flags"] == ["solution_leakage"]
    assert data[2]["flags"] == ["test_leakage"]
    assert set(data[3]["flags"]) == {"underspecification", "external_links", "scope_gap"}
    rows = list(csv.DictReader(out_csv.read_text().splitlines()))
    assert len(rows) == 4
    assert rows[1]["solution_leakage_flag"] == "1"
    assert rows[0]["solution_leakage_flag"] == "0"
    assert main(["check", str(SAMPLE), "--quiet", "--fail-on-flag"]) == 1
    assert "clean-1  " not in capsys.readouterr().out.splitlines()[0]


def test_cli_missing_file_and_version(capsys: pytest.CaptureFixture[str]):
    assert main(["check", "/nonexistent/file.jsonl"]) == 2
    assert "issuelint:" in capsys.readouterr().err
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("issuelint 0.1.0")


def test_cli_thresholds_are_flags(capsys: pytest.CaptureFixture[str]):
    assert main(["check", str(SAMPLE), "--quiet", "--scope-gap", "0", "--fail-on-flag"]) == 1
    assert "scope_gap            flagged    4" in capsys.readouterr().out


def test_hints_are_read_only_when_asked(tmp_path: Path):
    from issuelint.checks import Thresholds, run_checks

    row = {
        "instance_id": "org__repo-1",
        "problem_statement": "Something is off with the converter.",
        "hints_text": "See https://example.org/thread for the details.",
        "patch": "",
        "test_patch": "",
    }
    record = record_from_dict(row)
    assert record.hints.startswith("See")
    assert record.issue_text() == record.issue
    plain = run_checks(record)
    hinted = run_checks(record, Thresholds(with_hints=True))
    assert plain.finding("external_links").score == 0.0
    assert hinted.finding("external_links").score == 1.0


def test_parquet_input_and_limit(tmp_path: Path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    rows = [
        {"instance_id": f"org__repo-{i}", "problem_statement": "x", "patch": "", "test_patch": ""}
        for i in range(3)
    ]
    path = tmp_path / "split.parquet"
    pq.write_table(pa.Table.from_pylist(rows), path)
    records = load_records(path)
    assert [r.id for r in records] == ["org__repo-0", "org__repo-1", "org__repo-2"]
    assert len(load_records(path, limit=2)) == 2
    assert main(["check", str(path), "--quiet", "--limit", "1"]) == 0


def test_duplicate_ids_are_rejected(tmp_path: Path):
    path = tmp_path / "dup.jsonl"
    row = json.dumps({"id": "a", "issue": "x", "patch": ""})
    path.write_text(f"{row}\n{row}\n", encoding="utf-8")
    with pytest.raises(RecordError, match="duplicate"):
        load_records(path)


def test_quotes_are_one_token_and_punctuation_grams_are_dropped():
    from issuelint.text import code_ngrams, informative

    assert tokens("f('a')") == tokens('f("a")')
    assert not informative((")", ")", ",", "0", "]", ")"))
    assert informative(("x", ".", "y", "(", "z", ")"))
    assert code_ngrams(tokens(") ) ) ] ] ]"), 3) == []


def test_check_stats_and_markdown(tmp_path: Path):
    from issuelint.checks import run_all
    from issuelint.report import check_stats, to_markdown

    reports = run_all(load_records(SAMPLE))
    stats = {s.check: s for s in check_stats(reports, examples=2)}
    assert stats["solution_leakage"].flagged == 1
    assert stats["solution_leakage"].examples == ["leaky-solution"]
    assert stats["location_hints"].flagged == 0
    assert stats["location_hints"].nonzero == 3
    assert len(stats["location_hints"].examples) == 2
    assert 0.0 <= stats["scope_gap"].nonzero_share <= 1.0
    md = to_markdown(reports)
    assert md.startswith("4 tasks.")
    assert "| `location_hints` | never flagged |" in md
    out = tmp_path / "s.md"
    assert main(["check", str(SAMPLE), "--quiet", "--examples", "1", "--markdown", str(out)]) == 0
    assert "`leaky-solution`" in out.read_text(encoding="utf-8")


def test_traceback_source_lines_are_dropped():
    from issuelint.text import drop_traceback_source

    text = "\n".join(
        [
            "Traceback (most recent call last):",
            '  File "pkg/a.py", line 3, in f',
            "    return compute(x) / total",
            'INTERNALERROR>   File "saferepr.py", line 23, in g',
            "INTERNALERROR>     exc_info, obj.__class__.__name__, id(obj)",
            "    349 vmin, vmax = axis.convert_units((vmin, vmax))",
            "--> 351 b = forward(vmax) - forward(vmin)",
            ">       assert helper() == 2",
            "ZeroDivisionError: division by zero",
            "x = compute(1)",
        ]
    )
    kept = drop_traceback_source(text)
    assert "compute(x) / total" not in kept
    assert "id(obj)" not in kept
    assert "convert_units" not in kept
    assert "forward(vmax)" not in kept
    assert "helper()" not in kept
    assert "ZeroDivisionError" in kept
    assert "x = compute(1)" in kept


def test_explain_flagged_only(capsys):
    assert main(["check", str(SAMPLE), "--quiet", "--explain", "--flagged-only"]) == 0
    out = capsys.readouterr().out
    assert "leaky-solution" in out
    assert "\nclean-1\n" not in out


@pytest.mark.parametrize(
    ("content", "message"),
    [("{not json", "not JSON"), ("[1, 2]", "expected an object, got int")],
)
def test_bad_json_files_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str, message: str
):
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(RecordError, match=message):
        load_records(path)
    assert main(["check", str(path), "--quiet"]) == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "flags",
    [
        ["--ngram", "0"],
        ["--limit", "-1"],
        ["--examples", "-2"],
        ["--max-evidence", "-1"],
        ["--min-issue-tokens", "x"],
    ],
)
def test_out_of_range_counts_exit_2(capsys: pytest.CaptureFixture[str], flags: list[str]):
    with pytest.raises(SystemExit) as exc:
        main(["check", str(SAMPLE), "--quiet", *flags])
    assert exc.value.code == 2
    assert flags[0] in capsys.readouterr().err


def test_fences_are_split_line_by_line():
    from issuelint.text import split_fences

    issue = "a\n  ```py\nx = 1\ny = 2```\nb ```` c\n~~~\nz\n~~~\nend"
    blocks, outside = split_fences(issue)
    assert blocks == ["x = 1\ny = 2", "z"]
    assert outside == ["a", "", "b ```` c", "", "end"]
    # A backtick opener whose info string holds a backtick is a code span.
    assert split_fences("```x = 1``` here") == ([], ["```x = 1``` here"])


def test_backtick_heavy_text_is_linear():
    import time

    start = time.perf_counter()
    code_blocks("```" * 70_000)
    inline_code("```" * 70_000)
    assert time.perf_counter() - start < 1.0


@pytest.mark.parametrize("option", ["--json", "--csv", "--markdown"])
def test_unwritable_output_exits_2_before_any_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], option: str
):
    target = tmp_path / "missing" / "out.txt"
    assert main(["check", str(SAMPLE), "--quiet", option, str(target)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "missing" in captured.err
    assert len(captured.err.strip().splitlines()) == 1


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("bad.jsonl", b'\xff\xfe{"id": 1}\n', "UTF-8"),
        ("bad.json", b"\xff\xfe[]", "UTF-8"),
        ("bad.parquet", b"not parquet", "Parquet"),
    ],
)
def test_undecodable_input_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str, content: bytes, message: str
):
    path = tmp_path / name
    path.write_bytes(content)
    assert main(["check", str(path), "--quiet"]) == 2
    err = capsys.readouterr().err
    assert message in err
    assert len(err.strip().splitlines()) == 1


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[1, 2]", "item 1"),
        ('[{"id": "a"}]', "item 1"),
        ('[{"id": "a", "findings": [{"check": "x"}]}]', "item 1"),
        ("{bad", "not JSON"),
    ],
)
def test_agree_rejects_malformed_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str, message: str
):
    findings = tmp_path / "f.json"
    findings.write_text(content, encoding="utf-8")
    labels = tmp_path / "l.csv"
    labels.write_text("instance_id,l\na,1\n", encoding="utf-8")
    assert main(["agree", str(findings), str(labels), "--label", "l"]) == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "flags",
    [
        ["--solution-leakage", "nan"],
        ["--test-leakage", "-1"],
        ["--underspecification", "1.5"],
        ["--scope-gap", "inf"],
        ["--solution-leakage", "x"],
    ],
)
def test_out_of_range_shares_exit_2(capsys: pytest.CaptureFixture[str], flags: list[str]):
    with pytest.raises(SystemExit) as exc:
        main(["check", str(SAMPLE), "--quiet", *flags])
    assert exc.value.code == 2
    assert flags[0] in capsys.readouterr().err


def test_share_bounds_are_accepted(capsys: pytest.CaptureFixture[str]):
    assert main(
        ["check", str(SAMPLE), "--quiet", "--solution-leakage", "1", "--test-leakage", "0"]
    ) in (0, 1)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "x"])
def test_agree_positive_at_must_be_finite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], value: str
):
    with pytest.raises(SystemExit) as exc:
        main(["agree", "f.json", "l.csv", "--label", "l", "--positive-at", value])
    assert exc.value.code == 2
    assert "--positive-at" in capsys.readouterr().err
