"""
GitHub-to-EXE Flask Web Application

This is the main web server that provides:
- Static file serving for the frontend
- REST API for repository analysis and building
- Build status tracking and downloads

Known Issues:
- In-memory build status (lost on restart)
- No rate limiting or concurrent build protection
- Basic error handling only
"""
import logging
import tempfile
import time
from pathlib import Path

from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv

# Load environment variables with fallback strategies
import os
def load_env_robust():
    """Load .env file with multiple fallback strategies"""
    env_paths = [
        # Strategy 1: Relative to current file (assumes backend/app.py structure)
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
        # Strategy 2: Current working directory
        os.path.join(os.getcwd(), '.env'),
        # Strategy 3: Parent of current working directory
        os.path.join(os.path.dirname(os.getcwd()), '.env'),
        # Strategy 4: Environment variable override
        os.environ.get('DOTENV_PATH', '')
    ]

    for env_path in env_paths:
        if env_path and os.path.exists(env_path):
            load_dotenv(env_path)
            return env_path

    # If no .env found, load_dotenv() will still work with system env vars
    load_dotenv()
    return None

env_path = load_env_robust()

from .build_manager import BuildManager, check_dependencies
from .config import Config
from .payments import create_stripe_payment, create_paypal_payment, create_paystack_payment

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure directories exist
Config.ensure_dirs()

app = Flask(__name__, static_folder="../frontend", static_url_path="")

# In-memory build status tracking
# TODO: Replace with persistent storage for production
build_status = {}

@app.route('/')
def index():
    return send_file("../frontend/index.html")

# Serve static files explicitly for better compatibility
@app.route('/css/<path:filename>')
def css_files(filename):
    return send_file(f"../frontend/css/{filename}")

@app.route('/js/<path:filename>')
def js_files(filename):
    return send_file(f"../frontend/js/{filename}")

@app.route('/assets/<path:filename>')
def asset_files(filename):
    return send_file(f"../frontend/assets/{filename}")

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

    # Additional validation
    if len(repo_url.split('/')) < 5:
        return jsonify({'error': 'Invalid GitHub URL format. Expected: https://github.com/username/repo'}), 400

    try:
        logger.info(f"Analyzing repository: {repo_url}")
        with tempfile.TemporaryDirectory() as temp_dir:
            build_mgr = BuildManager()
            analysis = build_mgr.analyze_repository(repo_url, temp_dir)
            logger.info(f"Analysis complete for {repo_url}: can_build={analysis.get('can_build', False)}")
            return jsonify(analysis)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Analysis failed for {repo_url}: {error_msg}")
        if 'not found' in error_msg.lower() or '404' in error_msg:
            return jsonify({'error': 'Repository not found or not accessible'}), 404
        elif 'timeout' in error_msg.lower():
            return jsonify({'error': 'Repository analysis timed out'}), 408
        else:
            return jsonify({'error': f'Analysis failed: {error_msg}'}), 500

