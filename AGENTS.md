# AGENTS.md

## 1. Overview  
This file defines documentation requirements and best practices for all coding agents. Every agent must generate and maintain both external Markdown documentation **and** inline code comments to ensure clarity, maintainability, and traceability.

---

## 2. External Markdown Documentation

### 2.1 Per-Feature Docs  
For each new feature or module, create a separate `*.md` under `docs/`:
- **Naming**:  
  `docs/<feature-name>.md`  
  e.g. `docs/user-authentication.md`, `docs/data-exporter.md`
- **Structure**:
  ```markdown
  # <Feature Name>

  ## Purpose
  A brief description of what this feature does and why it exists.

  ## Usage
  - Installation or enablement steps.
  - Configuration options (with defaults).
  - CLI or API examples.

  ## Internals
  - High-level architecture or flow diagram (ASCII or embedded image).
  - Key components / classes / functions.
  - Data schemas or interface contracts.

  ## Examples
  ```js
  // Code snippet demonstrating typical usage
  ```
  ```

### 2.2 Documented Features List  
Maintain a “Documented Features” section in this file. Update whenever you add/remove a `docs/*.md`:
```markdown
## Documented Features
- [architecture_overview](docs/architecture_overview.md)
- [Code_logic](docs/Code_logic.md)
- [hardware_command_flow](docs/hardware_command_flow.md)
- [LLM_logic](docs/LLM_logic.md)
- [long-term-memory](docs/long-term-memory.md)
- [present-timeline](docs/present-timeline.md)
- [speaker-warmup](docs/speaker-warmup.md)
- [timing-logging](docs/timing-logging.md)
- [tts_and_hotword_flow](docs/tts_and_hotword_flow.md)
- [Wiering_diagram](docs/Wiering_diagram.md)
```

---

## 3. Inline Code Documentation

### 3.1 Docstrings & Comments

* **Functions / Methods**
  Every public function or method must have a docstring immediately preceding its signature, in the project’s style (e.g. Python triple-quote, JSDoc, JavaDoc).

  > **Note:**  
  > _For this Python-based project, use Python triple-quoted docstrings for all public functions, methods, and classes._

  ```python
  def fetch_user(id: int) -> User:
      """
      Fetch a User record by ID.

      Args:
          id (int): Unique identifier of the user.
      Returns:
          User: Populated User object.
      Raises:
          NotFoundError: If no user with given ID exists.
      """
      ...
  ```

* **Classes**
  Include a class-level docstring describing responsibility and usage:

  ```js
  /**
   * Manages connection pooling to the database.
   *
   * @param {Object} config
   * @param {string} config.host
   * @param {number} config.port
   */
  class ConnectionPool { … }
  ```

* **Inline Comments**
  Explain *why* something is done (not *what* the code does):

  ```java
  // Use a linked list here because insertions at head are O(1).
  LinkedList<Node> list = new LinkedList<>();
  ```

### 3.2 TODO / FIXME

Mark temporary hacks or future work:

```go
// TODO: handle pagination once API supports cursors
```

---

## 4. Documentation Workflow

1. **Plan**

   * Identify new modules/features before coding.
   * Stub out corresponding `docs/*.md` with headings.

2. **Implement**

   * Write code and inline docs in tandem.
   * Commit only when docstrings and comments are complete.

3. **Review**

   * In PR reviews, verify:

     * Every public function/class has a docstring.
     * New `docs/*.md` files accurately describe the feature.
     * Examples are tested and up-to-date.
     * This `AGENTS.md` “Documented Features” list is updated.

4. **Publish**

   * Merge to `main`.
   * If using a docs-site generator, confirm pages render without errors.

---

## 5. Templates & Helpers

### 5.1 Markdown Front Matter (Optional)

If your docs site uses front matter, each `*.md` should start with:

<!-- (Add your front matter template here if needed) -->

### 5.2 Code Snippet Blocks

Always specify language for syntax highlighting:

```python
# example code here
```

### 5.3 Diagrams & Images

* Place assets under `docs/assets/<feature-name>/`.
* Reference as:

  ```markdown
  ![Flow chart](assets/<feature-name>/flow.png)
  ```

---

## 6. Enforcing Consistency

* **Linters / CI**

  * Enable a docs linter to catch missing front-matter or broken links.
  * Enforce presence of docstrings with code linters (e.g. ESLint, flake8-docstrings).

* **Review Checklist**

  * [ ] All public interfaces documented.
  * [ ] Example usages included.
  * [ ] External docs created/updated.
  * [ ] Changelog entry added if behavior changed.
