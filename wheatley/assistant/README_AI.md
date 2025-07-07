# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\assistant\assistant.py
Here is a detailed summary and analysis of the provided Python script:

---

## **Overall Purpose**

The script defines utilities for managing conversation history in the context of an assistant called "Wheatley". Its main goal is to maintain a bounded, structured, and up-to-date conversation buffer between a user and the assistant, including system-level context and long-term memory. This is crucial for conversational AI applications, where context management and memory are essential for coherent and context-aware interactions.

---

## **Main Class: `ConversationManager`**

### **Responsibilities**

- **Conversation Buffer:** Maintains a list of messages representing the conversation history, including system prompts, user inputs, and assistant responses.
- **System Message Handling:** Loads and dynamically updates a system message template from a configuration file, injecting current time and day.
- **Long-term Memory:** Supports a dedicated message slot for long-term memory, which can be updated independently.
- **History Boundedness:** Ensures the conversation history does not exceed a specified number of user/assistant turns.
- **Debugging:** Provides a method to pretty-print the current conversation buffer for inspection.

---

## **Structure and Component Interaction**

### **Initialization (`__init__`)**

- **Configuration Loading:** On instantiation, the class loads a YAML configuration file (`config.yaml`) located two directories up from the script, inside a `config` folder.
- **System Message:** Extracts a system message template from the config, replaces placeholders (`<current_time>`, `<current_day>`) with the current timestamp and weekday, and sets it as the first message in the buffer.
- **Long-term Memory Placeholder:** Adds a second system message as a placeholder for long-term memory.
- **Buffer Setup:** Initializes the buffer with the above two system messages. The rest of the buffer will be filled with user and assistant messages.

### **Adding Messages (`add_text_to_conversation`)**

- **Dynamic System Message:** Each time a new message is added, the system message is refreshed with the latest time and day.
- **Message Appending:** Appends the new message (from either user or assistant) to the buffer.
- **Buffer Trimming:** Ensures the buffer only retains the most recent `max_memory` user/assistant turns (plus the two system messages), discarding older messages as needed.

### **Long-term Memory (`update_memory`)**

- **Memory Slot:** Updates or sets the second message in the buffer to store long-term memory, which can be used for persistent context or facts.

### **Retrieving Conversation (`get_conversation`)**

- **Access:** Returns the current state of the conversation buffer as a list of message dictionaries.

### **Debugging (`print_memory`)**

- **Pretty Printing:** Prints the entire conversation buffer to the console with color-coded roles and wrapped text for readability, aiding debugging and inspection.

---

## **External Dependencies**

- **Standard Library:**
  - `os`: For file path manipulation.
  - `textwrap`: For formatting output.
  - `datetime`: For current time and day.
- **Third-party:**
  - `yaml`: For reading the configuration file. (Requires `PyYAML` to be installed.)

---

## **Configuration Requirements**

- **Config File:** Expects a YAML file at `../../config/config.yaml` relative to the script's location.
  - **Key:** The config must have an `assistant` section with a `system_message` string, which may contain `<current_time>` and `<current_day>` placeholders.

---

## **Notable Algorithms and Logic**

- **Dynamic System Message Replacement:** Each time the conversation is updated, the system message is refreshed with the current time and day, ensuring that the assistant's context is always up to date.
- **Bounded Buffer:** The buffer is kept at a fixed size (`max_memory` user/assistant turns + 2 system messages) by removing the oldest user/assistant messages as new ones are added.
- **Long-term Memory Slot:** A dedicated slot in the buffer for persistent context, separate from the rolling conversation history.
- **Pretty-printing Algorithm:** Uses color codes and text wrapping to display the conversation buffer in a readable format, distinguishing between system, user, and assistant roles.

---

## **Component Interaction**

- The class is self-contained and manages all aspects of conversation history.
- It interacts with the file system to load configuration and with the system clock for dynamic placeholders.
- The buffer structure is always: `[system message, long-term memory, ...recent conversation turns...]`.
- All methods operate on this shared buffer, ensuring consistency.

---

## **Summary Table**

| Component                | Purpose/Responsibility                                                                 |
|--------------------------|---------------------------------------------------------------------------------------|
| `__init__`               | Loads config, sets up system message, initializes buffer                              |
| `add_text_to_conversation` | Adds a message, refreshes system message, trims buffer                               |
| `update_memory`          | Updates long-term memory slot                                                         |
| `get_conversation`       | Returns current buffer                                                                |
| `print_memory`           | Pretty-prints buffer with color and wrapping                                          |
| External: `yaml`         | Loads config file                                                                     |
| Config: `system_message` | Template for system context, supports dynamic placeholders                            |

---

## **Conclusion**

This script provides a robust, configurable, and extensible foundation for managing conversational context in an AI assistant. Its use of a dynamic system message, bounded memory, and explicit long-term memory slot makes it suitable for applications where both recency and persistence of context are important. The reliance on external configuration and YAML parsing allows for easy customization without code changes. The pretty-printing utility aids in development and debugging.
