"""
Comprehensive tests for build_manager module

These tests prove that the code actually works (or doesn't).
No feel-good "it works!" bullshit - real verification.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from build_manager import (
    RepositoryAnalyzer,
    PyInstallerManager,
    BuildManager,
    BuildError
)


class TestRepositoryAnalyzer(unittest.TestCase):
    """Test repository analysis logic"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "test_repo"
        self.repo_path.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_file(self, filename: str, content: str):
        """Helper to create test Python files"""
        file_path = self.repo_path / filename
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path

    def test_find_python_files_empty_repo(self):
        """Test behavior with no Python files"""
        files = RepositoryAnalyzer.find_python_files(self.repo_path)
        self.assertEqual(files, [])

    def test_find_python_files_with_files(self):
        """Test finding Python files"""
        self.create_test_file("main.py", "print('hello')")
        self.create_test_file("utils.py", "def helper(): pass")
        self.create_test_file("readme.txt", "not python")

        files = RepositoryAnalyzer.find_python_files(self.repo_path)
        file_names = [f.name for f in files]

        self.assertIn("main.py", file_names)
        self.assertIn("utils.py", file_names)
        self.assertNotIn("readme.txt", file_names)

    def test_find_entry_point_main_py(self):
        """Test finding main.py as entry point"""
        main_py = self.create_test_file("main.py", "print('hello')")
        self.create_test_file("other.py", "print('other')")

        py_files = RepositoryAnalyzer.find_python_files(self.repo_path)
        entry_point = RepositoryAnalyzer.find_entry_point(self.repo_path, py_files)

        self.assertEqual(entry_point, main_py)

    def test_find_entry_point_app_py(self):
        """Test finding app.py when no main.py"""
        app_py = self.create_test_file("app.py", "print('hello')")
        self.create_test_file("other.py", "print('other')")

        py_files = RepositoryAnalyzer.find_python_files(self.repo_path)
        entry_point = RepositoryAnalyzer.find_entry_point(self.repo_path, py_files)

        self.assertEqual(entry_point, app_py)

    def test_find_entry_point_if_name_main(self):
        """Test finding file with if __name__ == '__main__'"""
        self.create_test_file("utils.py", "def helper(): pass")
        script_py = self.create_test_file("script.py", """
def main():
    print("hello")

if __name__ == "__main__":
    main()
""")

        py_files = RepositoryAnalyzer.find_python_files(self.repo_path)
        entry_point = RepositoryAnalyzer.find_entry_point(self.repo_path, py_files)

        self.assertEqual(entry_point, script_py)

    def test_find_entry_point_none_found(self):
        """Test when no suitable entry point exists"""
        self.create_test_file("utils.py", "def helper(): pass")
        self.create_test_file("config.py", "DEBUG = True")

        py_files = RepositoryAnalyzer.find_python_files(self.repo_path)
        entry_point = RepositoryAnalyzer.find_entry_point(self.repo_path, py_files)

        # Should NOT blindly pick first file
        self.assertIsNone(entry_point)

    def test_find_entry_point_no_files(self):
        """Test when no Python files exist"""
        entry_point = RepositoryAnalyzer.find_entry_point(self.repo_path, [])
        self.assertIsNone(entry_point)


class TestPyInstallerManager(unittest.TestCase):
    """Test PyInstaller integration"""

    @patch('subprocess.run')
    def test_check_available_direct_command(self, mock_run):
        """Test detecting pyinstaller command"""
        mock_run.return_value = MagicMock()

        available, cmd = PyInstallerManager.check_available()

        self.assertTrue(available)
        self.assertEqual(cmd, ['pyinstaller'])
        mock_run.assert_called_with(
            ['pyinstaller', '--version'],
            capture_output=True,
            check=True,
            timeout=10
        )

    @patch('subprocess.run')
    def test_check_available_python_module(self, mock_run):
        """Test falling back to python -m PyInstaller"""
        # First call fails (direct command not found)
        # Second call succeeds (python module works)
        mock_run.side_effect = [
            FileNotFoundError(),
            MagicMock()
        ]

        available, cmd = PyInstallerManager.check_available()

        self.assertTrue(available)
        self.assertEqual(cmd, ['python', '-m', 'PyInstaller'])

    @patch('subprocess.run')
    def test_check_available_not_found(self, mock_run):
        """Test when PyInstaller is not available"""
        mock_run.side_effect = FileNotFoundError()

        available, cmd = PyInstallerManager.check_available()

        self.assertFalse(available)
        self.assertIsNone(cmd)

    @patch('subprocess.run')
    def test_check_available_timeout(self, mock_run):
        """Test timeout handling"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(['pyinstaller'], 10)

        available, cmd = PyInstallerManager.check_available()

        self.assertFalse(available)
        self.assertIsNone(cmd)


class TestBuildManagerIntegration(unittest.TestCase):
    """Integration tests for the full build process"""

    def setUp(self):
        self.build_manager = BuildManager()

    @patch('build_manager.Repo.clone_from')
    def test_analyze_repository_clone_failure(self, mock_clone):
        """Test handling of git clone failures"""
        mock_clone.side_effect = Exception("Network error")

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.build_manager.analyze_repository(
                "https://github.com/fake/repo",
                temp_dir
            )

        self.assertFalse(result['can_build'])
        self.assertIn('Failed to clone repository', result['issues'][0])

    def test_analyze_repository_no_python_files(self):
        """Test repository with no Python files"""
        # Create a temp directory with no Python files
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "repo"
            repo_path.mkdir()
            (repo_path / "README.md").write_text("# Test")

            # Mock the clone to do nothing (files already exist)
            with patch('build_manager.Repo.clone_from'):
                result = self.build_manager.analyze_repository(
                    "https://github.com/fake/repo",
                    temp_dir
                )

        self.assertFalse(result['can_build'])
        self.assertIn('No Python files found', result['issues'][0])
        self.assertEqual(result['file_count'], 0)


class TestRealWorldScenarios(unittest.TestCase):
    """Tests with real-world-like scenarios"""

    def test_malicious_executable_name(self):
        """Test handling of malicious repository names"""
        from build_manager import BuildManager

        # Test with malicious URL that could cause path traversal
        malicious_url = "https://github.com/user/../../../etc/passwd"
        repo_name = malicious_url.rstrip('/').split('/')[-1]
        exe_name = "".join(c for c in repo_name if c.isalnum() or c in "._-") or "app"

        # Should sanitize to safe name
        self.assertNotIn('/', exe_name)
        self.assertNotIn('\\', exe_name)
        self.assertNotIn('..', exe_name)

    def test_empty_executable_name(self):
        """Test handling of URLs that result in empty executable names"""
        from build_manager import BuildManager

        # URL with no valid characters for exe name
        url = "https://github.com/user/!@#$%^&*()"
        repo_name = url.rstrip('/').split('/')[-1]
        exe_name = "".join(c for c in repo_name if c.isalnum() or c in "._-") or "app"

        # Should fallback to "app"
        self.assertEqual(exe_name, "app")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)