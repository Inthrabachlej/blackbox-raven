blackbox-raven
==============

blackbox-raven is a local AI operator for Claude 4.5 that runs fully in a Linux terminal.

**What it does**

- Lets you talk to Claude 4.5 directly from the console. No browser UI.
- Injects local project files or entire folders into the model context on demand.
- Asks the model to generate complete source files (modules, services, configs).
- Saves those generated files directly to disk inside an active workspace.
- Can persist and reload conversation and planning state across sessions.

This is not "copy a snippet from chat and paste into VS Code".
This is "describe the module → get a ready file written straight to disk".

---

Core workflow
-------------

The main CLI is `raven.py`. It exposes a minimal command set:

- `:use <name>`  
  Selects or creates a workspace under `workspaces/<name>`.  
  A workspace is basically a project sandbox. Each project is isolated.

- `:read_file <path>`  
  Injects a file or a whole directory (from the active workspace) into the model context.  
  This lets the model see your current codebase structure, not just one file.

- `:write_file <path>`  
  Opens a "spec" prompt.  
  You describe what should exist in `<path>` (for example `api/main.py`).  
  Claude then returns a full file body.  
  raven.py writes that file to disk in the workspace, overwriting or creating it.

  Result: you ask for a module, you get an actual module on disk, ready to commit.

- `:ask`  
  Multiline prompt mode.  
  You can paste long architecture plans, system blueprints, etc.  
  You finish with `:end`.  
  The whole block is sent to the model as one request.

- `:save` / `:load`  
  `:save` dumps the current conversation and context into `sessions/active_session.json`.  
  `:load` restores it later.  
  You can stop working, come back tomorrow, reload the planning state, and continue.

---

Example: generating a new service
---------------------------------

Typical session flow:

1. `:use archon2`  
   Create/select workspace `workspaces/archon2`.

2. `:read_file prompt_archon2.0.txt`  
   Inject high-level requirements and system goals into context.

3. `:write_file api/main.py`  
   Spec says:  
   - build a FastAPI service  
   - expose `/health`  
   - expose `/build`  
   - wire it for `uvicorn`

4. `:write_file core/state.py`  
   Spec says:  
   - keep per-project build state  
   - simple storage, readable for humans

5. `:write_file core/planner.py`  
   Spec says:  
   - given "I want X service", plan modules / tasks / structure

This produced a working codebase called `archon2`.

`archon2` is a FastAPI backend that:
- serves basic health/build endpoints,
- tracks build state per project,
- can plan code structure for a requested service (like "blog API with auth + SQLite"),
- is ready to run with `uvicorn`.

`archon2` lives in its own public repo:
`github.com/Inthrabachlej/archon2`
and it was generated almost entirely through `:write_file`, not manual typing.

This proves blackbox-raven is not theoretical.  
It is already being used to generate and publish backend services.

---

Running blackbox-raven locally
------------------------------

Minimal bootstrap on a new Linux (Mint / Ubuntu family):

```bash
# 1. system deps
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# 2. clone
cd /home/akex/Projects
git clone https://github.com/Inthrabachlej/blackbox-raven.git
cd blackbox-raven

# 3. virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. python deps
pip install --upgrade pip
pip install -r requirements.txt

# 5. local API key (never commit this file)
echo 'ANTHROPIC_API_KEY=sk-ant-...your_key...' > .env.local

# 6. run
source .env.local
chmod +x raven.py
./raven.py

