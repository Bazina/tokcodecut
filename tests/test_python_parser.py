import pytest
from tokcodecut import python_parser

SAMPLE = '''\
import os
from pathlib import Path

class MyClass(Base):
    """Handles record processing."""

    def __init__(self, client) -> None:
        self.client = client

    async def process_data(self, rows: list) -> dict:
        """Process and deduplicate rows."""
        return {}

def fetch_records(app_id: str) -> list:
    """Fetch all records."""
    return []
'''


@pytest.fixture
def sample_file(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text(SAMPLE)
    return str(f)


class TestStructure:
    def test_top_level_function(self, sample_file):
        result = python_parser.structure(sample_file)
        assert "fetch_records" in result

    def test_class_name(self, sample_file):
        result = python_parser.structure(sample_file)
        assert "MyClass" in result

    def test_methods_indented(self, sample_file):
        result = python_parser.structure(sample_file)
        assert "  __init__" in result
        assert "  process_data" in result

    def test_file_not_found(self):
        result = python_parser.structure("/no/such/file.py")
        assert result == "File not found: /no/such/file.py"

    def test_no_imports_in_output(self, sample_file):
        result = python_parser.structure(sample_file)
        assert "import" not in result

    def test_syntax_error(self, tmp_path):
        bad = tmp_path / "bad.py"
        bad.write_text("def (broken:\n")
        result = python_parser.structure(str(bad))
        assert result.startswith("Parse error in")


class TestSkeleton:
    def test_class_signature(self, sample_file):
        result = python_parser.skeleton(sample_file)
        assert "class MyClass(Base):" in result

    def test_class_docstring(self, sample_file):
        result = python_parser.skeleton(sample_file)
        assert '"""Handles record processing."""' in result

    def test_method_signatures(self, sample_file):
        result = python_parser.skeleton(sample_file)
        assert "def __init__" in result
        assert "async def process_data" in result

    def test_no_function_bodies(self, sample_file):
        result = python_parser.skeleton(sample_file)
        assert "self.client = client" not in result
        assert "return {}" not in result
        assert "return []" not in result

    def test_function_signature(self, sample_file):
        result = python_parser.skeleton(sample_file)
        assert "def fetch_records(app_id: str) -> list: ..." in result

    def test_file_not_found(self):
        result = python_parser.skeleton("/no/such/file.py")
        assert result == "File not found: /no/such/file.py"
