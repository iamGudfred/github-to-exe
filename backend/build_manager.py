"""
GitHub Repository to Executable Builder

This module handles:
- Repository cloning and analysis
- Entry point detection
- Security scanning integration
- PyInstaller executable generation

Known Issues:
- No concurrent build support
- Basic security scanning only
- Windows executables only
"""
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from git import Repo
from .security import SecurityScanner
from .config import Config


class BuildError(Exception):
    """Raised when build process fails"""
    pass


class RepositoryAnalyzer:
    """Handles repository analysis and entry point detection"""

    # Entry point candidates in priority order
    ENTRY_POINT_CANDIDATES = [
        "main.py",
        "app.py",
        "run.py",
        "__main__.py",
        "cli.py"
    ]

    @staticmethod
    def find_python_files(repo_path: Path) -> List[Path]:
        """Find all Python files in repository"""
        return list(repo_path.rglob("*.py"))

    @staticmethod
    def find_entry_point(repo_path: Path, py_files: List[Path]) -> Optional[Path]:
        """
        Find the most likely entry point for the application

        Returns:
            Path to entry point file, or None if no suitable candidate found
        """
        if not py_files:
            return None

        # Try known entry point names first
        for candidate_name in RepositoryAnalyzer.ENTRY_POINT_CANDIDATES:
            candidate = repo_path / candidate_name
            if candidate.exists() and candidate in py_files:
                return candidate

        # Fallback: look for files with if __name__ == "__main__"
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'if __name__ == "__main__"' in content:
                        return py_file
            except (IOError, UnicodeError):
                continue

        return None  # Don't blindly pick first file

    @classmethod
    def analyze_repository(cls, repo_url: str, temp_dir: str) -> Dict:
        """
        Analyze repository for buildability

        Returns:
            Dict with analysis results including can_build, issues, entry_point, file_count
        """
        repo_path = Path(temp_dir) / "repo"

        try:
            # Clone with timeout
            Repo.clone_from(repo_url, repo_path, depth=1)
        except Exception as e:
            return {
                'can_build': False,
                'issues': [f'Failed to clone repository: {str(e)}'],
                'entry_point': None,
                'file_count': 0
            }

        # Find Python files
        py_files = cls.find_python_files(repo_path)
        if not py_files:
            return {
                'can_build': False,
                'issues': ['No Python files found in repository'],
                'entry_point': None,
                'file_count': 0
            }

        # Find entry point
        entry_point = cls.find_entry_point(repo_path, py_files)
        issues = []

        if not entry_point:
            issues.append('No clear entry point found (no main.py, app.py, or files with if __name__ == "__main__")')

        # Security scan
        security_issues = SecurityScanner.scan_directory(repo_path)
        if security_issues:
            issues.extend([issue for file_issues in security_issues.values() for issue in file_issues])

        return {
            'can_build': len(issues) == 0,
            'issues': issues,
            'entry_point': entry_point.name if entry_point else None,
            'file_count': len(py_files)
        }


class PyInstallerManager:
    """Handles PyInstaller detection and execution"""

    @staticmethod
    def check_available() -> Tuple[bool, Optional[List[str]]]:
        """
        Check if PyInstaller is available and return command to use

        Returns:
            (is_available, command_args) where command_args is None if not available
        """
        # Try direct pyinstaller command
        try:
            result = subprocess.run(
                ['pyinstaller', '--version'],
                capture_output=True,
                check=True,
                timeout=10
            )
            return True, ['pyinstaller']
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try python -m PyInstaller
        try:
            result = subprocess.run(
                ['python', '-m', 'PyInstaller', '--version'],
                capture_output=True,
                check=True,
                timeout=10
            )
            return True, ['python', '-m', 'PyInstaller']
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return False, None

    @staticmethod
    def build_executable(entry_point: Path, output_dir: Path, exe_name: str,
                        console: bool = True, timeout: int = 300) -> Path:
        """
        Build executable using PyInstaller

        Args:
            entry_point: Python file to build
            output_dir: Directory to place built executable
            exe_name: Name for the executable
            console: Whether to show console window
            timeout: Build timeout in seconds

        Returns:
            Path to built executable

        Raises:
            BuildError: If build fails
        """
        available, cmd = PyInstallerManager.check_available()
        if not available:
            raise BuildError("PyInstaller not found. Install with: pip install pyinstaller")

        dist_path = output_dir / "dist"
        work_path = output_dir / "work"

        # Security: Validate entry_point is safe
        if not entry_point.exists():
            raise BuildError("Entry point file does not exist")
        if not entry_point.suffix == '.py':
            raise BuildError("Entry point must be a Python file")
        if not entry_point.is_file():
            raise BuildError("Entry point must be a regular file")

        # Security: Validate paths don't contain directory traversal
        try:
            entry_point.resolve().relative_to(entry_point.parent.resolve())
        except ValueError:
            raise BuildError("Invalid entry point path")

        # Build command
        build_cmd = cmd + [
            "--onefile",
            "--console" if console else "--windowed",
            "--name", exe_name,
            "--distpath", str(dist_path),
            "--workpath", str(work_path),
            str(entry_point)
        ]

        try:
            result = subprocess.run(
                build_cmd,
                cwd=entry_point.parent,
                check=True,
                timeout=timeout,
                capture_output=True,
                text=True
            )
        except subprocess.TimeoutExpired as e:
            # Kill the process if it times out
            if e.process:
                e.process.kill()
            raise BuildError(f"Build timed out after {timeout} seconds")
        except subprocess.CalledProcessError as e:
            raise BuildError(f"PyInstaller failed: {e.stderr}")

        # Verify executable was created
        # Security: Sanitize exe_name again before path construction
        safe_exe_name = "".join(c for c in exe_name if c.isalnum() or c in "._-")
        exe_path = dist_path / f"{safe_exe_name}.exe"
        if not exe_path.exists():
            raise BuildError("Executable was not created")

        return exe_path


