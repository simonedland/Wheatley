# AI Summary

### C:\GIT\eatly\Wheatley\Weatly\python\src\assistant\assistant.py
The Python code defines a `ConversationManager` class that manages conversation history with a fixed memory size. It loads a system message from a YAML configuration file, replacing placeholders with the current date and time. The class maintains a list of messages, starting with the system message, and allows adding new messages with roles like "user" or "assistant." It ensures the conversation history does not exceed a specified maximum memory by removing the oldest messages. The class also provides methods to retrieve the conversation and print it in a formatted manner with color-coded roles.
