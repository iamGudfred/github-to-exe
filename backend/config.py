import os
from pathlib import Path

class Config:
    # Security settings
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
    
    # Ensure directories exist
    BUILD_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)