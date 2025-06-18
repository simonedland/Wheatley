# AI Summary

### C:\GIT\Wheatley\Wheatley\Wheatley\python\src\assistant\assistant.py
Certainly! Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script defines utilities for managing conversation history for an AI assistant named "Wheatley." Its primary goal is to maintain a bounded (limited-length) buffer of conversation turns between a user and the assistant, while also managing a system prompt that can be dynamically updated with the current time and day. This is useful for conversational AI systems that need to maintain context over several turns, but not indefinitely, and where the system prompt may need to reflect real-time information.

---

## **Main Class: `ConversationManager`**

This is the core class in the script. Its responsibilities include:

- **Maintaining Conversation History:** It keeps a list of message dictionaries, each with a `role` (system, user, assistant) and `content`.
- **Enforcing a Memory Limit:** Only a fixed number of recent user/assistant turns are kept (default is 5), plus the system prompt.
- **Dynamic System Prompt:** The system message is loaded from a YAML configuration file and dynamically updated to include the current time and day.
- **Debugging/Display:** Provides a method to pretty-print the conversation buffer for debugging.

---

## **Key Methods and Their Responsibilities**

### **1. `__init__(self, max_memory=5)`**

- **Purpose:** Initializes the conversation manager.
- **Actions:**
  - Loads the system message from a YAML config file (`config/config.yaml`).
  - Replaces placeholders (`<current_time>`, `<current_day>`) in the system message with the current time and day.
  - Initializes the conversation buffer with the system message as the first entry.
  - Sets the memory limit for user/assistant turns.

### **2. `add_text_to_conversation(self, role, text)`**

- **Purpose:** Adds a new message (from either user or assistant) to the conversation.
- **Actions:**
  - Reloads and refreshes the system message with the current time and day (ensuring it's always up-to-date).
  - Adds the new message to the buffer.
  - Ensures the buffer does not exceed the specified memory limit (removes oldest user/assistant messages as needed, always retaining the system message at the start).

### **3. `get_conversation(self)`**

- **Purpose:** Returns the current conversation buffer as a list of message dictionaries.
- **Usage:** This is likely used by other components (e.g., the assistant's response generator) to get the current conversation context.

### **4. `print_memory(self)`**

- **Purpose:** Pretty-prints the conversation buffer for debugging.
- **Features:**
  - Uses ANSI color codes to distinguish roles (system, user, assistant).
  - Wraps long lines for readability.
  - Prints each message with its index and role.

---

## **Structure and Component Interaction**

- **Initialization:** When a `ConversationManager` instance is created, it loads the system prompt from the configuration and prepares the initial conversation buffer.
- **Adding Messages:** Each time a user or assistant message is added, the system prompt is refreshed (to reflect the current time/day), and the buffer is updated.
- **Retrieving Conversation:** Other components (e.g., the AI model) can call `get_conversation()` to get the current context for generating responses.
- **Debugging:** Developers can call `print_memory()` to inspect the current state of the conversation buffer.

---

## **External Dependencies and Configuration**

- **YAML Configuration:** The script depends on a YAML file located at `config/config.yaml` (relative to the script's parent directory). This file must contain an `assistant` section with a `system_message` key, which can include placeholders for `<current_time>` and `<current_day>`.
- **Python Modules:** Uses standard libraries: `os`, `textwrap`, `yaml` (PyYAML, which must be installed), and `datetime`.
- **No External APIs:** The script does not directly call any external APIs, but is designed to be used as a utility within a larger assistant framework.

---

## **Notable Algorithms and Logic**

- **Dynamic System Prompt:** Each time a message is added, the system prompt is reloaded and updated with the current time and day. This ensures that the assistant always has up-to-date context about the current moment, which can be important for time-sensitive interactions.
- **Bounded Buffer:** The conversation buffer always contains the system message plus up to `max_memory` most recent user/assistant turns. This is managed by popping the oldest messages (excluding the system message) when the buffer exceeds the allowed size.
- **Pretty-Printing with Wrapping:** For debugging, the conversation is printed with color-coding and line-wrapping to ensure readability, especially for long messages.

---

## **Summary Table**

| Component           | Purpose/Responsibility                                              |
|---------------------|---------------------------------------------------------------------|
| `ConversationManager` | Main class for managing conversation history and system prompt      |
| `__init__`          | Loads system prompt, initializes buffer, sets memory limit           |
| `add_text_to_conversation` | Adds new message, refreshes system prompt, enforces buffer size |
| `get_conversation`  | Returns current conversation buffer                                 |
| `print_memory`      | Pretty-prints buffer for debugging                                  |
| **Config File**     | Supplies system prompt template (with time/day placeholders)         |
| **Dependencies**    | `os`, `textwrap`, `yaml`, `datetime`                                |

---

## **Summary**

This script provides a robust and configurable way to manage the conversation context for an AI assistant, with special attention to keeping the system prompt current and the conversation history bounded. It is designed for integration into a larger conversational AI system and relies on an external YAML configuration for flexibility. The code is modular, with clear separation of responsibilities, and includes developer-friendly debugging output.
