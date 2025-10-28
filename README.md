# blackbox-raven

Local Claude 4.5 operator running fully in a Linux terminal.

This is not a browser UI or SaaS IDE. You run `./raven.py`, point it at a workspace directory, and it:
- reads your code / plans (:read_file)
- generates new files (:write_file)
- writes them directly to disk in that workspace
- keeps state across turns

All using your Anthropic API key. No copy/paste.

## Why this exists

Normal "AI coding assistants" make you:
- paste context into a web chat
- manually copy code back into files
- hope it doesn't leak private data

blackbox-raven flips that:
- You decide which workspace is active
- You choose what files to inject
- Claude 4.5 writes full-source files straight into that workspace on your machine

You stay air-gapped. You own output.

## Core commands inside raven.py

- :use <name>  
  Create / switch active workspace under workspaces/<name>.  
  Example: :use archon2

- :read_file <path>  
  Inject a file or a whole directory tree from the active workspace into Claude context.  
  Works on folders. Recurses and shows file tree + file contents.

- :write_file <path>  
  Opens a spec prompt. You describe what should exist in that file.  
  Claude returns complete file content.  
  raven.py writes that file to disk.

- :ask  
  Multiline prompt mode. You can paste long spec / architecture.  
  Finish by typing :end on its own line.

- :save / :load  
  Persist / restore chat history to sessions/active_session.json.

## Workflow

Real flow actually used:

:use archon2  
:read_file prompt_archon2.0.txt  
:write_file api/main.py  
:write_file core/state.py  
:write_file core/planner.py  

This produced a new project (archon2) on disk with:
- FastAPI service
- state manager with timestamped per-project snapshots
- planner that turns plain English description into a structured build plan
- requirements.txt
- README.md

Then that workspace was pushed as its own repo.

## Related repo: archon2

archon2 is public here:  
github.com/Inthrabachlej/archon2

What archon2 is:
- A code orchestration API generated using blackbox-raven.
- Exposes FastAPI endpoints like /health and /build.
- Tracks build state per project under projects/<name>/state.
- A planner module that takes a high-level description of a service (ex: "blog API with auth, posts, SQLite") and turns it into a task/module breakdown.

Key files in archon2:
- api/main.py
- core/state.py
- core/planner.py
- requirements.txt
- README.md

This is not demo CRUD. It's the start of an automated build pipeline.

## Quick start: run blackbox-raven locally

cd /home/akex/Projects/blackbox-raven  
python3 -m venv .venv  
source .venv/bin/activate  
pip install -r requirements.txt  

Create .env.local with your Anthropic key:

echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env.local

Start the operator:

source .env.local  
./raven.py  

Then inside raven.py:

:use test-workspace  
:write_file demo.py  

Describe the file you want. It writes demo.py to disk.

## Security / keys

- .env.local is gitignored.
- Workspaces are local folders under workspaces/.
- Only files you explicitly :read_file are injected into model context.

You control exposure. You control output. No browser session needed.
