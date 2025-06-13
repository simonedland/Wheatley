# Long Term Memory

## Purpose
Provide persistent storage so Wheatley can recall facts between sessions.

## Usage
- The LLM invokes the `write_long_term_memory` tool with a JSON object under the `data` field.
- Stored entries accumulate in `long_term_memory.json`.
- `read_long_term_memory` returns the list of stored objects.

## Internals
- `utils.long_term_memory` defines `append_memory` and `read_memory`.
- `Functions` exposes `write_long_term_memory` and `read_long_term_memory` to the LLM.
- Tool definitions live in `llm_client_utils.build_tools()`.

## Examples
```python
from utils.long_term_memory import append_memory, read_memory

append_memory({"note": "Remember to buy cake"})
print(read_memory())
```
