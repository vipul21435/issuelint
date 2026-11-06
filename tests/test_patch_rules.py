"""Hunk line counting and new-name rules of the patch parser."""

from __future__ import annotations

from issuelint.patch import parse_patch

FORMAT_PATCH = (
    "From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001\n"
    "Subject: [PATCH] Change x\n"
    "\n"
    "---\n"
    " a.py | 2 +-\n"
    "\n"
    "diff --git a/a.py b/a.py\n"
    "index 1111111..2222222 100644\n"
    "--- a/a.py\n"
    "+++ b/a.py\n"
    "{hunk}"
    "-- \n"
    "2.39.0\n"
)


def _only_file(hunk: str):
    parsed = parse_patch(FORMAT_PATCH.format(hunk=hunk))
    assert parsed.paths == ["a.py"]
    return parsed.files[0]


def test_format_patch_signature_after_the_last_hunk_is_not_a_removed_line():
    f = _only_file("@@ -1 +1 @@\n-x = 1\n+x = 2\n")
    assert f.added == ["x = 2"]
    assert f.removed == ["x = 1"]


def test_context_lines_count_against_both_sides():
    f = _only_file("@@ -1,3 +1,3 @@\n c1 = 0\n c2 = 0\n-a = 1\n+a = 2\n")
    assert f.added == ["a = 2"]
    assert f.removed == ["a = 1"]


def test_removed_and_added_lines_count_once_each():
    f = _only_file("@@ -1,2 +1,2 @@\n-a = 1\n-b = 1\n+a = 2\n+b = 2\n")
    assert f.added == ["a = 2", "b = 2"]
    assert f.removed == ["a = 1", "b = 1"]


def test_prose_after_a_hunk_is_ignored():
    text = "--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,1 @@\n-x\n+y\nThanks for the review.\n- one\n+ two\n"
    f = parse_patch(text).files[0]
    assert (f.added, f.removed) == (["y"], ["x"])


def test_a_hunk_header_without_counts_covers_one_line():
    text = "--- a/a.py\n+++ b/a.py\n@@ -3 +3 @@\n-x = 1\n+x = 2\n+not part of the hunk\n"
    f = parse_patch(text).files[0]
    assert f.added == ["x = 2"]


def test_new_names_keep_three_characters_and_skip_two():
    patch = parse_patch("--- a/a.py\n+++ b/a.py\n@@ -1,0 +1,1 @@\n+ab = abc + abcd\n")
    assert patch.new_names() == ["abc", "abcd"]
    assert patch.new_names(min_length=4) == ["abcd"]


def test_removed_lines_after_the_added_ones_are_kept():
    f = _only_file("@@ -1,2 +1,1 @@\n+c = 2\n-a = 1\n-b = 1\n")
    assert f.removed == ["a = 1", "b = 1"]
    f = _only_file("@@ -1,3 +1,2 @@\n+n = 1\n c1 = 0\n-r = 1\n-s = 1\n")
    assert f.removed == ["r = 1", "s = 1"]


def test_a_hunk_header_without_an_old_count_covers_one_old_line():
    f = _only_file("@@ -3 +3 @@\n+x = 2\n-x = 1\n")
    assert (f.added, f.removed) == (["x = 2"], ["x = 1"])
