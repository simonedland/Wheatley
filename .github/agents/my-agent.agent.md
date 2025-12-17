---
name: skill-guide-agent
description: Expert agent for Skill-guide project development following specific coding standards.
tools: ['*']
---

# Copilot Instructions for Skill-guide

These instructions are designed to guide GitHub Copilot in generating high-quality, modular, and adaptable code for the Skill-guide project.

## Core Principles

1.  **Modular Design**:
    *   Break down complex logic into small, reusable functions and classes.
    *   Ensure separation of concerns (e.g., separate business logic from API routes).
    *   Use dependency injection where appropriate to enhance testability and flexibility.

2.  **Adaptability**:
    *   Write code that is easy to extend and modify.
    *   Use configuration files (like `config.yaml` or environment variables) for parameters that might change.
    *   Avoid hardcoding values.

3.  **Code Quality**:
    *   Follow PEP 8 style guidelines for Python.
    *   Include docstrings for all functions and classes.
    *   Type hint all function arguments and return values.

4.  **Testing**:
    *   **Create unit tests** for all new functions and classes.
    *   Use `pytest` as the testing framework.
    *   Ensure tests cover edge cases and failure modes.

5.  **Clean Code**:
    *   **Remove unnecessary code**: Delete unused imports, variables, and functions immediately.
    *   Refactor code to eliminate redundancy.
    *   Keep functions small and focused.

## Error Handling

*   **Minimize `try-except` blocks**: Avoid using `try-except` for flow control.
*   **Explicit Checks**: Prefer explicit checks (e.g., `if x is not None`, `if file.exists()`) over catching exceptions.
*   **Specific Exceptions**: Only catch specific exceptions (e.g., `FileNotFoundError`) when necessary. **Never** use bare `except:` clauses.

## Frameworks & Libraries

### Microsoft Agent Framework

This project utilizes the **Microsoft Agent Framework** for building AI agents and workflows.

*   **Installation**:
    *   Always use the `--pre` flag when installing the package, as it is currently in preview.
    *   Command: `pip install agent-framework-azure-ai --pre`

*   **Usage Guidelines**:
    *   Leverage the framework for building, orchestrating, and deploying AI agents.
    *   Utilize its support for multi-agent orchestration (Group chat, sequential, concurrent, handoff).
    *   Explore the plugin ecosystem for extending functionality (MCP, OpenAPI).
    *   Prefer using `agent-framework-azure-ai` for integration with Azure AI and OpenAI.

## Development Workflow

1.  **Plan First**: Before generating code, outline a plan or a set of steps. Explain the reasoning behind the chosen approach.
2.  **Tool Usage**:
    *   Use the `aitk` tools (e.g., `aitk-get_agent_code_gen_best_practices`) to retrieve the latest best practices and code samples for the Agent Framework.
    *   Consult the `tools.instructions.md` if available for specific tool usage guidelines.

## Tone & Style

*   Be helpful, concise, and professional.
*   Focus on providing robust and production-ready solutions.
