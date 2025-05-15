# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\assistant\assistant.py
The Python code defines a `ConversationManager` class that manages a conversation history with a fixed memory limit. It loads a system message from a YAML configuration file, replacing placeholders for the current time and day. The class maintains a list of messages, starting with the system message, and allows adding new messages with specified roles (e.g., user or assistant). It ensures the conversation history does not exceed a specified maximum number of messages, excluding the system message. The class also provides methods to retrieve the conversation and print it in a formatted manner, using different colors for different roles.
