# GitHub to EXE Converter

A web-based tool that converts Python projects from GitHub repositories into Windows executable files. This project addresses the common frustration of users who want to run applications directly rather than dealing with source code.

## Overview

This tool provides a simple web interface where users can paste a GitHub repository URL and receive a compiled Windows executable file. It's designed for users who prefer ready-to-run applications over source code compilation.

## Features

- **Simple Web Interface**: Paste GitHub URL, click build, download executable
- **Security Scanning**: Basic security analysis of Python code before compilation
- **Real-time Progress**: Live updates during the build process
- **Automatic Packaging**: Creates downloadable ZIP files with executables
- **Open Source**: Full source code available for transparency and security auditing

## How It Works

1. **Repository Analysis**: Clones the GitHub repository and analyzes Python files
2. **Entry Point Detection**: Automatically finds main.py, app.py, or other entry points
3. **Security Scanning**: Performs basic security checks on the codebase
4. **Compilation**: Uses PyInstaller to create Windows executable
5. **Packaging**: Creates downloadable ZIP file with the executable

## Requirements

- Python 3.8+
- Git
- PyInstaller
- Flask and dependencies (see requirements.txt)

## Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/iamGudfred/github-to-exe.git
   cd github-to-exe
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   pip install pyinstaller
   ```

4. **Run the application**
   ```bash
   python server.py
   ```

5. **Access the web interface**
   Open your browser to `http://127.0.0.1:5001`

## Usage

1. Visit the web interface
2. Paste a GitHub repository URL containing Python code
3. Click "Create EXE File"
4. Wait for the build process to complete (2-5 minutes)
5. Download the resulting ZIP file
6. Extract and run the executable

### Example Repositories

The tool works best with Python projects that have clear entry points:
- Projects with `main.py`, `app.py`, or `run.py`
- Scripts with `if __name__ == "__main__":` blocks
- Simple command-line tools or GUI applications

## Security Considerations

**Important**: This tool compiles third-party code into executables. Only use with repositories you trust.

- The security scanner performs basic pattern matching for potentially dangerous code
- It is not a comprehensive security solution
- Always review the source code of repositories before building
- Generated executables will trigger Windows security warnings (normal for unsigned applications)

## Architecture

- **Frontend**: HTML/CSS/JavaScript interface for user interaction
- **Backend**: Flask web server handling API requests
- **Build System**: PyInstaller integration for executable generation
- **Security**: Basic regex-based code scanning

### API Endpoints

- `GET /` - Serves the web interface
- `POST /api/analyze` - Analyzes repository for buildability
- `POST /api/build` - Starts executable build process
- `GET /api/status/<build_id>` - Checks build progress
- `GET /api/download/<build_id>` - Downloads completed executable

## Limitations

- **Windows executables only**: Currently supports Windows .exe generation only
- **Python projects only**: Designed specifically for Python repositories
- **Single-threaded**: One build at a time per server instance
- **Basic security**: Simple pattern matching, not comprehensive code analysis
- **No dependency management**: Limited handling of complex project dependencies

## Contributing

Contributions are welcome! Areas for improvement:

- Multi-platform support (Linux, macOS)
- Better security scanning
- Queue system for concurrent builds
- Support for more programming languages
- Improved dependency resolution

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Godfred Prebbie Mensah**
- GitHub: [@iamGudfred](https://github.com/iamGudfred)
- Email: gprebbiemensah@gmail.com

## Acknowledgments

This project was inspired by user frustration with GitHub repositories containing only source code when users needed ready-to-run applications. It aims to bridge the gap between developers and end users.

## Support

- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and community support
- **Security**: Report security concerns privately via email

## Deployment

The application can be deployed on platforms supporting Python web applications:

- **Render** (recommended for free deployment)
- **Railway** (paid but reliable)
- **PythonAnywhere**
- **Self-hosted VPS**

For deployment instructions, see the [deployment guide](docs/deployment.md).

---

**Disclaimer**: This tool generates executable files from third-party source code. Users are responsible for ensuring the safety and legitimacy of repositories they choose to build. Always scan downloaded executables with antivirus software before running.