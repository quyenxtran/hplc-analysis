"""Enforce exact byte limits, including UTF-8 and test modules."""
from pathlib import Path
import tempfile
import unittest
from check_module_sizes import oversized_files


class ModuleSizeTests(unittest.TestCase):
    def test_repository_sources_are_at_most_5000_bytes(self):
        self.assertEqual(oversized_files(Path(__file__).parent), [])

    def test_exact_boundary_and_multibyte_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "example.py"
            path.write_bytes(b"#" * 5000)
            self.assertEqual(oversized_files(root), [])
            path.write_bytes(b"#" * 4999 + "µ".encode("utf-8"))
            self.assertEqual(oversized_files(root), [("example.py", 5001)])
