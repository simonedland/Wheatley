# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\utils\long_term_memory.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script provides a simple, persistent, JSON-based storage mechanism for an "assistant" application. It allows the assistant to store, retrieve, and manage a list of memory entries (as dictionaries), which are saved to and loaded from a JSON file on disk. This enables the assistant to maintain long-term memory across sessions.

---

## **Main Components**

### **Global Constants**

- **MEMORY_FILE**:  
  This is the default path to the JSON file used for storing the assistant's memory. It is located two directories above the script's location, named `long_term_memory.json`.

---

### **Functions**

#### 1. **read_memory**
- **Purpose**:  
  Reads and returns all memory entries from the JSON file at the specified path.
- **Behavior**:  
  - If the file does not exist, returns an empty list.
  - If the file exists, attempts to load and return its contents as a list of dictionaries.
  - If any error occurs (e.g., invalid JSON), returns an empty list.

#### 2. **_compress_entry**
- **Purpose**:  
  Compresses a memory entry by truncating any string values longer than a specified maximum length (default 200 characters).
- **Behavior**:  
  - For each key-value pair in the entry, if the value is a string and exceeds `max_len`, it is truncated and suffixed with "...".
  - Returns a new dictionary with the possibly truncated values.

#### 3. **_optimize_memory**
- **Purpose**:  
  Ensures the memory list does not exceed a maximum number of entries (default 100).
- **Behavior**:  
  - If the list is longer than `max_entries`, only the most recent entries (the last `max_entries` items) are kept.
  - Returns the trimmed list.

#### 4. **overwrite_memory**
- **Purpose**:  
  Replaces the entire memory file with a single new entry.
- **Behavior**:  
  - Compresses the entry.
  - Optimizes the memory (though with one entry, this is trivial).
  - Writes the entry as a single-item list to the JSON file, overwriting any existing content.
  - Prints an error message if writing fails.

#### 5. **edit_memory**
- **Purpose**:  
  Edits or appends a memory entry at a specified index.
- **Behavior**:  
  - Reads the current memory list.
  - If the index is valid (within bounds), replaces the entry at that index.
  - If the index is out of bounds, appends the entry to the end.
  - Compresses the entry before storing.
  - Optimizes the memory list to ensure it does not exceed the maximum allowed entries.
  - Writes the updated list back to the JSON file.
  - Returns `True` if successful, `False` otherwise, printing an error message on failure.

---

## **Structure and Interactions**

- The script is function-based, with no classes.
- All functions interact via the shared memory file, whose path can be overridden but defaults to `MEMORY_FILE`.
- Helper functions (`_compress_entry`, `_optimize_memory`) are used internally to maintain data consistency and size constraints.
- The main workflow is:
  - Read memory from disk.
  - Modify or replace entries as needed.
  - Compress and optimize the memory list.
  - Write the updated list back to disk.

---

## **External Dependencies**

- **Standard Library Only**:  
  - `json` for serialization/deserialization.
  - `os` for file path manipulation and existence checks.
  - `typing` for type hints.

- **No external packages or APIs** are required.

---

## **Configuration Requirements**

- The script expects to have read/write access to the directory containing the `long_term_memory.json` file.
- The file path can be overridden in function calls if needed.

---

## **Notable Algorithms and Logic**

- **Compression**:  
  Long string values in memory entries are truncated to avoid excessive file size and improve readability.

- **Optimization**:  
  The memory list is trimmed to a maximum number of entries (default 100), ensuring the file does not grow indefinitely.

- **Fault Tolerance**:  
  - Reading functions handle missing files and invalid JSON gracefully, returning empty lists.
  - Writing functions catch exceptions and print error messages, preventing crashes.

- **Flexible Editing**:  
  The `edit_memory` function allows both replacement and appending, depending on whether the specified index exists. This makes it robust against out-of-bounds edits.

---

## **Summary Table**

| Function         | Responsibility                                             |
|------------------|-----------------------------------------------------------|
| read_memory      | Load all memory entries from disk                         |
| _compress_entry  | Truncate long string values in a memory entry             |
| _optimize_memory | Trim memory list to a maximum number of entries           |
| overwrite_memory | Replace all memory with a single new entry                |
| edit_memory      | Replace or append a memory entry at a specified index     |

---

## **Conclusion**

