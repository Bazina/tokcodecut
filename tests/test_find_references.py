import pytest
from pathlib import Path
from tokcodecut.dispatcher import find_references


def test_finds_references_across_files(tmp_path):
    (tmp_path / "a.py").write_text("from b import MyClass\n")
    (tmp_path / "b.py").write_text("class MyClass: pass\n")
    result = find_references("MyClass", str(tmp_path))
    lines = result.splitlines()
    paths = [l.rsplit(":", 1)[0] for l in lines]
    assert any("a.py" in p for p in paths)


def test_returns_correct_line_number(tmp_path):
    content = "x = 1\nMyClass()\ny = 2\n"
    (tmp_path / "usage.py").write_text(content)
    result = find_references("MyClass", str(tmp_path))
    assert "usage.py:2" in result


def test_skips_node_modules(tmp_path):
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "index.js").write_text("const MyClass = 1;\n")
    (tmp_path / "src.ts").write_text("const x = MyClass;\n")
    result = find_references("MyClass", str(tmp_path))
    assert str(nm) not in result


def test_skips_dot_dirs(tmp_path):
    hidden = tmp_path / ".git"
    hidden.mkdir()
    (hidden / "COMMIT_EDITMSG").write_text("MyClass refactor\n")
    (tmp_path / "real.py").write_text("MyClass()\n")
    result = find_references("MyClass", str(tmp_path))
    assert ".git" not in result


def test_dir_not_found():
    result = find_references("Foo", "/nonexistent/dir/abc")
    assert "not found" in result.lower() or "Directory" in result


def test_no_matches(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    result = find_references("Unicorn", str(tmp_path))
    assert result == "(no references found)"