class BuildManager:
    """Main build management class"""

    def __init__(self):
        self.analyzer = RepositoryAnalyzer()

    def analyze_repository(self, repo_url: str, temp_dir: str) -> Dict:
        """Analyze repository for buildability"""
        return self.analyzer.analyze_repository(repo_url, temp_dir)

    def build_executable(self, build_data: Dict, force_build: bool = False) -> Dict:
        """
        Build executable from GitHub repository

        Args:
            build_data: Dict containing 'url' and optional build parameters

        Returns:
            Dict with success status, file_path, filename, or error message
        """
        repo_url = build_data['url']
        build_id = f"build_{int(time.time())}"
        build_path = Config.BUILD_DIR / build_id

        try:
            build_path.mkdir(parents=True, exist_ok=True)

            # Clone repository
            repo_path = build_path / "repo"
            try:
                Repo.clone_from(repo_url, repo_path, depth=1)
            except Exception as e:
                return {'success': False, 'error': f'Failed to clone repository: {str(e)}'}

            # Analyze repository
            py_files = RepositoryAnalyzer.find_python_files(repo_path)
            if not py_files:
                return {'success': False, 'error': 'No Python files found'}

            entry_point = RepositoryAnalyzer.find_entry_point(repo_path, py_files)
            if not entry_point:
                return {'success': False, 'error': 'No suitable entry point found'}

            # Security check (unless forced)
            if not force_build:
                from .security import SecurityScanner
                security_issues = SecurityScanner.scan_directory(repo_path)
                if security_issues:
                    issue_count = sum(len(issues) for issues in security_issues.values())
                    return {
                        'success': False,
                        'error': f'This repository contains {issue_count} potentially risky operations (network requests, file operations, etc.). This could be legitimate code, but building executables from untrusted sources is dangerous.',
                        'security_warning': True,
                        'can_force': True
                    }

            # Generate safe executable name with strict validation
            repo_name = repo_url.rstrip('/').split('/')[-1]
            exe_name = "".join(c for c in repo_name if c.isalnum() or c in "._-") or "app"
            # Additional security: limit length and ensure it starts with alphanumeric
            exe_name = exe_name[:50]  # Limit length
            if not exe_name[0].isalnum():
                exe_name = "app_" + exe_name

            # Build executable
            try:
                # Get console setting from build_data, default to False (no console)
                show_console = build_data.get('show_console', False)

                exe_path = PyInstallerManager.build_executable(
                    entry_point=entry_point,
                    output_dir=build_path,
                    exe_name=exe_name,
                    console=show_console,
                    timeout=Config.BUILD_TIMEOUT
                )
            except BuildError as e:
                if 'timed out' in str(e).lower():
                    return {
                        'success': False,
                        'error': 'Build timed out. This repository might be too complex for free hosting.',
                        'suggestion': 'Try a simpler repository or consider upgrading to paid hosting for faster builds.'
                    }
                elif 'not found' in str(e).lower():
                    return {
                        'success': False,
                        'error': 'PyInstaller requires paid hosting tier.',
                        'analysis_passed': True,
                        'suggestion': 'Your repository passed security analysis and is ready to build! However, the free hosting tier has limitations. Help us upgrade to paid hosting ($7/month) by using the Support button above.'
                    }
                else:
                    return {'success': False, 'error': str(e)}

            # Create distribution package
            zip_path = build_path / f"{exe_name}_package.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(exe_path, exe_path.name)
                zf.writestr("README.txt",
                           f"Built from: {repo_url}\n"
                           f"Build date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                           f"WARNING: Only run executables from sources you trust.")

            return {
                'success': True,
                'file_path': str(zip_path),
                'filename': zip_path.name
            }

        except Exception as e:
            return {'success': False, 'error': f'Build failed: {str(e)}'}

        finally:
            # Always cleanup intermediate files
            self._cleanup_build_files(build_path)

    def _cleanup_build_files(self, build_path: Path):
        """Clean up intermediate build files, keeping only the final package"""
        cleanup_dirs = ["work", "repo"]
        for dir_name in cleanup_dirs:
            dir_path = build_path / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path, ignore_errors=True)


# Legacy function for backward compatibility
def check_dependencies() -> bool:
    """Check if PyInstaller is available (legacy function)"""
    available, _ = PyInstallerManager.check_available()
    return available