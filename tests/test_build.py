import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from build_manager import BuildManager

class TestBuildManager(unittest.TestCase):
    def test_analyze_real_repo(self):
        """Test with a real, safe public repo"""
        mgr = BuildManager()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = mgr.analyze_repository(
                "https://github.com/realpython/python-scripts",
                temp_dir
            )
            self.assertIsInstance(result, dict)
            # Don't assert can_build=True (repo might change)

if __name__ == '__main__':
    unittest.main()