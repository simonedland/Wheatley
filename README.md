## Getting Started

1. Create your configuration:
   - Copy the example file from:
     `\Weatly\python\src\config\config.example.yaml`
     to
     `\Weatly\python\src\config\config.yaml`
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

## Roadmap

### LLM

- [ ] Add long term memory (LTM) to the LLM.
- [ ] make a memmory store with conigurable storage prioroties, and storage timestamps.
    - [ ] make a memmory "time out" for the LLM, so it can forget things after a certain time.

### Tools
- [ ] Add a google notes tool to the LLM.

### ideas
    - [ ] Proactive conversation
      - [ ] Monitoring calendar?
      - [ ] Air quality alert?
      - [ ] Sett timer for x minutes?
    - [ ] Digital twin?
    - [ ] Readup in another voice?
    - [ ] Self aware of mood?
    - [ ] Object spotting???
    - [ ] Briefing?
    - [ ] Multi speaker recognition?
    - [ ] Todo list
    - [ ] Multi-room audio orchestrator
    - [ ] Quirkiness slider
    - [ ] Voiceprint authentication – owner unlocks high-impact commands; guests get limited scope.


![image](https://github.com/user-attachments/assets/8a19e5c1-a585-4bda-a584-b9c9db2b953a)
