# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\assistant\assistant.py
The provided Python script is a utility for managing conversation history for an assistant named Wheatley. It is designed to maintain a bounded conversation history, ensuring that the assistant can reference recent interactions while keeping memory usage controlled.

### Overall Purpose
The script's main purpose is to manage a conversation history buffer for an assistant, allowing it to store a limited number of user and assistant interactions, along with a system message that includes dynamic information like the current time and day.

### Main Class and Functions

#### `ConversationManager`
This is the primary class responsible for handling the conversation history. It includes several methods to manage and interact with this history:

- **`__init__(self, max_memory=5)`**: 
  - Initializes the conversation manager with a specified maximum memory for user/assistant turns.
  - Loads a system message from a YAML configuration file and dynamically inserts the current time and day into the message.
  - Initializes the conversation history with this system message.

- **`add_text_to_conversation(self, role, text)`**: 
  - Adds a new message to the conversation history from a specified role (either user or assistant).
  - Updates the system message with the current time and day each time a new message is added.
  - Ensures that the conversation history does not exceed the specified memory limit by removing the oldest messages, excluding the system message.

- **`get_conversation(self)`**: 
  - Returns the current state of the conversation history as a list of message dictionaries.

- **`print_memory(self)`**: 
  - Outputs the conversation history in a human-readable format, using different colors for system, user, and assistant messages.
  - Uses text wrapping to ensure that messages are displayed neatly within a specified width.

### Structure and Interaction
The script is structured around the `ConversationManager` class, which encapsulates all functionality related to managing the conversation history. The class interacts with a configuration file (`config.yaml`) to load the initial system message, which is dynamically updated with the current time and day.

### External Dependencies
- **`os`**: Used to construct the file path for the configuration file.
- **`textwrap`**: Utilized for wrapping text in the `print_memory` method to ensure neat output.
- **`yaml`**: Used to parse the YAML configuration file.
- **`datetime`**: Provides the current date and time for dynamic message updates.

### Configuration Requirements
The script requires a configuration file (`config.yaml`) located in a specific directory structure. This file must contain an "assistant" section with a "system_message" entry, which can include placeholders for `<current_time>` and `<current_day>`.

### Notable Algorithms and Logic
- **Dynamic System Message Update**: The script dynamically updates the system message with the current time and day each time the conversation is modified. This ensures that the assistant's context is always up-to-date.
- **Bounded Memory Management**: The `add_text_to_conversation` method ensures that the conversation history does not exceed the specified memory limit by removing the oldest entries, maintaining only the most recent interactions.

Overall, the script provides a structured way to manage conversation history for an assistant, with dynamic context updates and controlled memory usage.
