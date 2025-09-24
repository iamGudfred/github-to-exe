from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
from pathlib import Path
import threading
import time

from security import SecurityScanner
from build_manager import BuildManager
import config

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

# In-memory build status tracking (use Redis in production)
build_status = {}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

@app.route('/api/analyze', methods=['POST'])
def analyze_repository():
    """Analyze a GitHub repository before building"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing repository URL'}), 400
    
    repo_url = data['url'].strip()
    
    # Basic URL validation
    if not repo_url.startswith('https://github.com/'):
        return jsonify({'error': 'Invalid GitHub URL'}), 400
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Clone and analyze repository
            build_mgr = BuildManager()
            analysis = build_mgr.analyze_repository(repo_url, temp_dir)
            
            return jsonify({
                'can_build': analysis['can_build'],
                'issues': analysis['issues'],
                'entry_point': analysis['entry_point'],
                'file_count': analysis['file_count']
            })
            
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/build', methods=['POST'])
def start_build():
    """Start a build process"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing repository URL'}), 400
    
    # Generate build ID
    build_id = f"build_{int(time.time())}_{hash(data['url']) % 1000}"
    build_status[build_id] = {'status': 'queued', 'progress': 0}
    
    # Start build in background thread
    thread = threading.Thread(
        target=run_build,
        args=(build_id, data),
        daemon=True
    )
    thread.start()
    
    return jsonify({'build_id': build_id, 'status': 'queued'})

def run_build(build_id: str, build_data: dict):
    """Run build process in background thread"""
    try:
        build_status[build_id] = {'status': 'cloning', 'progress': 10}
        
        build_mgr = BuildManager()
        result = build_mgr.build_executable(build_data)
        
        build_status[build_id] = {
            'status': 'completed' if result['success'] else 'failed',
            'progress': 100,
            'result': result
        }
        
    except Exception as e:
        build_status[build_id] = {
            'status': 'failed',
            'progress': 0,
            'error': str(e)
        }

@app.route('/api/status/<build_id>', methods=['GET'])
def get_build_status(build_id: str):
    """Get build status"""
    status = build_status.get(build_id, {'status': 'not_found'})
    return jsonify(status)

@app.route('/api/download/<build_id>', methods=['GET'])
def download_build(build_id: str):
    """Download completed build"""
    status = build_status.get(build_id)
    
    if not status or status['status'] != 'completed':
        return jsonify({'error': 'Build not found or not completed'}), 404
    
    result = status.get('result', {})
    file_path = result.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Build file not found'}), 404
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=result.get('filename', 'build.zip')
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)