# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\assistant\assistant.py
The Python script is designed to manage a conversation history with a fixed memory size. It primarily revolves around the `ConversationManager` class, which handles storing, updating, and displaying conversation messages.

### Overall Purpose
The script's main purpose is to maintain a conversation history that includes system, user, and assistant messages. It ensures that the conversation does not exceed a specified memory size, keeping only the most recent messages.

### Main Components

#### 1. `ConversationManager` Class
- **Initialization (`__init__`)**: 
  - Loads a system message from a configuration file (`config.yaml`).
  - Replaces placeholders in the system message with the current date and time.
  - Initializes the conversation with the system message and sets the maximum memory size for the conversation history.

- **`add_text_to_conversation` Method**:
  - Updates the system message with the current date and time each time a new message is added.
  - Appends a new message (from either the user or assistant) to the conversation.
  - Ensures the conversation does not exceed the specified memory size by removing the oldest messages, excluding the system message.

- **`get_conversation` Method**:
  - Returns the current list of messages in the conversation.

- **`print_memory` Method**:
  - Prints the conversation history to the console with color-coded roles (system, user, assistant).
  - Uses text wrapping to ensure messages are displayed neatly within a specified width.

### Structure and Interaction
- The script begins by importing necessary modules: `os`, `textwrap`, `yaml`, and `datetime`.
- The `ConversationManager` class is instantiated with a maximum memory size, which defaults to 5.
- The system message is dynamically updated with the current date and time whenever a message is added.
- The conversation history is maintained as a list of dictionaries, each containing a role and content.

### External Dependencies and Configuration
- **YAML Configuration**: The script relies on a `config.yaml` file located in a `config` directory. This file should contain a `system_message` under an `assistant` key.
- **OS Module**: Used to construct the path to the configuration file.
- **Datetime Module**: Provides the current date and time for updating the system message.

### Notable Logic
- **Dynamic System Message**: The system message is refreshed with the current date and time each time a message is added, ensuring it remains relevant.
- **Memory Management**: The script maintains a fixed memory size by removing the oldest messages once the limit is exceeded, ensuring efficient memory usage.

### Summary
The `ConversationManager` class effectively manages a conversation's history by dynamically updating system messages and maintaining a fixed memory size. It leverages external configuration for initial settings and provides a user-friendly way to display the conversation with color-coded roles.
