# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\assistant\assistant.py
Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

This script provides conversation management utilities for an assistant called "Wheatley." Its main role is to maintain a bounded (limited-length) conversation history between a user and the assistant, handle memory management (including a slot for long-term memory), and support debugging by printing the conversation in a readable format. It is designed to be used as part of a larger assistant or chatbot system.

---

## **Main Class and Responsibilities**

### **ConversationManager**

This is the only class in the script and encapsulates all conversation management logic. Its responsibilities include:

- **Initializing the conversation buffer** with system messages and configuration.
- **Adding new messages** (from user or assistant) to the conversation.
- **Maintaining a fixed-size buffer** for recent conversation turns.
- **Managing a long-term memory slot** in the conversation.
- **Providing access to the current conversation** as a list of message dictionaries.
- **Pretty-printing the conversation** for debugging purposes.

---

## **Key Methods and Their Roles**

### **1. `__init__(self, max_memory=5)`**

- **Purpose:** Initializes the conversation manager.
- **Actions:**
  - Loads a system message template from a YAML configuration file (`config/config.yaml`).
  - Replaces placeholders (`<current_time>`, `<current_day>`) in the system message with the current date and day of the week.
  - Sets up the conversation buffer (`self.messages`) with:
    - The system message (with current time/day).
    - A placeholder for long-term memory (empty system message).
  - Sets the maximum number of user/assistant turns to remember (`max_memory`).

### **2. `add_text_to_conversation(self, role, text)`**

- **Purpose:** Adds a new message from a given role (user or assistant) to the conversation.
- **Actions:**
  - Refreshes the system message with the current time and day (re-reads config).
  - Appends the new message to the buffer.
  - Ensures that only the most recent `max_memory` user/assistant turns are kept (oldest are removed if over limit, always preserving the two system messages at the start).

### **3. `update_memory(self, memory_text)`**

- **Purpose:** Updates the long-term memory slot in the conversation.
- **Actions:**
  - If the slot does not exist, inserts it.
  - Otherwise, replaces its content with the new memory text.

### **4. `get_conversation(self)`**

- **Purpose:** Returns the current conversation buffer as a list of message dictionaries.
- **Actions:** Simple getter for `self.messages`.

### **5. `print_memory(self)`**

- **Purpose:** Pretty-prints the current conversation buffer for debugging.
- **Actions:**
  - Uses ANSI color codes to differentiate roles (system, user, assistant).
  - Wraps message text for readability.
  - Prints each message with its index, role, and content.

---

## **Structure and Component Interaction**

- **Initialization:** When a `ConversationManager` is created, it loads configuration and sets up the initial conversation buffer.
- **Adding Messages:** New messages are added via `add_text_to_conversation`, which also ensures the buffer does not exceed the specified memory size.
- **Memory Management:** The long-term memory slot can be updated independently of the main conversation turns.
- **Access and Debugging:** The current state of the conversation can be retrieved or printed for inspection.

---

## **External Dependencies**

- **Standard Library:** Uses `os`, `textwrap`, and `datetime` modules.
- **PyYAML:** Uses `yaml` for loading configuration files. This is an external dependency and must be installed (e.g., via `pip install pyyaml`).
- **Configuration File:** Expects a YAML file at `config/config.yaml` (relative to the script's parent directory). This file must contain an `assistant` section with a `system_message` key.

---

## **Configuration Requirements**

- **YAML Config:** The configuration file must be present and properly formatted. The `system_message` can include placeholders `<current_time>` and `<current_day>`, which are dynamically replaced with the current date and day.
- **Directory Structure:** The script assumes a specific directory structure for locating the config file.

---

## **Notable Algorithms and Logic**

- **Bounded Conversation Buffer:** The buffer always contains two system messages at the start (the main system message and the long-term memory slot), followed by up to `max_memory` user/assistant turns. When the buffer exceeds this size, the oldest user/assistant message is removed.
- **Dynamic System Message:** The system message is refreshed with the current time and day every time a new message is added, ensuring context is always up-to-date.
- **Long-term Memory Slot:** The second message in the buffer is reserved for long-term memory, which can be updated independently of the conversation flow.

---

## **Summary of Design**

- **Single Responsibility:** The `ConversationManager` is solely responsible for managing the conversation buffer.
- **Extensibility:** The design allows for easy extension, such as adding more memory slots or custom message roles.
- **Separation of Concerns:** Configuration loading, message management, and debugging output are cleanly separated within the class.
- **User-Friendly Debugging:** The pretty-printing method aids developers in understanding the current conversation state.

---

## **In Summary**

This script is a utility for managing the conversation history of an AI assistant, handling both short-term and long-term memory, with configuration-driven system messages that adapt to the current time and day. It relies on a YAML config file and the PyYAML library, and is designed for integration into a larger assistant framework. The logic ensures that the conversation context remains relevant and manageable, while providing tools for inspection and debugging.
