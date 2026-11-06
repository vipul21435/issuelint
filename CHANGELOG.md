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
