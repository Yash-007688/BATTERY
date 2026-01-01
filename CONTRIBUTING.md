# Contributing to Battery Monitor

Thank you for your interest in contributing to the Battery Monitor project! This document outlines the guidelines for contributing to this repository.

## Prerequisites

- **Python 3.9+**: The application is built using Python 3.9 and above
- **Operating System**: Windows (primary development platform), with some cross-platform support
- **ADB Tools** (optional): For Android phone battery monitoring
- **Git**: For version control

## Setup Instructions

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/BATTERY.git
   cd BATTERY
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the setup script:**
   ```bash
   setup.bat  # On Windows
   ```
   
   **Note**: If the setup.bat script encounters dependency installation failures, it will prompt you to decide whether to continue. Some features may not work if dependencies fail to install.

4. **Run the application:**
   ```bash
   python app.py --web  # With web interface
   # or
   python app.py  # Console only
   ```

## Branching and PR Workflow

1. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-description
   ```

2. Make your changes and commit them with clear, descriptive messages:
   ```bash
   git add .
   git commit -m "Add clear description of changes"
   ```

3. Push your branch and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Ensure your PR:
   - Addresses a specific issue or adds clear value
   - Includes appropriate tests (if applicable)
   - Follows the coding standards below
   - Links to any related issues

## Coding Standards

- **Python**: Follow PEP 8 style guidelines
- **Documentation**: Include docstrings for all public functions and classes
- **Testing**: Add tests for new functionality (if applicable)
- **Code Formatting**: Use consistent indentation (4 spaces)
- **Comments**: Use clear, concise comments for complex logic
- **File Naming**: Use lowercase with underscores for Python files

## How to Pick Up Issues

1. Look for issues labeled `good first issue` if you're new to the project
2. Check issues labeled `help wanted` for areas where the team needs assistance
3. Comment on the issue you'd like to work on to let others know
4. If you have questions, ask in the issue comments
5. Submit your PR when ready and link it to the issue

## Communication

- Use issue comments for technical discussions
- For general questions, open a new issue with the "question" label
- Be respectful and constructive in all interactions
- If you're stuck, don't hesitate to ask for help

## Areas of Contribution

We welcome contributions in these areas:
- Bug fixes
- Code refactoring
- UI/UX improvements
- Documentation
- Testing
- Feature enhancements
- Performance improvements

## Credit Policy

- All contributors will be credited in the commit history
- Major contributors may be acknowledged in the README
- Pull requests will be reviewed promptly
- Your contribution is valued regardless of size

## Getting Help

If you need help:
1. Check the existing issues to see if your question has been addressed
2. Open a new issue with the "question" label
3. Include details about your environment and steps to reproduce if reporting bugs

Thank you for contributing to Battery Monitor!