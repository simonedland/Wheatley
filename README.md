# Wheatley

Welcome to **Wheatley**, an experimental voice assistant powered by open-source
tools. The project is a work in progress and we rely on community feedback to
make it better. If you spot a bug or have an idea, please let us know or send a
pull request.

## Getting Started

1. Create your configuration:
   - Copy the example file from:
    `\wheatley\config\config.example.yaml`
     to
    `\wheatley\config\config.yaml`
   - Edit `config.yaml` to adjust settings as needed.
2. Run the system check script:
   > .\system check.ps1  
   This script:
   - Verifies Python is installed.
   - Creates and activates the virtual environment (.venv) if needed.
   - Installs all prerequisites.
   - Checks for the configuration file.
   - Runs initial tests.
3. Initialize the environment:
   - Once the configuration file is set and prerequisites installed, the environment is ready.
   - To manually activate the environment, run:
    > .\\.venv\Scripts\Activate.ps1
   - To deactivate the environment when needed, simply type:
     > deactivate
   - To reinitialize, delete the `.venv` folder and re-run the system check script.
   - Confirm that the virtual environment activates without errors and tests execute successfully.

4. Run the assistant from the project root:
   > python -m wheatley

## Roadmap
### TTS
- [ ] end to end streaming
  - [ ] STT streaming input transcription
  [reference](https://platform.openai.com/docs/guides/speech-to-text?lang=curl#streaming-transcriptions)
  - [ ] Stream LLM response to TTS
  TTS does not support streaming input, so there is no value in streaming the LLM response to TTS.
  TTS supports "previus text" and "next text" wich means we can "stream" the innput by continuously sending previus, current, and next text to the TTS service.
  [reference](https://platform.openai.com/docs/api-reference/responses-streaming)
  - [ ] Stream TTS response to speaker
  [reference](https://elevenlabs.io/docs/api-reference/streaming)

### LLM
- [X] Add long term memory (LTM) to the LLM.
- [ ] make a memory store with configurable storage priorities and storage timestamps.
    - [ ] make a memory "timeout" for the LLM so it can forget things after a certain time.

### Tools
- [ ] Add a google notes tool to the LLM.

### ideas
    - [ ] Wi-Fi monitoring/management
    - [ ] remote webhook management
    - [ ] guest mode
    - [X] Proactive conversation
      - [ ] Monitoring calendar?
      - [ ] Air quality alert?
      - [X] Set timer for x minutes?
    - [ ] Digital twin?
    - [ ] Read up in another voice?
    - [ ] Self aware of mood?
    - [ ] Object spotting???
    - [X] Briefing?
    - [ ] Multi speaker recognition?
    - [ ] Todo list
    - [ ] Multi-room audio orchestrator
    - [ ] Quirkiness slider
    - [ ] Voiceprint authentication – owner unlocks high-impact commands; guests get limited scope.


![image](https://github.com/user-attachments/assets/8a19e5c1-a585-4bda-a584-b9c9db2b953a)

## Contributing
We know Wheatley isn't perfect—there are plenty of bugs and rough edges yet to be smoothed out. If you have ideas or fixes, please jump in! For guidelines on how to contribute, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Code of Conduct
Please read and abide by our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License
This project is licensed under the [MIT License](LICENSE).

## Attribution
If you reuse or adapt Wheatley's code in your own projects, please keep the
license notice intact and include a link back to this repository. Giving credit
helps others discover the original source and keeps the community strong.
