import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from git import Repo
from .security import SecurityScanner
from .config import Config

class BuildManager:
    def analyze_repository(self, repo_url: str, temp_dir: str) -> dict:
        """Clone and analyze repo without building"""
        repo_path = Path(temp_dir) / "repo"
        Repo.clone_from(repo_url, repo_path, depth=1)
        
        # Find Python files
        py_files = list(repo_path.rglob("*.py"))
        if not py_files:
            return {
                'can_build': False,
                'issues': ['No Python files found'],
                'entry_point': None,
                'file_count': 0
            }
        
        # Find entry point
        entry_point = None
        for name in ["main.py", "app.py", "run.py"]:
            candidate = repo_path / name
            if candidate.exists():
                entry_point = candidate
                break
        if not entry_point:
            entry_point = py_files[0]
        
        # Security scan
        security_issues = SecurityScanner.scan_directory(repo_path)
        
        return {
            'can_build': len(security_issues) == 0,
            'issues': [issue for issues in security_issues.values() for issue in issues],
            'entry_point': entry_point.name,
            'file_count': len(py_files)
        }

    def build_executable(self, build_data: dict) -> dict:
        """Build executable from GitHub repo"""
        repo_url = build_data['url']
        build_id = f"build_{int(subprocess.time.time())}"
        build_path = Config.BUILD_DIR / build_id
        build_path.mkdir()
        
        try:
            # Clone repo
            repo_path = build_path / "repo"
            Repo.clone_from(repo_url, repo_path, depth=1)
            
            # Find entry point
            py_files = list(repo_path.rglob("*.py"))
            if not py_files:
                return {'success': False, 'error': 'No Python files found'}
            
            entry_point = None
            for name in ["main.py", "app.py", "run.py"]:
                candidate = repo_path / name
                if candidate.exists():
                    entry_point = candidate
                    break
            if not entry_point:
                entry_point = py_files[0]
            
            # Get safe exe name
            repo_name = repo_url.rstrip('/').split('/')[-1]
            exe_name = "".join(c for c in repo_name if c.isalnum() or c in "._-")
            
            # Build with PyInstaller (NO pip install!)
            dist_path = build_path / "dist"
            work_path = build_path / "work"
            
            subprocess.run([
                "pyinstaller",
                "--onefile",
                "--noconsole",
                "--name", exe_name,
                "--distpath", str(dist_path),
                "--workpath", str(work_path),
                str(entry_point.relative_to(repo_path))
            ], cwd=repo_path, check=True, timeout=Config.BUILD_TIMEOUT)
            
            # Create zip
            exe_file = dist_path / f"{exe_name}.exe"
            if not exe_file.exists():
                return {'success': False, 'error': 'Executable not created'}
            
            zip_path = build_path / f"{exe_name}_package.zip"
            import zipfile
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.write(exe_file, exe_file.name)
                zf.writestr("README.txt", f"Built from: {repo_url}\nWARNING: Only run if you trust this source.")
            
            return {
                'success': True,
                'file_path': str(zip_path),
                'filename': zip_path.name
            }
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Build timed out (5 minutes)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            # Cleanup work files (keep dist for download)
            if (build_path / "work").exists():
                shutil.rmtree(build_path / "work", ignore_errors=True)
            if (build_path / "repo").exists():
                shutil.rmtree(build_path / "repo", ignore_errors=True)