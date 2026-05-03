import pytest
from pathlib import Path
from tokcodecut import dispatcher


@pytest.fixture
def py_file(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("def hello(): pass\n")
    return str(f)


def test_routes_py_structure(py_file):
    result = dispatcher.structure(py_file)
    assert "hello" in result


def test_routes_py_imports(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("import os\ndef foo(): pass\n")
    result = dispatcher.imports(str(f))
    assert "import os" in result


def test_unsupported_extension(tmp_path):
    f = tmp_path / "file.rb"
    f.write_text("puts 'hello'\n")
    for op in [dispatcher.structure, dispatcher.skeleton, dispatcher.imports]:
        result = op(str(f))
        assert "Unsupported" in result
        assert ".rb" in result


def test_unsupported_symbol_body(tmp_path):
    f = tmp_path / "file.rb"
    f.write_text("puts 'hello'\n")
    result = dispatcher.symbol_body(str(f), "hello")
    assert "Unsupported" in result
