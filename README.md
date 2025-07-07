# Wheatley

Wheatley is an experimental voice assistant built with open‑source tools. The project is evolving quickly, so expect the occasional portal-induced glitch. Contributions are welcome as long as they follow our strict guidelines.

## Quick Start
1. Copy `wheatley/config/config.example.yaml` to `wheatley/config/config.yaml` and tweak settings.
2. Run the setup script:
   ```powershell
   .\system check.ps1
   ```
   This verifies Python, creates the virtual environment, installs requirements and runs initial tests.
3. Activate the environment when needed:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   Deactivate with `deactivate`.
4. Launch Wheatley:
   ```bash
   python -m wheatley
   ```

## Development Workflow
Our `code-quality` pipeline runs flake8 with bugbear, docstring, naming and complexity checks. If it finds even one issue, PRs into `main` are rejected. Run tests with `pytest -q` and lint locally before pushing.

Develop on a feature branch and open a pull request into `Test`. That branch runs the same pipeline as `main`, giving you a safe place to squash flake8 issues and test failures.
Once `Test` is green, open a follow‑up PR from `Test` to `main` for final approval.

A CODEOWNER must approve any pull request to `main`. Until tests and lint are clean, merging is impossible—no amount of pleading with GLaDOS will help.

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions.

## Code of Conduct
All testers must follow the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Breaking the rules may result in removal from the project.

## License
This project is licensed under the [MIT License](LICENSE).

## Attribution
If you reuse Wheatley, retain the license notice and link back here so others can find the original.

