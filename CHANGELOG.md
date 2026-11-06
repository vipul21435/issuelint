# Changelog

## 0.1.0 - 2026-11-06

First release.

### Added

- Task records from JSONL, JSON (a list, or one object per line) or Parquet,
  in the plain layout (`id`, `issue`, `patch`, `test_patch`, `hints`) or the
  SWE-bench layout (`instance_id`, `problem_statement`, `patch`,
  `test_patch`, `hints_text`); duplicate ids are rejected; `--limit` and
  `--with-hints`.
- Plain and `diff --git` multi-file diffs are split by file, and the
  test-path rule separates test files from the gold patch.
- Issue code is read from fenced blocks (including `~~~` and unclosed
  fences, and fences marked `diff` or `patch`) and from unfenced unified
  diffs, in linear time.
- Six checks, each with a score in [0, 1], a flag, evidence lines and the
  counts behind the score: solution leakage, test leakage, location hints
  (reported, never flagged), underspecification signals, dependence on
  external links, scope gap.
- Solution leakage ignores moved lines, traceback source lines and
  punctuation-heavy n-grams, with `--ngram` to set the n-gram length.
- Test leakage reads test names from the test patch (Python, JavaScript and
  TypeScript, Rust, Go) or from `FAIL_TO_PASS` when the record has it.
- Location hints match file paths as whole names.
- Scope gap reports names the tests rely on that the gold patch adds and the
  issue never mentions.
- `issuelint check` prints a table, per-task explanations with `--explain`
  and per-check shares with example ids, and writes JSON, CSV or Markdown.
- `issuelint agree` reports the AUC, with a bootstrap interval, of every
  score and count against a numeric human label per task.
- Bad input (malformed or undecodable files, out-of-range options,
  unwritable outputs, repeated ids in a labels file) exits 2 with a
  one-line error.
- A `py.typed` marker, so the package's type hints are visible to checkers.
- `examples/swebench_analysis.py` and the measured results on SWE-bench Lite,
  Verified, the SWE-bench test split and SWE-Bench+, in the README and
  `docs/results.md`.

### Known limitations

See the Limitations section of the README: overlap is read on code tokens
only, underspecification is a weak screen, and nothing is executed.
