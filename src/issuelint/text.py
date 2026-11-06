"""Issue text handling: code blocks, tokens, n-grams, links, identifiers."""

from __future__ import annotations

import re
from collections.abc import Iterable

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_URL_RE = re.compile(r"https?://[^\s)>\]\"']+")
_TOKEN_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|==|!=|<=|>=|->|=>|\*\*|//|[^\sA-Za-z0-9_]"
)
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_COMMENT_RE = re.compile(r"^\s*(?:#|//|/\*|\*)")


def code_blocks(issue: str) -> list[str]:
    """Fenced blocks first, then indented blocks (four spaces or a tab) outside fences."""
    blocks = [m.group(1) for m in _FENCE_RE.finditer(issue)]
    rest = _FENCE_RE.sub("\n", issue)
    current: list[str] = []
    for line in rest.splitlines():
        if line.startswith(("    ", "\t")) and line.strip():
            current.append(line)
        elif current:
            if len(current) >= 2:
                blocks.append("\n".join(current))
            current = []
    if len(current) >= 2:
        blocks.append("\n".join(current))
    return blocks


def inline_code(issue: str) -> list[str]:
    """Single-backtick spans outside fenced blocks."""
    rest = _FENCE_RE.sub("\n", issue)
    return [m.group(1).strip() for m in _INLINE_CODE_RE.finditer(rest)]


def urls(issue: str) -> list[str]:
    return [u.rstrip(".,;:") for u in _URL_RE.findall(issue)]


def tokens(text: str) -> list[str]:
    """Code tokens: identifiers, numbers and punctuation; whitespace dropped."""
    return _TOKEN_RE.findall(text)


def words(text: str) -> set[str]:
    """Identifier-shaped words of a text."""
    return set(_WORD_RE.findall(text))


def ngrams(items: list[str], n: int) -> list[tuple[str, ...]]:
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
    """The form in which a file path is mentioned: the full path, a suffix, or its basename."""
    if path in issue:
        return path
    parts = path.split("/")
    for start in range(1, len(parts)):
        suffix = "/".join(parts[start:])
        if suffix in issue:
            return suffix
    return None
