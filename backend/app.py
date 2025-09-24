import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, send_file
import time
from build_manager import BuildManager
from config import Config

# Ensure directories exist
Config.ensure_dirs()

app = Flask(__name__, static_folder="../frontend")

# In-memory status (OK for learning)
build_status = {}

@app.route('/')
def index():
    return send_file("../frontend/index.html")

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy'})

@app.route('/api/analyze', methods=['POST'])
def analyze_repository():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing repository URL'}), 400
    
    repo_url = data['url'].strip()
    if not repo_url.startswith('https://github.com/'):
        return jsonify({'error': 'URL must start with https://github.com/'}), 400

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            build_mgr = BuildManager()
            analysis = build_mgr.analyze_repository(repo_url, temp_dir)
            return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/build', methods=['POST'])
def start_build():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing repository URL'}), 400
    
    build_id = f"build_{int(time.time())}"
    build_status[build_id] = {'status': 'queued', 'progress': 0}
    
    # Start build
    try:
        build_mgr = BuildManager()
        result = build_mgr.build_executable(data)
        build_status[build_id] = {
            'status': 'completed' if result['success'] else 'failed',
            'progress': 100,
            'result': result
        }
    except Exception as e:
        build_status[build_id] = {'status': 'failed', 'error': str(e)}
    
    return jsonify({'build_id': build_id, 'status': build_status[build_id]['status']})

@app.route('/api/status/<build_id>')
def get_build_status(build_id):
    return jsonify(build_status.get(build_id, {'status': 'not_found'}))

@app.route('/api/download/<build_id>')
def download_build(build_id):
    status = build_status.get(build_id)
    if not status or status['status'] != 'completed':
        return jsonify({'error': 'Build not ready'}), 404
    
    result = status.get('result', {})
    file_path = result.get('file_path')
    if not file_path or not Path(file_path).exists():
        return jsonify({'error': 'File missing'}), 404
    
    return send_file(file_path, as_attachment=True, download_name=result.get('filename'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)