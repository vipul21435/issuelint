"""Issue text handling: code blocks, tokens, n-grams, links, identifiers."""

from __future__ import annotations

import re
from collections.abc import Iterable

_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_URL_RE = re.compile(r"https?://[^\s)>\]\"']+")
_TOKEN_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|==|!=|<=|>=|->|=>|\*\*|//|[^\sA-Za-z0-9_]"
)
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_COMMENT_RE = re.compile(r"^\s*(?:#|//|/\*|\*)")
_DIFF_START_RE = re.compile(r"^(?:diff --git |@@ -\d)")


def split_fences(issue: str) -> tuple[list[str], list[str]]:
    """Fenced block contents, and the lines outside fences.

    A fence opens on a line that starts (after up to three spaces) with three or
    more backticks or tildes; a backtick opener whose info string holds a
    backtick is a code span, not a fence. The block ends at the first line that
    holds the same marker, and text before the marker on that line belongs to
    the block. An unclosed fence runs to the end of the text, as GitHub renders
    it. One pass over the lines, so the time is linear in the text length.
    """
    blocks: list[str] = []
    outside: list[str] = []
    current: list[str] | None = None
    marker = ""
    for line in issue.splitlines():
        if current is None:
            match = _FENCE_OPEN_RE.match(line)
            if match and not (match.group(1)[0] == "`" and "`" in line[match.end() :]):
                marker = match.group(1)
                current = []
            else:
                outside.append(line)
            continue
        at = line.find(marker)
        if at < 0:
            current.append(line)
            continue
        if line[:at].strip():
            current.append(line[:at])
        blocks.append("\n".join(current))
        current = None
        outside.append(line[at + len(marker) :].lstrip(marker[0]))
    if current is not None:
        blocks.append("\n".join(current))
    return blocks, outside


def _diff_blocks(lines: list[str]) -> tuple[list[str], list[str]]:
    """Unfenced unified diffs, as the code they leave behind, and the other lines.

    A diff starts at a ``diff --git`` line, a ``--- `` line followed by ``+++ ``,
    or an ``@@ -N`` hunk header, and runs through lines that start with a space, a tab,
    ``+``, ``-`` or a backslash (blank lines included). Context and added lines
    are kept without their one-character prefix; removed lines and headers are
    dropped, since they show the code before the change.
    """
    blocks: list[str] = []
    rest: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        starts = _DIFF_START_RE.match(line) or (
            line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ ")
        )
        if not starts:
            rest.append(line)
            i += 1
            continue
        kept: list[str] = []
        while i < len(lines):
            line = lines[i]
            if line.startswith(("diff --git ", "index ", "--- ", "+++ ", "@@", "-", "\\")):
                pass
            elif line.startswith(("+", " ")):
                kept.append(line[1:])
            elif line.startswith("\t"):
                # Context whose leading space was turned into a tab on the way
                # into the tracker (seen in Trac tickets).
                kept.append(line)
            elif not line.strip():
                kept.append("")
            else:
                break
            i += 1
        if any(k.strip() for k in kept):
            blocks.append("\n".join(kept))
    return blocks, rest


def code_blocks(issue: str) -> list[str]:
    """Code in an issue: fenced blocks, unfenced diffs, then indented blocks.

    Indented blocks are runs of two or more lines starting with four spaces or a
    tab, outside fences and diffs.
    """
    blocks, outside = split_fences(issue)
    diffs, rest = _diff_blocks(outside)
    blocks.extend(diffs)
    current: list[str] = []
    for line in rest:
        if line.startswith(("    ", "\t")) and line.strip():
            current.append(line)
        elif current:
            if len(current) >= 2:
                blocks.append("\n".join(current))
            current = []
    if len(current) >= 2:
        blocks.append("\n".join(current))
    return blocks


_TB_FILE_RE = re.compile(r'\bFile "[^"]+", line \d+')
_TB_NUMBERED_RE = re.compile(r"^\s*(?:-*>\s*)?\d+\s")
_TB_PYTEST_RE = re.compile(r"^>\s{2,}\S")


def drop_traceback_source(text: str) -> str:
    """Remove the source lines a traceback quotes.

    A traceback shows the code as it was when the error happened, so it says
    nothing about the fix. Dropped: the line after a Python ``File "...", line N``
    header, IPython's numbered source lines (``    349 code``, ``--> 351 code``) and
    pytest's ``>   code`` lines.
    """
    out: list[str] = []
    skip_next = False
    for line in text.splitlines():
        if skip_next:
            skip_next = False
            continue
        if _TB_FILE_RE.search(line):
            skip_next = True
            out.append(line)
            continue
        if _TB_NUMBERED_RE.match(line) or _TB_PYTEST_RE.match(line):
            continue
        out.append(line)
    return "\n".join(out)


def inline_code(issue: str) -> list[str]:
    """Single-backtick spans outside fenced blocks."""
    rest = "\n".join(split_fences(issue)[1])
    return [m.group(1).strip() for m in _INLINE_CODE_RE.finditer(rest)]


def urls(issue: str) -> list[str]:
    """The http and https links of a text, trailing punctuation removed."""
    return [u.rstrip(".,;:") for u in _URL_RE.findall(issue)]


def tokens(text: str) -> list[str]:
    """Code tokens: identifiers, numbers and punctuation; whitespace dropped.

    Single and double quotes become one token so that ``'a'`` and ``"a"`` match.
    """
    return ['"' if tok == "'" else tok for tok in _TOKEN_RE.findall(text)]


def informative(gram: tuple[str, ...]) -> bool:
    """Whether at least half of a gram's tokens are identifiers.

    Grams made mostly of punctuation and numbers (``) ) ) , 0 ]``, table rules,
    closing brackets) occur in unrelated code and would count as shared code.
    """
    idents = sum(1 for tok in gram if tok[0].isalpha() or tok[0] == "_")
    return 2 * idents >= len(gram)


def code_ngrams(items: list[str], n: int) -> list[tuple[str, ...]]:
    """The informative n-grams of a token list, in order, repeats kept."""
    return [g for g in ngrams(items, n) if informative(g)]


def words(text: str) -> set[str]:
    """Identifier-shaped words of a text."""
    return set(_WORD_RE.findall(text))


def ngrams(items: list[str], n: int) -> list[tuple[str, ...]]:
    """Every run of ``n`` consecutive items, in order; ``ValueError`` when ``n`` is not positive."""
    if n <= 0:
        raise ValueError("n must be positive")
    return [tuple(items[i : i + n]) for i in range(len(items) - n + 1)]


def code_lines(lines: Iterable[str]) -> list[str]:
    """Lines that carry code: not blank, not a plain comment line."""
    return [line for line in lines if line.strip() and not _COMMENT_RE.match(line)]


def mentions(issue_words: set[str], name: str) -> bool:
    """Whether an identifier appears in the issue as a whole word."""
    return name in issue_words


def mentions_path(issue: str, path: str) -> str | None:
    """The form in which a file path is mentioned: the full path, a suffix, or its basename.

    A form counts only as a whole name: not preceded by a word character or
    ``-`` (so ``base.py`` is not found in ``database.py`` or ``test_base.py``)
    and not followed by a word character. A leading ``/`` is allowed, so the
    tail of an absolute path in a traceback counts.
    """
    parts = path.split("/")
    for start in range(len(parts)):
        form = "/".join(parts[start:])
        if re.search(r"(?<![\w-])" + re.escape(form) + r"(?!\w)", issue):
            return form
    return None
