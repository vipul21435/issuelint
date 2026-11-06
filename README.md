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

Each check lines the issue text up against the gold patch or the test patch
and returns a score in [0, 1], a flag (`score >= threshold`), the counts
behind the score and evidence lines. Nothing is learned; every rule is below.

**Parsing.** Patches are parsed as unified diffs into files, added lines,
removed lines and hunk context headers. Paths under `tests/`, `test/`,
`__tests__/`, `spec/` or named `test_*`, `*_test.*`, `*.test.*`, `*.spec.*`
count as test files. Issue code is the content of fenced blocks, indented
blocks of two or more lines, and single-backtick spans. Tokens are
identifiers, numbers and punctuation with whitespace dropped and single and
double quotes merged, so reformatting does not break a match.

**Why these six.** The SWE-bench paper (Jimenez et al., "SWE-bench: Can
Language Models Resolve Real-World GitHub Issues?", ICLR 2024,
[arXiv 2310.06770](https://arxiv.org/abs/2310.06770)) builds tasks from an
issue, the fix in the linked pull request and the tests that pull request
adds; every check here reads one pair out of those three texts. The SWE-bench
Verified annotation instructions (published by OpenAI with SWE-bench
Verified, [PDF](https://cdn.openai.com/introducing-swe-bench-verified/swe-b-annotation-instructions.pdf))
ask annotators whether the issue is well specified "without further
information", tell them not to follow external links, and name tests that
rely on "a new function, variable name, or error message" introduced by the
gold patch and absent from the issue as the most common test problem.
SWE-Bench+ (Aleithan et al., "SWE-Bench+: Enhanced Coding Benchmark for
LLMs", [arXiv 2410.06992](https://arxiv.org/abs/2410.06992)) defines
solution leakage as the fix being given in the issue or its comments. The
SWE-bench Lite filters ([swebench.com/lite](https://www.swebench.com/lite.html))
drop issues with external hyperlinks or fewer than 40 words, which is where
`external_links` and the default `--min-issue-tokens 40` come from.

| check | score | default threshold |
| --- | --- | --- |
| `solution_leakage` | share of the token n-grams (n = 6) of the gold patch's new code lines that also occur in the issue's code | 0.2 |
| `test_leakage` | share of (test names + assertion lines) the test patch adds that the issue names (name as a whole word) or contains (every n-gram of the assertion) | 0.34 |
| `location_hints` | share of (changed non-test files + changed identifiers) the issue names; a file counts when its path, a path suffix or its basename appears | never flagged |
| `underspecification` | missing signals out of four: a reproduction (a code block or words such as "reproduce", "steps to"), expected-against-actual wording, error text (a traceback, exception or error name), and a length of at least 40 tokens | 0.5 |
| `external_links` | 1.0 when the issue has links and no code block or error text of its own, 0.5 with links beside its own evidence, 0 without links | 1.0 |
| `scope_gap` | share of identifiers the gold patch changes (hunk context definitions plus added or removed `def`, `class`, `function`, `fn`, `struct`, `func` and similar lines in non-test files) that the issue never mentions | 0.5 |

Details that matter on real issues:

- *Solution leakage* counts only new code. Comment and blank lines are
  dropped; an added line whose tokens equal a removed line's (moved or
  re-indented code) is dropped; n-grams in which fewer than half of the
  tokens are identifiers (`) ) , 0 ] )`) are dropped. On the issue side, the
  source lines a traceback quotes (the line after `File "...", line N`,
  IPython's numbered lines, pytest's `>` lines) are dropped, because they
  show the code before the fix. With `S` the n-grams of the new code and `I`
  those of the issue's code, the score is `|{g in S : g in I}| / |S|`, with
  repeats in `S` counted.
- *Test leakage* matches whole assertion lines, so all n-grams of an
  assertion must occur in the issue, not only the identifier-heavy ones.
- *Scope gap* also reports, without changing its score,
  `tests_use_new_names`: identifiers (three characters or more) on the gold
  patch's added code lines and on none of its removed lines, used on the
  test patch's added lines, and absent from the issue. This is the test
  problem the Verified instructions describe.
- *Location hints* are reported and never flagged: naming the file or the
  function is normal in a good bug report, but it is worth knowing how much
  of the search the issue already did.
- `--with-hints` appends SWE-bench's `hints_text` (issue comments made before
  the fix) to the issue, which matches the SWE-Bench+ definition of leakage
  in "the issue or its comments".

**Agreement with human labels.** `issuelint agree` reads a `check --json`
file and a CSV with one numeric label per task, marks a task positive when
its label is at least `--positive-at`, and reports for every score and
count the area under the ROC curve: with `P` positives and `N` negatives
and `R` the sum of the positives' average ranks among all scores,
`AUC = (R - P(P + 1)/2) / (P N)`, the chance that a random positive scores
above a random negative (ties count one half; 0.5 is chance). The 95 %
interval is a percentile bootstrap over tasks (1000 resamples, seed 0). For
flagging checks it also prints the share flagged among positives and among
negatives.

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
