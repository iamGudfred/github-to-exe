import unittest
import tempfile
from pathlib import Path
from backend.security import SecurityScanner

class TestSecurityScanner(unittest.TestCase):
    
    def test_dangerous_patterns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with dangerous code
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
import os
os.system("rm -rf /")  # Dangerous!
x = eval("2 + 2")
            """)
            
            issues = SecurityScanner.scan_file(test_file)
            self.assertGreater(len(issues), 0)
            self.assertTrue(any("os.system" in issue for issue in issues))
    
    def test_safe_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "safe.py"
            test_file.write_text("""
def hello():
    print("Hello, World!")
    
if __name__ == "__main__":
    hello()
            """)
            
            issues = SecurityScanner.scan_file(test_file)
            self.assertEqual(len(issues), 0)

if __name__ == '__main__':
    unittest.main()