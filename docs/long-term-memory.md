# Long Term Memory

## Purpose
Provide persistent storage so Wheatley can recall facts between sessions.

## Usage
- The LLM invokes the `add_long_term_memory` tool with a text string and an `index`.
  The entry at that index is replaced or appended if the index is out of range.
- The file `long_term_memory.txt` is completely overwritten whenever a new entry is added so stale data is removed.
- Memory access is silent; Wheatley no longer speaks when storing or retrieving data.
- The assistant maintains a single memory message right after the system prompt labelled **LONG TERM MEMORY** and updates it every interaction.
- The memory is also loaded once at startup so Wheatley begins each session aware of past entries.
- When entries are written or edited they are compressed to keep only the most important content.

## Internals
- `utils.long_term_memory` defines `overwrite_memory`, `append_memory`, `read_memory`, `edit_memory` and helper compression functions.
- `Functions` exposes `add_long_term_memory` and `read_long_term_memory` to the LLM.
- Tool definitions live in `llm_client_utils.build_tools()`.

## Examples
```python
from utils.long_term_memory import overwrite_memory, read_memory, edit_memory

overwrite_memory("Remember to buy cake")
print(read_memory())
edit_memory(0, "Updated entry")
```
