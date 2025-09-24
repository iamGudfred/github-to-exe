import re
import os
from pathlib import Path

class SecurityScanner:
    """Basic security scanner to detect potentially dangerous code"""
    
    DANGEROUS_PATTERNS = [
        (r'os\.system\s*\(', 'os.system call'),
        (r'subprocess\.run\s*\(', 'subprocess call'),
        (r'eval\s*\(', 'eval function'),
        (r'exec\s*\(', 'exec function'),
        (r'__import__\s*\(', 'dynamic import'),
        (r'open\s*\([^)]*w[^)]*\)', 'file write operation'),
        (r'requests\.(get|post|put|delete)\s*\(', 'HTTP request'),
    ]
    
    @classmethod
    def scan_file(cls, file_path: Path) -> list:
        """Scan a file for potentially dangerous patterns"""
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
        """Scan a directory for security issues"""
        issues = {}
        
        for py_file in directory.rglob("*.py"):
            file_issues = cls.scan_file(py_file)
            if file_issues:
                issues[str(py_file.relative_to(directory))] = file_issues
                
        return issues