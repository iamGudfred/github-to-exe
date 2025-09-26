# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Flexible donation system with multiple payment options (Stripe, PayPal, Paystack)
- Support for custom donation amounts and preset values ($5, $7, $10, $25, $50)
- Comprehensive input validation for payment processing
- Professional open-source documentation (CODE_OF_CONDUCT, SECURITY, etc.)
- GitHub badges and professional repository structure

### Changed
- Enhanced environment variable loading with multiple fallback strategies
- Improved error handling and security validation
- Updated UI with consistent hover effects and styling

### Fixed
- Python-dotenv dependency issue for deployment
- Payment validation edge cases and security vulnerabilities
- CSS styling consistency across payment and header icons

## [1.0.0] - 2025-09-26

### Added
- Initial release of GitHub-to-EXE converter
- Web-based interface for converting Python repositories to executables
- PyInstaller integration for Windows executable generation
- Basic security scanning of Python code
- Docker containerization support
- Flask backend with REST API endpoints
- Real-time build progress tracking

### Security
- Basic regex-based code scanning for potentially dangerous patterns
- Input validation for GitHub repository URLs
- Sandboxed build environment

[Unreleased]: https://github.com/iamGudfred/github-to-exe/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/iamGudfred/github-to-exe/releases/tag/v1.0.0