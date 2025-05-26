# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\assistant\assistant.py
The Python code defines a `ConversationManager` class that manages a conversation history with a fixed memory size. Its main purpose is to maintain a list of messages, including a system message that dynamically updates with the current date and time.

- **Initialization**: The class initializes with a system message loaded from a YAML configuration file. This message includes placeholders for the current time and day, which are replaced with actual values during initialization.

- **Adding Messages**: The `add_text_to_conversation` method allows adding new messages to the conversation. It refreshes the system message with the current time and day each time a new message is added. The conversation history is trimmed to maintain only the latest messages, according to the specified memory limit.

- **Retrieving and Printing**: The `get_conversation` method returns the current list of messages. The `print_memory` method prints the conversation history with color-coded roles (system, user, assistant) and wraps text for readability.

Overall, the class is designed to manage a conversation with a dynamic system message and a limited memory of past interactions.