@app.route('/api/build', methods=['POST'])
def start_build():
    """
    Start building executable from repository

    TODO: This should be async with proper queue management
    Currently blocks the entire server during build
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing repository URL'}), 400

    repo_url = data['url'].strip()
    force_build = data.get('force_build', False)  # Allow bypassing security

    if not repo_url.startswith('https://github.com/'):
        return jsonify({'error': 'URL must start with https://github.com/'}), 400

    # Check PyInstaller availability first
    if not check_dependencies():
        return jsonify({'error': 'PyInstaller not found. Install with: pip install pyinstaller'}), 500

    build_id = f"build_{int(time.time())}"
    build_status[build_id] = {'status': 'queued', 'progress': 0}

    try:
        logger.info(f"Starting build for: {repo_url}")
        build_mgr = BuildManager()
        result = build_mgr.build_executable(data, force_build=force_build)

        build_status[build_id] = {
            'status': 'completed' if result['success'] else 'failed',
            'progress': 100,
            'result': result
        }

        logger.info(f"Build {build_id} completed: {result.get('success', False)}")

    except Exception as e:
        logger.error(f"Build {build_id} failed: {str(e)}")
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

@app.route('/api/payment/stripe', methods=['POST'])
def create_stripe_checkout():
    """Create Stripe payment session"""
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'error': 'Missing required field: amount'}), 400

    amount = data['amount']

    result = create_stripe_payment(amount)
    if result['success']:
        return jsonify({'checkout_url': result['checkout_url']})
    else:
        return jsonify({'error': result['error']}), 500

@app.route('/api/payment/paypal', methods=['POST'])
def create_paypal_checkout():
    """Create PayPal payment"""
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'error': 'Missing required field: amount'}), 400

    amount = data['amount']

    result = create_paypal_payment(amount)
    if result['success']:
        return jsonify({'approval_url': result['approval_url']})
    else:
        return jsonify({'error': result['error']}), 500

@app.route('/api/payment/paystack', methods=['POST'])
def create_paystack_checkout():
    """Create Paystack payment for Mobile Money"""
    data = request.get_json()
    amount = data.get('amount', 50.00)  # Default 50 GHS
    # Generate unique anonymous email for each donation
    email = f'anonymous-{int(time.time())}@github-to-exe.com'

    result = create_paystack_payment(amount, 'GHS', email)
    if result['success']:
        return jsonify({'authorization_url': result['authorization_url']})
    else:
        return jsonify({'error': result['error']}), 500

@app.route('/success')
def payment_success():
    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                min-height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 60px 40px;
                text-align: center;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                max-width: 500px;
                margin: 20px;
            }
            .success-icon {
                font-size: 64px;
                color: #28a745;
                margin-bottom: 30px;
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
                font-size: 28px;
                font-weight: 600;
            }
            p {
                color: #666;
                font-size: 18px;
                line-height: 1.6;
                margin-bottom: 40px;
            }
            .back-btn {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                background: #667eea;
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .back-btn:hover {
                background: #5a6fd8;
                transform: translateY(-2px);
            }
        </style>
        <script>
            // Handle back button click for popup windows
            function goBack() {
                if (window.opener) {
                    window.opener.location.href = '/';
                    window.close();
                } else {
                    window.location.href = '/';
                }
            }
        </script>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">
                <i class="fas fa-check-circle"></i>
            </div>
            <h1>Thank you for your support!</h1>
            <p>Your donation will help us upgrade to better hosting for faster builds and serve the community better.</p>
            <button onclick="goBack()" class="back-btn">
                <i class="fas fa-arrow-left"></i>
                Back to GitHub-to-EXE Converter
            </button>
        </div>
    </body>
    </html>
    """

@app.route('/cancel')
def payment_cancel():
    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                min-height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 60px 40px;
                text-align: center;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                max-width: 500px;
                margin: 20px;
            }
            .cancel-icon {
                font-size: 64px;
                color: #ffc107;
                margin-bottom: 30px;
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
                font-size: 28px;
                font-weight: 600;
            }
            p {
                color: #666;
                font-size: 18px;
                line-height: 1.6;
                margin-bottom: 40px;
            }
            .back-btn {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                background: #667eea;
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .back-btn:hover {
                background: #5a6fd8;
                transform: translateY(-2px);
            }
        </style>
        <script>
            // Handle back button click for popup windows
            function goBack() {
                if (window.opener) {
                    window.opener.location.href = '/';
                    window.close();
                } else {
                    window.location.href = '/';
                }
            }
        </script>
    </head>
    <body>
        <div class="container">
            <div class="cancel-icon">
                <i class="fas fa-times-circle"></i>
            </div>
            <h1>Payment Cancelled</h1>
            <p>No worries! You can still support us by starring the project on GitHub or trying other payment methods.</p>
            <button onclick="goBack()" class="back-btn">
                <i class="fas fa-arrow-left"></i>
                Back to GitHub-to-EXE Converter
            </button>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Use environment variable for debug mode (secure for production)
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='127.0.0.1', port=5001)