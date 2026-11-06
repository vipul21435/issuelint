# issuelint

Check issue-to-fix task records for solution leaks, test leaks, location hints,
underspecification, external links and scope gaps before they become benchmark items.

## Why this is hard

An issue-to-fix task is only a fair test of a coding agent when the issue
text says what is wrong without saying how to fix it or how it will be
checked. An issue that pastes the fix, names the new test, or links to a
thread that holds the real description measures copying rather than
debugging; an issue with no reproduction, no expected-against-actual and no
error text leaves the task underdetermined and the gold patch becomes one
of many defensible answers. None of these properties is visible from the
patch or the issue alone: each check has to line the two up, and the useful
output is the evidence (which line, which name) rather than a verdict.

## Install

```
pip install git+https://github.com/vipul21435/issuelint
```

Python 3.10 or later, no dependencies outside the standard library. Reading
the Parquet files that SWE-bench splits are published in needs `pyarrow`:

```
pip install "issuelint[parquet] @ git+https://github.com/vipul21435/issuelint"
```

## Quickstart

Input is a `.jsonl` (one object per line), `.json` or `.parquet` file. Each
record has an issue, a gold patch and, optionally, a test patch and hints;
both the plain keys (`id`, `issue`, `patch`, `test_patch`, `hints`) and the
SWE-bench keys (`instance_id`, `problem_statement`, `patch`, `test_patch`,
`hints_text`) are read, so a SWE-bench split downloaded from Hugging Face is
checked as it is.

```
$ issuelint check examples/sample.jsonl
id              solution     tests  location underspec     links     scope  flags
clean-1            0.00      0.00      0.50      0.00      0.00      0.00   0
leaky-solution     1.00*     0.00      0.50      0.00      0.00      0.00   1
leaky-tests        0.00      1.00*     0.50      0.00      0.00      0.00   1
vague-link         0.00      0.00      0.00      1.00*     1.00*     1.00*  3

4 task(s)
  solution_leakage     flagged    1 ( 25.0%)  nonzero    1 ( 25.0%)  mean score 0.250
  test_leakage         flagged    1 ( 25.0%)  nonzero    1 ( 25.0%)  mean score 0.250
  location_hints       flagged    0 (  0.0%)  nonzero    3 ( 75.0%)  mean score 0.375
  underspecification   flagged    1 ( 25.0%)  nonzero    1 ( 25.0%)  mean score 0.250
  external_links       flagged    1 ( 25.0%)  nonzero    1 ( 25.0%)  mean score 0.250
  scope_gap            flagged    1 ( 25.0%)  nonzero    1 ( 25.0%)  mean score 0.250
```

A `*` marks a flagged check. `--explain` prints the evidence behind every
score; this is the block for one task:

```
$ issuelint check examples/sample.jsonl --explain --quiet
leaky-tests
       solution_leakage     0.00  0 of 9 added-code 6-grams appear in the issue's code
  FLAG test_leakage         1.00  3 of 3 (1 test names, 2 assertions) already in the issue
         - issue names the added test: test_kelvin_and_celsius
         - issue contains the added assertion: assert to_celsius(273.15, "K") == 0
         - issue contains the added assertion: assert to_celsius(20, "C") == 20
       location_hints       0.50  1 of 2 (1 files, 1 identifiers) named in the issue
         - issue names changed identifier to_celsius
       underspecification   0.00  0 of 4 specification signals missing
       external_links       0.00  no links
       scope_gap            0.00  0 of 1 changed identifiers never mentioned in the issue
```

`--json FILE` and `--csv FILE` write the same findings as data (the JSON
also carries the counts behind every score); `--markdown FILE` writes the
per-check shares with example ids; `--examples N` adds up to N example ids
per check to the printed summary; `--with-hints` reads the hints together
with the issue; `--limit N` checks the first N records; `--fail-on-flag`
exits 1 when any check other than `location_hints` flags a task. Every
cut-off is a flag (`--ngram`, `--solution-leakage`, `--test-leakage`,
`--underspecification`, `--scope-gap`, `--min-issue-tokens`,
`--max-evidence`); `issuelint check --help` lists the defaults.

