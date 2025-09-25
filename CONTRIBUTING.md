# Contributing to GitHub-to-EXE

Thank you for considering contributing to this project! This tool helps users convert Python GitHub repositories into Windows executables.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/github-to-exe.git
   cd github-to-exe
   ```

3. **Set up development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt
   pip install pyinstaller
   ```

4. **Run tests** to ensure everything works:
   ```bash
   python -m pytest tests/ -v
   ```

5. **Start the development server**:
   ```bash
   python server.py
   ```

## Development Guidelines

### Code Quality
- Follow PEP 8 Python style guidelines
- Add type hints where appropriate
- Write clear, descriptive variable names
- Keep functions focused and single-purpose
- Add docstrings for all public functions and classes

### Testing
- Write tests for new features
- Ensure existing tests pass
- Use pytest for testing
- Aim for good test coverage

### Security
- This tool executes third-party code - security is critical
- Review any changes to security scanning patterns
- Never weaken security checks without thorough review
- Document security implications of changes

## Areas for Contribution

### High Priority
- **Multi-platform support**: Add Linux and macOS executable generation
- **Queue system**: Enable concurrent builds instead of single-threaded processing
- **Better dependency resolution**: Improve handling of complex Python projects
- **Enhanced security scanning**: More sophisticated code analysis

### Medium Priority
- **Build optimization**: Faster compilation times and smaller executables
- **Better error messages**: More helpful feedback for users
- **Logging improvements**: Better debugging and monitoring
- **API rate limiting**: Prevent abuse of the service

### Future Features
- **Multiple language support**: Support for Node.js, Go, Rust projects
- **Custom build configurations**: User-specified PyInstaller options
- **Build caching**: Avoid rebuilding unchanged repositories

## Submitting Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the guidelines above

3. **Add tests** for new functionality

4. **Run the test suite**:
   ```bash
   python -m pytest tests/ -v
   ```

5. **Commit your changes** with clear messages:
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** on GitHub with:
   - Clear title and description
   - List of changes made
   - Any breaking changes noted
   - Test results

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn and contribute
- Report issues through proper channels

## Questions?

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Security**: Email security concerns privately to gprebbiemensah@gmail.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.