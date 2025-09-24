from pathlib import Path

class Config:
    # Security
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'.py', '.txt', '.md', '.yml', '.yaml', '.json'}
    BLACKLISTED_PATTERNS = [
        '__pycache__', '.git', 'node_modules', 'venv', 'env',
        '.env', 'secret', 'password', 'key'
    ]
    
    # Build settings
    BUILD_TIMEOUT = 300  # 5 minutes
    MAX_CONCURRENT_BUILDS = 3
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    BUILD_DIR = BASE_DIR / "builds"
    UPLOAD_DIR = BASE_DIR / "uploads"
    
    @classmethod
    def ensure_dirs(cls):
        """Create directories only when needed (not at import time)"""
        cls.BUILD_DIR.mkdir(exist_ok=True)
        cls.UPLOAD_DIR.mkdir(exist_ok=True)