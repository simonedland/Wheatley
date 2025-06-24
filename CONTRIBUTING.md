# Contributing to Wheatley

Thank you for considering contributing to Wheatley! This project is still evolving and there are many rough edges to polish. We welcome community contributions of all kinds. Before submitting a pull request, please follow these guidelines to ensure a smooth development process.

## Getting Started

1. **Fork the repository** and create your branch from `main`.
2. **Install dependencies** using the helper script:

   ```bash
   python install_prerequisites.py
   ```
   This installs the packages listed in `wheatley/requirements.txt`.
3. **Run the tests** to make sure everything works:

   ```bash
   pytest -q
   ```

## Coding Standards

- Include Python docstrings for all public classes, functions, and methods.
- Add inline comments explaining why complex logic is necessary.
- Keep code style consistent with the existing project.

## Documentation

- Update or create Markdown documentation whenever you add a new feature.
- If adding files under `docs/`, update the "Documented Features" list in `AGENTS.md`.

## Pull Requests

1. Ensure your branch is up to date with `main`.
2. Provide a clear description of your changes and reference any relevant issues.
3. Confirm that all tests pass before submitting the pull request.
4. Be responsive to review feedback and update your PR as needed.

Thank you for helping improve Wheatley! Your ideas, bug reports, and code contributions all make the project better for everyone.
