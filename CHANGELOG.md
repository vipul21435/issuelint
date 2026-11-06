# Changelog

## 0.1.0

First version.

- Task records from JSONL (`id`, `issue`, `patch`, `test_patch`) or the
  SWE-bench field names (`instance_id`, `problem_statement`, `patch`,
  `test_patch`).
- Six checks, each with a score in [0, 1], a flag and evidence lines:
  solution leakage, test leakage, location hints (reported, never flagged),
  underspecification signals, dependence on external links, scope gap.
- `issuelint check` prints a table, per-task explanations with `--explain`,
  and writes JSON or CSV with `--json` / `--csv`.
