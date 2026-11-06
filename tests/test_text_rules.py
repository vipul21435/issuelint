"""Exact-output tests for the issue code extraction rules in issuelint.text."""

from __future__ import annotations

from issuelint.text import code_blocks, code_lines, informative

UNFENCED = (
    "Saving fails, I would change it like this:\n"
    "\n"
    "diff --git a/pkg/x.py b/pkg/x.py\n"
    "index 1111111..2222222 100644\n"
    "--- a/pkg/x.py\n"
    "+++ b/pkg/x.py\n"
    "@@ -1,4 +1,4 @@\n"
    " def save(item):\n"
    "-    item.write()\n"
    "+    item.write(flush=True)\n"
    "     log(item)\n"
    "+    return item\n"
    "\n"
    "Thanks for looking."
)


def test_unfenced_diff_keeps_context_and_added_lines_in_order_without_prefixes():
    assert code_blocks(UNFENCED) == [
        "def save(item):\n    item.write(flush=True)\n    log(item)\n    return item\n"
    ]


def test_unfenced_diff_may_start_at_a_file_header_pair_without_a_hunk_header():
    issue = "Patch:\n--- a/pkg/x.py\n+++ b/pkg/x.py\n-old_call()\n+new_call()\nend of patch"
    assert code_blocks(issue) == ["new_call()"]


def test_a_dash_line_alone_does_not_start_a_diff():
    assert code_blocks("--- notes\n+ one item\nmore prose") == []


def test_prose_and_single_indented_lines_are_not_code():
    issue = "First line of prose.\nSecond line of prose.\n    only_one_indented()\nBack to prose."
    assert code_blocks(issue) == []
    assert code_blocks("Prose at the start.\n    one_indented_line_at_the_end()") == []


def test_two_indented_lines_are_one_block():
    issue = "Run this:\n    a = load()\n\tprint(a)\nand it fails."
    assert code_blocks(issue) == ["    a = load()\n\tprint(a)"]
    assert code_blocks("Run this:\n    a = load()\n    print(a)") == [
        "    a = load()\n    print(a)"
    ]


def test_comment_and_blank_lines_are_not_code_lines():
    lines = ["# a comment", "  // another", "/* block */", " * star", "", "   ", "x = 1  # set"]
    assert code_lines(lines) == ["x = 1  # set"]


def test_informative_at_exactly_half_identifiers():
    assert informative(("a", "(", "b", ")"))
    assert informative(("a", "(", "b", ")", "c"))
    assert not informative(("a", "(", "b", ")", ")"))
    assert not informative(("a", "(", ")", ")"))
    assert informative(("_x", "1", "2", "y"))
