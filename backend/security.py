"""
Security Scanner for Python Code

This module provides basic security scanning for Python repositories.
It looks for potentially dangerous patterns in code.

Limitations:
- Regex-based scanning can be bypassed with code obfuscation
- Does not understand context (legitimate vs malicious usage)
- No AST parsing for deeper analysis
- High false positive rate

This is NOT a comprehensive security solution.
"""
import re
from pathlib import Path
from typing import Dict, List

from .config import Config


class SecurityScanner:
    """
    Basic security scanner using regex patterns

    This scanner is intentionally simple and conservative.
    It will flag many legitimate operations to err on the side of caution.
    """

    # Patterns that indicate potentially dangerous operations
    # These are conservative and will produce false positives
    DANGEROUS_PATTERNS = [
        # System command execution
        (r'os\.system\s*\(', 'System command execution (os.system)'),
        (r'subprocess\.(run|Popen|call|check_call|check_output)\s*\(',
         'Subprocess execution'),
        (r'os\.(popen|spawn|exec)', 'Process spawning'),

        # Code execution
        (r'\beval\s*\(', 'Dynamic code evaluation (eval)'),
        (r'\bexec\s*\(', 'Dynamic code execution (exec)'),
        (r'compile\s*\([^)]*,\s*["\'][^"\']*["\'],\s*["\']exec["\']',
         'Code compilation for execution'),

        # Dynamic imports (can be dangerous)
        (r'__import__\s*\(', 'Dynamic module import'),
        (r'importlib\.import_module\s*\(', 'Dynamic module import'),

        # File operations
        (r'open\s*\([^)]*[,\s]+["\']w["\']', 'File write operation'),
        (r'open\s*\([^)]*[,\s]+["\']a["\']', 'File append operation'),
        (r'shutil\.(rmtree|move|copy)', 'File system manipulation'),

        # Network operations
        (r'requests\.(get|post|put|delete|patch)\s*\(', 'HTTP request'),
        (r'urllib\.(request|urlopen)', 'URL request'),
        (r'socket\.(socket|connect)', 'Socket operation'),

        # Dangerous builtins
        (r'\bgetattr\s*\(.*,.*["\']__.*__["\']', 'Attribute access to dunder methods'),
        (r'\bsetattr\s*\(', 'Dynamic attribute setting'),
        (r'\bdelattr\s*\(', 'Dynamic attribute deletion'),
    ]

    @classmethod
    def scan_file(cls, file_path: Path) -> List[str]:
        """
        Scan a single Python file for security issues

        Args:
            file_path: Path to the Python file to scan

        Returns:
            List of issue descriptions found in the file
        """
        # Skip files that are too large
        if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
            return [f"File too large to scan safely: {file_path.name}"]

        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            line_number = 0
            for line in content.splitlines():
                line_number += 1
                for pattern, description in cls.DANGEROUS_PATTERNS:
                    if re.search(pattern, line):
                        issues.append(f"{description} on line {line_number}")

        except (IOError, OSError, UnicodeError) as e:
            issues.append(f"Could not scan {file_path.name}: {str(e)}")

        return issues

    @classmethod
    def scan_directory(cls, directory: Path) -> Dict[str, List[str]]:
        """
        Scan all Python files in a directory

        Args:
            directory: Directory to scan recursively

        Returns:
            Dict mapping relative file paths to lists of issues
        """
        issues = {}

        for py_file in directory.rglob("*.py"):
            # Skip files in blacklisted directories
            relative_path = py_file.relative_to(directory)
            if cls._should_skip_file(relative_path):
                continue

            file_issues = cls.scan_file(py_file)
            if file_issues:
                issues[str(relative_path)] = file_issues

        return issues

    @classmethod
    def _should_skip_file(cls, relative_path: Path) -> bool:
        """
        Check if a file should be skipped during scanning

        Args:
            relative_path: Relative path to the file

        Returns:
            True if file should be skipped
        """
        path_str = str(relative_path).lower()

        for pattern in Config.BLACKLISTED_PATTERNS:
            if pattern.lower() in path_str:
                return True

        # Skip test files as they often contain mock dangerous operations
        if any(part in path_str for part in ['test_', '_test.py', '/tests/', '\\tests\\']):
            return True

        return False

    @classmethod
    def is_likely_safe(cls, issues: Dict[str, List[str]]) -> bool:
        """
        Heuristic to determine if repository is likely safe despite flagged issues

        This is a simple heuristic and should not be relied upon for security.

        Args:
            issues: Security issues found by scan

        Returns:
            True if repository seems likely to be safe
        """
        if not issues:
            return True

        total_issues = sum(len(file_issues) for file_issues in issues.values())

        # If only a few issues and they're in specific files, might be OK
        if total_issues <= 3:
            safe_patterns = [
                'setup.py',
                'install',
                'config',
                'example',
                'demo'
            ]
            for file_path in issues.keys():
                if any(pattern in file_path.lower() for pattern in safe_patterns):
                    return True

        return False