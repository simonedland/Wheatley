# AI Codebase Overview

### C:\GIT\Wheatly\Wheatley\ad_nauseam.py

The `ad_nauseam.py` script is part of a larger project designed to automate the summarization of Python and Arduino source files using AI. It leverages the OpenAI API to generate detailed summaries, which can be useful for documentation or understanding complex codebases.

### Overall Purpose

The script's primary function is to generate AI-based summaries for source code files (.py and .ino), excluding those within virtual environment directories. It automates the documentation process, providing insights into the structure and functionality of the code.

### Main Components

#### 1. Configuration

- **_load_config()**: Loads settings from a YAML file, including API keys and model parameters.
- **Config Class**: A data class that stores configuration details like model type, temperature, and file types to process.

#### 2. LLM Client

- **LLMClient Class**: A wrapper around the OpenAI API, responsible for generating summaries.
  - **summarise()**: Sends file content to the API and returns a summary. Supports a dry-run mode for testing.
  - **_instructions_for()**: Creates specific instructions for the AI model based on file type.
  - **_extract_text()**: Extracts text from the API response, handling different formats.

#### 3. File Crawler

- **DirectoryCrawler Class**: Searches for files with specified extensions, excluding `.venv` directories.
  - **crawl()**: Returns a list of file paths to be summarized.

#### 4. Orchestrator

- **Summariser Class**: Manages the summarization workflow.
  - **run()**: Coordinates file discovery and summary generation, organizing results into markdown files.
  - **_write_folder_md()**: Writes summaries for each directory into a `README_AI.md`.
  - **_write_root_md()**: Compiles a global summary for the entire codebase.

### External Dependencies

- **OpenAI API**: Used for generating summaries, requiring an API key from the configuration file.
- **PyYAML**: For reading configuration files.
- **tqdm**: Provides a progress bar during processing.

### Configuration Requirements

The script requires a `config.yaml` file containing the OpenAI API key and other settings, located at a specific path.

### Notable Logic

- **File Filtering**: Efficiently excludes files in virtual environments to focus on relevant code.
- **Dynamic Instructions**: Tailors instructions for the AI model based on file type, ensuring relevant summaries.
- **Error Handling**: Robust error handling in `_extract_text()` for various API response formats.

### Execution

The script can be executed from the command line, allowing users to specify the target directory and enable a dry-run mode. The main function initializes the `Summariser` and starts the summarization process.

Overall, `ad_nauseam.py` automates the generation of code summaries, enhancing documentation and understanding of codebases through AI-driven insights.