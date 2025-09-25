#!/usr/bin/env python3
"""
GitHub-to-EXE Server Launcher

Simple launcher script that starts the Flask application
"""
if __name__ == '__main__':
    from backend.app import app

    print("🚀 Starting GitHub-to-EXE Server")
    print("📍 Server will be available at: http://127.0.0.1:5001")
    print("⚠️  WARNING: This server has no rate limiting or security controls")
    print("   Only use with repositories you trust!")
    print()

    app.run(debug=True, host='127.0.0.1', port=5001)