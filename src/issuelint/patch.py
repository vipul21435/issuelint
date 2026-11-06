"""Unified diff parsing: files touched, added lines, and the identifiers a patch changes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_FILE_RE = re.compile(r"^diff --git a/(?P<a>\S+) b/(?P<b>\S+)$")
_PLUS_FILE_RE = re.compile(r"^\+\+\+ (?:b/)?(?P<path>\S+)")
_MINUS_FILE_RE = re.compile(r"^--- (?:a/)?(?P<path>\S+)")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,(?P<old>\d+))? \+\d+(?:,(?P<new>\d+))? @@(?P<context>.*)$")

# Definitions in the languages that dominate public issue-to-fix datasets.
_DEF_RES = (
    re.compile(r"^\s*(?:async\s+)?def\s+(?P<name>[A-Za-z_]\w*)"),
    re.compile(r"^\s*class\s+(?P<name>[A-Za-z_]\w*)"),
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s*\*?\s*(?P<name>[A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*="),
    re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(?P<name>[A-Za-z_]\w*)"),
    re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait|impl)\s+(?P<name>[A-Za-z_]\w*)"),
    re.compile(r"^func\s+(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_]\w*)"),
)
_CONTEXT_NAME_RE = re.compile(
    r"\b(?:def|class|function|fn|func|struct|impl|trait)\s+([A-Za-z_$][\w$]*)"
)
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_COMMENT_LINE_RE = re.compile(r"^\s*(?:#|//|/\*|\*)")


def code_lines_of(lines: list[str]) -> list[str]:
    """Lines that are not blank and not a plain comment."""
    return [line for line in lines if line.strip() and not _COMMENT_LINE_RE.match(line)]


_TEST_PATH_RE = re.compile(
    r"(?:^|/)(?:tests?|__tests__|spec|specs|testing)(?:/|$)|(?:^|/)(?:test_[^/]*|[^/]*_test\.[^/]+|[^/]*\.(?:test|spec)\.[^/]+)$"
)


@dataclass
class FileDiff:
    """The parts of one file's diff that the checks use."""

    path: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    hunk_contexts: list[str] = field(default_factory=list)

    @property
    def is_test(self) -> bool:
        return bool(_TEST_PATH_RE.search(self.path))


@dataclass
class ParsedPatch:
    """A parsed unified diff."""

    files: list[FileDiff] = field(default_factory=list)

    @property
    def paths(self) -> list[str]:
        return [f.path for f in self.files]

    def added_lines(self, *, include_tests: bool = True) -> list[str]:
        return [line for f in self.files if include_tests or not f.is_test for line in f.added]

    def removed_lines(self, *, include_tests: bool = True) -> list[str]:
        return [line for f in self.files if include_tests or not f.is_test for line in f.removed]

    def changed_identifiers(self, *, include_tests: bool = False) -> list[str]:
        """Names of functions, classes and similar that the patch defines or sits inside.

        Collected from hunk context headers (the enclosing definition) and from
        added or removed definition lines. Order of first appearance, no repeats.
        """
        seen: dict[str, None] = {}
        for f in self.files:
            if f.is_test and not include_tests:
                continue
            for context in f.hunk_contexts:
                for match in _CONTEXT_NAME_RE.finditer(context):
                    seen.setdefault(match.group(1), None)
            for line in (*f.added, *f.removed):
                for pattern in _DEF_RES:
                    match = pattern.match(line)
                    if match:
                        seen.setdefault(match.group("name"), None)
                        break
        return list(seen)

    def new_names(self, min_length: int = 3) -> list[str]:
        """Identifier tokens on added non-test lines that no removed line contains.

        This over-approximates what the fix introduces: a name already present
        elsewhere in the file but not in the hunk counts as new. Order of first
        appearance; names shorter than ``min_length`` (``i``, ``x``) are skipped.
        """
        removed = set(_NAME_RE.findall("\n".join(self.removed_lines(include_tests=False))))
        found: dict[str, None] = {}
        for line in code_lines_of(self.added_lines(include_tests=False)):
            for name in _NAME_RE.findall(line):
                if len(name) >= min_length and name not in removed:
                    found.setdefault(name, None)
        return list(found)


def parse_patch(text: str) -> ParsedPatch:
    """Parse a unified diff. Lines outside hunks are ignored except file headers.

    Each hunk ends when the line counts in its ``@@ -a,b +c,d @@`` header are
    used up, so a ``--- ``/``+++ `` pair after it starts a new file even when
    the diff has no ``diff --git`` lines (plain ``diff -u`` output).
    """
    parsed = ParsedPatch()
    current: FileDiff | None = None
    in_hunk = False
    old_left = new_left = 0
    old_path = "/dev/null"
    for raw in text.splitlines():
        header = _FILE_RE.match(raw)
        if header:
            current = FileDiff(path=header.group("b"))
            parsed.files.append(current)
            in_hunk = False
            continue
        hunk = _HUNK_RE.match(raw)
        if hunk:
            if current is None:
                current = FileDiff(path="<unknown>")
                parsed.files.append(current)
            in_hunk = True
            old_left = int(hunk.group("old") or 1)
            new_left = int(hunk.group("new") or 1)
            context = hunk.group("context").strip()
            if context:
                current.hunk_contexts.append(context)
            continue
        if in_hunk and current is not None:
            if raw.startswith("\\"):
                continue
            if raw.startswith("+"):
                current.added.append(raw[1:])
                new_left -= 1
            elif raw.startswith("-"):
                current.removed.append(raw[1:])
                old_left -= 1
            else:
                # A context line; some tools strip the leading space of blank ones.
                old_left -= 1
                new_left -= 1
            if old_left <= 0 and new_left <= 0:
                in_hunk = False
            continue
        minus = _MINUS_FILE_RE.match(raw)
        if minus:
            old_path = minus.group("path")
            continue
        plus = _PLUS_FILE_RE.match(raw)
        if plus:
            path = plus.group("path")
            if path == "/dev/null":
                path = old_path  # a deleted file keeps its old name
            if current is None or (current.added or current.removed or current.hunk_contexts):
                current = FileDiff(path=path)
                parsed.files.append(current)
            elif path != "/dev/null":
                current.path = path
            old_path = "/dev/null"
            continue
    return parsed
