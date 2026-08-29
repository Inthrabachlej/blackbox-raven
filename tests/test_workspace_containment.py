"""Regression tests for workspace path containment (raven.py).

Covers the fix for the prefix-based containment check (target_abs.startswith(ws_path)),
which incorrectly treated sibling directories sharing a name prefix (e.g. "proj" vs
"proj-evil") as being inside the workspace, and for unsanitized workspace names that
could resolve outside WORKSPACES_DIR entirely.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import raven


@pytest.fixture
def in_tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_make_workspace_normal_name(in_tmp_cwd):
    ws_path, ws_name = raven.make_workspace("myproj")
    assert ws_name == "myproj"
    assert os.path.isdir(ws_path)
    assert os.path.basename(ws_path) == "myproj"


def test_make_workspace_autoname(in_tmp_cwd):
    ws_path, ws_name = raven.make_workspace()
    assert os.path.isdir(ws_path)


@pytest.mark.parametrize("bad_name", [
    "../escape",
    "../../etc/escape",
    "sub/../../escape",
    "/tmp/escape",
])
def test_make_workspace_rejects_traversal(in_tmp_cwd, bad_name):
    with pytest.raises(ValueError):
        raven.make_workspace(bad_name)


def test_read_file_blocks_sibling_prefix_workspace(in_tmp_cwd):
    # "proj" and "proj-evil" share a string prefix but are different workspaces.
    ws_path, _ = raven.make_workspace("proj")
    evil_ws_path, _ = raven.make_workspace("proj-evil")
    secret = os.path.join(evil_ws_path, "secret.txt")
    with open(secret, "w") as f:
        f.write("top secret")

    result = raven.read_file_or_dir_for_context(ws_path, "../proj-evil/secret.txt")
    assert "SECURITY BLOCKED" in result
    assert "top secret" not in result


def test_read_file_blocks_parent_traversal(in_tmp_cwd):
    ws_path, _ = raven.make_workspace("proj")
    outside = os.path.join(str(in_tmp_cwd), "escape.txt")
    with open(outside, "w") as f:
        f.write("outside content")

    result = raven.read_file_or_dir_for_context(ws_path, "../../escape.txt")
    assert "SECURITY BLOCKED" in result


def test_read_file_allows_normal_nested_file(in_tmp_cwd):
    ws_path, _ = raven.make_workspace("proj")
    nested_dir = os.path.join(ws_path, "normal", "nested")
    os.makedirs(nested_dir, exist_ok=True)
    with open(os.path.join(nested_dir, "file.py"), "w") as f:
        f.write("print('hi')")

    result = raven.read_file_or_dir_for_context(ws_path, "normal/nested/file.py")
    assert "SECURITY BLOCKED" not in result
    assert "print('hi')" in result


def test_write_file_blocks_parent_traversal(in_tmp_cwd, monkeypatch):
    ws_path, _ = raven.make_workspace("proj")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not call Claude when path is blocked")

    monkeypatch.setattr(raven, "ask_claude", fail_if_called)
    result = raven.write_file_from_claude(ws_path, "../../escape.txt", "irrelevant", [])
    assert result == "[SECURITY BLOCKED] target outside workspace."
    assert not os.path.exists(os.path.join(str(in_tmp_cwd), "escape.txt"))


def test_write_file_blocks_sibling_prefix_workspace(in_tmp_cwd, monkeypatch):
    ws_path, _ = raven.make_workspace("proj")
    raven.make_workspace("proj-evil")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not call Claude when path is blocked")

    monkeypatch.setattr(raven, "ask_claude", fail_if_called)
    result = raven.write_file_from_claude(ws_path, "../proj-evil/pwned.txt", "irrelevant", [])
    assert result == "[SECURITY BLOCKED] target outside workspace."
