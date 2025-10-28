# blackbox-raven

blackbox-raven is a local AI operator that runs Claude 4.5 from your Linux terminal.
It gives you:
- persistent chat with context
- per-project workspaces
- read project code into context
- write new code files directly to disk

No browser. No SaaS UI limits. Full local control.

## Quick start

cd /home/akex/Projects/blackbox-raven
source .venv/bin/activate
source .env.local
./raven.py

## Commands

:use <name>       -> select/create workspace in workspaces/<name>
:read_file <p>    -> inject file/dir contents from workspace into chat context
:write_file <p>   -> generate/overwrite a file in workspace using Claude 4.5
:save / :load     -> persist and restore conversation state (sessions/active_session.json)
:new              -> clear in-memory chat_history
:exit             -> quit

All messages are also logged under sessions/log_YYYY-MM-DD.txt.