`issuelint agree FINDINGS.json LABELS.csv --label COLUMN --positive-at X`
compares every score and count in a `check --json` file with a numeric
human label per task (see "Agreement with human labels" below).

From Python:

```python
from issuelint.checks import run_all
from issuelint.records import load_records
from issuelint.report import explain

reports = run_all(load_records("examples/sample.jsonl"))
print(explain(reports[1]))
```

`examples/run_sample.py` does the same and prints the flagged tasks and the
Markdown summary; `examples/swebench_analysis.py` produces the results
section below.

## How it works

The gold patch and the test patch are parsed as unified diffs into files,
added lines, removed lines and hunk context headers. Paths under `tests/`,
`test/`, `__tests__/`, `spec/` or named `test_*`, `*_test.*`, `*.test.*`,
`*.spec.*` count as test files. Issue code is the content of fenced blocks,
indented blocks of two or more lines, and single-backtick spans. Tokens are
identifiers, numbers and punctuation with whitespace dropped, so formatting
differences do not break a match.

Every score is a ratio in [0, 1] and the flag is `score >= threshold`:

| check | score | default threshold |
| --- | --- | --- |
| `solution_leakage` | share of the token n-grams (n = 6) of the gold patch's added non-test code lines that also occur in the issue's code; evidence lists added lines whose every n-gram is in the issue | 0.2 |
| `test_leakage` | share of (test names + assertion lines) the test patch adds that the issue names (name as a whole word) or contains (every n-gram of the assertion) | 0.34 |
| `location_hints` | share of (changed non-test files + changed identifiers) the issue names; a file counts when its path, a path suffix or its basename appears | never flagged |
| `underspecification` | missing signals out of four: a reproduction (a code block or words such as "reproduce", "steps to"), expected-against-actual wording, error text (a traceback, exception or error name), and length of at least 40 tokens | 0.5 |
| `external_links` | 1.0 when the issue has links and no code block or error text of its own, 0.5 with links beside its own evidence, 0 without links | 1.0 |
| `scope_gap` | share of identifiers the gold patch changes (hunk context definitions plus added or removed `def`, `class`, `function`, `fn`, `struct`, `func` and similar lines in non-test files) that the issue never mentions | 0.5 |

Comment lines and blank lines are dropped before n-grams are built, and
patches that add less than one n-gram score 0 rather than raising.

## Results on real public data

Not run yet in this version. The next step is SWE-bench Lite's test split,
after reading its licence on the dataset card; this section will then carry
the share of items each check flags, the exact command, and instance ids as
examples.

## Limitations

- The definition patterns cover Python, JavaScript and TypeScript, Rust and
  Go. Other languages still get the n-gram checks, but `scope_gap` and the
  identifier half of `location_hints` see only hunk context headers.
- Underspecification is keyword based. An issue can describe a reproduction
  in words the patterns do not match, and an issue can match them without
  being specific.
- `solution_leakage` sees overlap of code tokens. A fix described in prose
  ("add a branch for kelvin") scores 0 even though it gives the solution
  away.
- `test_leakage` reads test names from `def test_*`, `it("...")`,
  `test("...")`, `fn test_*` and `func Test*`; parametrised or generated
  tests are missed.
- No model of what a test checks, no execution, no comparison with a
  published leakage analysis yet.

## Related tools

- https://github.com/vipul21435/taskgate: review gates for pull requests that add benchmark tasks.
- https://github.com/vipul21435/datasieve: filtering of training and evaluation records.
- https://github.com/vipul21435/verifybench: checks on benchmark verifiers.
- https://github.com/vipul21435/patchmin: minimal patches for issue-to-fix tasks.
- https://github.com/vipul21435/taskledger: a ledger of task records and their state.

## Licence

MIT.

Built by Vipul Raj Jha · https://vipul21435.github.io