This script provides a lightweight, robust, and persistent memory storage mechanism for an assistant application, using a JSON file as the backend. It ensures data size is controlled, handles errors gracefully, and provides flexible interfaces for reading, writing, and editing memory entries. All logic is implemented using Python's standard library, with no external dependencies.

### C:\GIT\Wheatly\Wheatley\Wheatley\utils\timing_logger.py
Certainly! Here’s a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script is a lightweight utility designed to **capture, store, and export execution timing information** for various operations within a Python application. It allows developers to measure how long specific code sections take to run, accumulate these measurements in memory, and optionally export them to a JSON file for later analysis.

---

## **Main Components**

### **Global Data Structure**

- **`timings`**:  
  A global, in-memory list that stores dictionaries, each representing a single timing entry. Each entry contains:
  - The name/label of the operation.
  - The start and end times (in ISO 8601 format, UTC).
  - The duration in milliseconds.

---

### **Functions**

#### 1. **`clear_timings(path: str = "timings.json")`**

- **Purpose**:  
  Resets the timing data both in memory and on disk.
- **Responsibilities**:
  - Clears the `timings` list, removing all accumulated timing entries.
  - Deletes the specified JSON file (default: `timings.json`) if it exists, to ensure no stale timing data remains.
  - Handles any file deletion errors gracefully, printing an error message if deletion fails.

#### 2. **`record_timing(name: str, start: float)`**

- **Purpose**:  
  Records a new timing entry for a completed operation.
- **Responsibilities**:
  - Accepts a descriptive name for the operation and the start timestamp (as returned by `time.time()`).
  - Captures the current time as the end timestamp.
  - Calculates the duration in milliseconds.
  - Converts start and end times to UTC ISO 8601 strings.
  - Appends a dictionary with all this information to the global `timings` list.
  - Captures the name of the calling thread for multithreaded timing.
  - Uses a lock to ensure thread-safe writes.

#### 3. **`export_timings(path: str = "timings.json")`**

- **Purpose**:  
  Persists all accumulated timing data to a JSON file.
- **Responsibilities**:
  - Writes the contents of the `timings` list to the specified file in a human-readable, indented JSON format.
  - Prints a message indicating where the timings are being exported.

---

## **Structure and Interaction**

- **Data Flow**:  
  - Timing entries are accumulated in the `timings` list via repeated calls to `record_timing`.
  - `clear_timings` can be called to reset both in-memory and on-disk timing data.
  - `export_timings` writes the current state of `timings` to disk for external analysis.

- **Typical Usage Pattern**:
  1. At the start of a code section, record the start time (`start = time.time()`).
  2. After the section completes, call `record_timing` with the operation name and the start time.
  3. Periodically or at the end of the application, call `export_timings` to save the results.
  4. Use `clear_timings` as needed to reset the state.

---

## **External Dependencies and Configuration**

- **Standard Library Only**:  
  - Uses only Python’s standard library modules: `time`, `datetime`, `json`, `os`, and `typing`.
  - No third-party dependencies.

- **Configuration**:  
  - File paths for exporting and clearing timings are configurable via function arguments (default: `"timings.json"`).

---

## **Notable Logic and Algorithms**

- **Timing Calculation**:  
  - Uses `time.time()` for high-resolution wall-clock timing (in seconds).
  - Duration is calculated as the difference between end and start times, converted to milliseconds for precision.

- **Timestamp Formatting**:
  - Converts timestamps to UTC and formats them as ISO 8601 strings using `datetime.utcfromtimestamp().isoformat()`. This ensures compatibility and readability for downstream tools.

- **Error Handling**:
  - File deletion in `clear_timings` is wrapped in a try-except block to handle and report any issues gracefully.

- **Thread Safety**:
  - A `threading.Lock` guards access to the shared `timings` list so that concurrent threads can record timings without race conditions.

---

## **Summary Table**

| Component         | Type      | Responsibility                                         |
|-------------------|-----------|-------------------------------------------------------|
| `timings`         | List      | Stores all timing entries in memory                   |
| `clear_timings`   | Function  | Resets timings in memory and deletes timing file      |
| `record_timing`   | Function  | Records a timing entry with duration and timestamps   |
| `export_timings`  | Function  | Exports all timings to a JSON file                    |

---

## **Conclusion**

This script provides a simple, reusable mechanism for **timing and logging the duration of operations** within a Python application. It is self-contained, easy to integrate, and requires no external dependencies. The design is straightforward, using global state for simplicity, and is suitable for small to medium-scale applications or for debugging and profiling purposes.
