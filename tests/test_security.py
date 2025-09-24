import unittest
import tempfile
from pathlib import Path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from security import SecurityScanner

class TestSecurityScanner(unittest.TestCase):
    def test_dangerous_patterns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text('import os\nos.system("echo hacked")')
            issues = SecurityScanner.scan_file(test_file)
            self.assertTrue(any("os.system" in issue for issue in issues))

    def test_safe_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "safe.py"
            test_file.write_text('print("Hello")\n')
            issues = SecurityScanner.scan_file(test_file)
            self.assertEqual(len(issues), 0)

if __name__ == '__main__':
    unittest.main()