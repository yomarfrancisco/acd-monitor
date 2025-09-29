# Contributing to ACD

Thank you for your interest in contributing to the Algorithmic Coordination Diagnostic (ACD) project!

## Development Guidelines

### Code Standards
- Follow Python PEP 8 for backend code
- Use TypeScript for frontend development
- Include comprehensive tests for new features
- Document all public APIs and functions

### Code Formatting
- **Pre-commit hooks**: Install and run pre-commit hooks to ensure consistent formatting:
  ```bash
  pre-commit install
  pre-commit run --all-files
  ```
- **Black**: Python code is automatically formatted with Black (line length: 100)
- **Flake8**: Python linting is enforced for `backend/` and `src/` directories
- **Line endings**: All files use LF line endings (enforced via `.gitattributes`)
- **Tool versions**: CI uses pinned versions (Black 24.8.0, Flake8 7.1.0) for deterministic builds

### Pull Request Process
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Testing
- Run unit tests: `python -m pytest src/tests/`
- Run integration tests: `python -m pytest src/tests/integration/`
- Ensure all tests pass before submitting PR

### Documentation
- Update relevant documentation files
- Include examples for new features
- Maintain consistency with existing style

## Questions?

Open an issue for questions, bug reports, or feature requests.
