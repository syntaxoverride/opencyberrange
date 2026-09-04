# Contributing to OpenCyberRange

Thank you for your interest in contributing to OpenCyberRange.

## How to Contribute

### Reporting Bugs

Open an issue on GitHub with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Docker version, etc.)

### Feature Requests

Open an issue with the `enhancement` label describing:
- What you'd like to see
- Why it would be useful
- Any implementation ideas

### Code Contributions

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run validation: `python3 scripts/validate-lab.py labs/{Track}/{slug}/`
5. Commit with clear messages
6. Open a pull request against `main`

### Exercise Contributions

New exercise scenarios are especially welcome. Each exercise is a self-contained directory with a `lab.yaml`, a `docker-compose.yml`, and its container build files, so the simplest starting point is to copy an existing lab and adapt it.

To contribute an exercise:
1. Follow the directory structure of an existing lab
2. Build and test locally with `docker compose up`
3. Validate with `python3 scripts/validate-lab.py labs/{Track}/{slug}/`
4. Submit a pull request or upload via the Instructor Panel

### Documentation

Improvements to documentation, installation guides, and tutorials are always appreciated.

## Code of Conduct

Be respectful, constructive, and collaborative. This project exists to serve educators and students.

## License

By contributing, you agree that your contributions will be licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE), the same license as this project.
