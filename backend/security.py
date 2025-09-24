import re
from pathlib import Path

class SecurityScanner:
    DANGEROUS_PATTERNS = [
        (r'os\.system\s*\(', 'os.system call'),
        (r'subprocess\.(run|Popen)\s*\(', 'subprocess call'),
        (r'eval\s*\(', 'eval function'),
        (r'exec\s*\(', 'exec function'),
        (r'__import__\s*\(', 'dynamic import'),
        (r'open\s*\([^)]*[\'"]?w[\'"]?[^)]*\)', 'file write operation'),
        (r'requests\.(get|post|put|delete)\s*\(', 'HTTP request'),
    ]
    
    @classmethod
    def scan_file(cls, file_path: Path) -> list:
        if file_path.stat().st_size > 10 * 1024 * 1024:  # Skip files >10MB
            return [f"File too large to scan: {file_path.name}"]
            
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for pattern, description in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, content):
                    issues.append(f"{description} in {file_path.name}")
        except Exception as e:
            issues.append(f"Could not scan {file_path.name}: {str(e)}")
        return issues

    @classmethod
    def scan_directory(cls, directory: Path) -> dict:
        issues = {}
        for py_file in directory.rglob("*.py"):
            # Skip blacklisted paths
            if any(part in str(py_file) for part in Config.BLACKLISTED_PATTERNS):
                continue
            file_issues = cls.scan_file(py_file)
            if file_issues:
                issues[str(py_file.relative_to(directory))] = file_issues
        return issues