import re

from pr_review_agent.diff_utils import _annotate_patch, build_annotated_diff

SAMPLE_PATCH = (
    "@@ -1,3 +1,4 @@\n"
    " def add(a, b):\n"
    "-    return a + b\n"
    "+    result = a + b\n"
    "+    return result\n"
)


def test_annotate_patch_assigns_correct_new_line_numbers():
    annotated = _annotate_patch(SAMPLE_PATCH)

    added_result = re.search(r"(\d+)\s+\+\s+.*result = a \+ b", annotated)
    added_return = re.search(r"(\d+)\s+\+\s+.*return result", annotated)

    assert added_result is not None and int(added_result.group(1)) == 2
    assert added_return is not None and int(added_return.group(1)) == 3


def test_annotate_patch_does_not_number_removed_lines():
    annotated = _annotate_patch(SAMPLE_PATCH)
    removed_lines = [line for line in annotated.splitlines() if " - " in line]
    assert len(removed_lines) == 1
    assert not re.match(r"^\s*\d+\s+-", removed_lines[0])


def test_build_annotated_diff_includes_modified_files():
    files = [{"filename": "app.py", "status": "modified", "patch": SAMPLE_PATCH}]
    diff_text, skipped = build_annotated_diff(files)
    assert "app.py" in diff_text
    assert skipped == []


def test_build_annotated_diff_skips_removed_and_binary_files():
    files = [
        {"filename": "deleted.py", "status": "removed", "patch": "@@ -1 +0,0 @@\n-x = 1"},
        {"filename": "image.png", "status": "modified", "patch": None},
        {"filename": "app.py", "status": "modified", "patch": SAMPLE_PATCH},
    ]
    diff_text, skipped = build_annotated_diff(files)

    assert "app.py" in diff_text
    assert "deleted.py" not in diff_text
    assert any("deleted.py" in s for s in skipped)
    assert any("image.png" in s for s in skipped)


def test_build_annotated_diff_skips_oversized_patch():
    huge_patch = "@@ -1,1 +1,1 @@\n" + "+x\n" * 20_000
    files = [{"filename": "huge.py", "status": "modified", "patch": huge_patch}]
    diff_text, skipped = build_annotated_diff(files)
    assert diff_text == ""
    assert any("zu groß" in s for s in skipped)
