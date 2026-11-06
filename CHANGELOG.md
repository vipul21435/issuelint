# Changelog

## Unreleased

- Plain multi-file unified diffs without `diff --git` lines are split by
  file: a hunk ends when the line counts in its `@@` header are used up, or
  at the next `---`/`+++`/`@@` header triple when the counts are wrong.
- Malformed `.json` input, a `.json` list of non-objects and out-of-range
  counts (`--ngram 0`, `--limit -1`) exit 2 with a one-line error instead of
  a traceback.
- `test_leakage` leaves assertion lines shorter than one n-gram out of its
  total; results in the README and `docs/results.md` were rerun.
- The package ships a `py.typed` marker.
- `test_leakage` takes test names from `FAIL_TO_PASS` alone when the record
  has it, skips test definitions nested in strings (by indentation), ignores
  `describe()` names and counts a one-word `it()`/`test()` title only when
  the issue quotes it.
- Issue code also includes unfenced unified diffs, `~~~` fences and
  unclosed fences; fences are found line by line, in linear time.
- File path mentions match as whole names (`base.py` no longer matches
  inside `database.py`).
- Undecodable input (not UTF-8, not Parquet), output files that cannot be
  written, malformed `agree` findings, share thresholds outside 0 to 1 and
  non-finite `--positive-at` exit 2 with a one-line error.
- `agree` reads CSVs with a byte-order mark, says when no id matches, and
  rejects non-finite scores and labels.
- `test_names_from_ids` is renamed `names_from_test_ids`, so pytest does not
  collect it when imported into a test module.
- `scope_gap.tests_use_new_names` no longer counts language keywords and
  builtins (`def`, `self`, `None`, `func`, `err`).
- `agree` rejects a labels CSV that repeats a task id (a file with one row
  per annotator) instead of keeping the last row.
- Fenced blocks marked `diff` or `patch`, or holding a diff header, lose
  their `+`/space prefixes and removed lines, as unfenced diffs do.
- A `.json` file of one object per line is read as JSON Lines, and row-level
  input errors name their line, record or row.
- Results in the README and `docs/results.md` were rerun.

## 0.1.0

First version.

- Task records from JSONL, JSON or Parquet, in the plain layout (`id`,
  `issue`, `patch`, `test_patch`, `hints`) or the SWE-bench layout
  (`instance_id`, `problem_statement`, `patch`, `test_patch`, `hints_text`);
  duplicate ids are rejected; `--limit` and `--with-hints`.
- Six checks, each with a score in [0, 1], a flag, evidence lines and the
  counts behind the score: solution leakage, test leakage, location hints
  (reported, never flagged), underspecification signals, dependence on
  external links, scope gap.
- Solution leakage ignores moved lines, traceback source lines and
  punctuation-heavy n-grams; scope gap reports names the tests rely on that
  the gold patch adds and the issue never mentions.
- `issuelint check` prints a table, per-task explanations with `--explain`,
  per-check shares with example ids, and writes JSON, CSV or Markdown.
- `issuelint agree` reports the AUC, with a bootstrap interval, of every
  score and count against a numeric human label per task.
- `examples/swebench_analysis.py` and the measured results on SWE-bench
  Lite, Verified, the SWE-bench test split and SWE-Bench+.
