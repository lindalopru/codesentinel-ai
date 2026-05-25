"""Unified diff parsing tests."""

from __future__ import annotations

from codesentinel.review.git_diff import parse_unified_diff

SAMPLE_DIFF = """diff --git a/foo.py b/foo.py
index 0000001..0000002 100644
--- a/foo.py
+++ b/foo.py
@@ -10,0 +11,3 @@
+def new_one():
+    return 1
+
@@ -50,2 +53,1 @@
-old_line_a
-old_line_b
+merged_replacement
diff --git a/bar.js b/bar.js
new file mode 100644
--- /dev/null
+++ b/bar.js
@@ -0,0 +1,2 @@
+const x = 1;
+console.log(x);
"""


def test_parses_added_lines_in_two_files():
    parsed = parse_unified_diff(SAMPLE_DIFF)
    assert "foo.py" in parsed
    assert "bar.js" in parsed
    # foo.py: added lines 11, 12, 13 then 53
    assert parsed["foo.py"] == {11, 12, 13, 53}
    # bar.js: added lines 1, 2
    assert parsed["bar.js"] == {1, 2}


def test_empty_diff_returns_empty():
    assert parse_unified_diff("") == {}
