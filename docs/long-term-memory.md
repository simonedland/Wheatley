# Long Term Memory

## Purpose
Provide persistent storage so Wheatley can recall facts between sessions.

## Usage
- The LLM invokes the `write_long_term_memory` tool with a JSON object under the `data` field.
- To modify an existing entry the LLM can call `edit_long_term_memory` with an `index` and new `data`.
- Stored entries accumulate in `long_term_memory.json`.
- Memory access is silent; Wheatley no longer speaks when storing or retrieving data.
- The assistant maintains a single memory message right after the system prompt labelled **LONG TERM MEMORY** and updates it every interaction.
- The memory is also loaded once at startup so Wheatley begins each session aware of past entries.
- When entries are written or edited they are compressed to keep only the most important content.

## Internals
- `utils.long_term_memory` defines `append_memory`, `read_memory`, `edit_memory` and helper compression functions.
- `Functions` exposes `write_long_term_memory`, `edit_long_term_memory` and `read_long_term_memory` to the LLM.
- Tool definitions live in `llm_client_utils.build_tools()`.

## Examples
```python
from utils.long_term_memory import append_memory, read_memory, edit_memory

append_memory({"note": "Remember to buy cake"})
print(read_memory())
edit_memory(0, {"note": "Updated entry"})
```
