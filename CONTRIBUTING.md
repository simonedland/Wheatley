# Contributing to Wheatley

Thanks for thinking about improving Wheatley. Collaboration is encouraged, but remember: GLaDOS is watching.

## Getting Started
1. **Fork the repository** and create a feature branch off `main`.
2. **Install dependencies** with:
   ```bash
   python install_prerequisites.py
   ```
3. **Run the tests**:
   ```bash
   pytest -q
   ```
   It's strongly advised to run tests locally, but you may open a pull request before they pass.

## Code Standards
- Every change must comply with our Flake8 configuration. The `code-quality` workflow runs flake8 with bugbear, docstring, naming, and complexity checks.
- Pull requests targeting `main` fail automatically if flake8 reports even a single issue. No mercy.
- Include docstrings for all public classes, functions, and methods, and keep comments concise but explanatory.

## Pull Requests
1. Keep your feature branch up to date with `main` and squash trivial commits.
2. Open a pull request targeting `Test` for review and discussion.
3. All tests and the `code-quality` workflow must pass before anything merges.
4. After the PR to `Test` is approved and merged, open a follow‑up PR from `Test` to `main`.
5. A CODEOWNER must approve that final PR to `main`.

Follow these steps and your PR will glide through like a portal. Skip them and the turret chorus will sing.

