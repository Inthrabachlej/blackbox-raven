#!/usr/bin/env python3
import anthropic
import readline
import json
import os
import datetime
import pathlib

MODEL_NAME = "claude-sonnet-4-5"
SESSIONS_DIR = "sessions"
WORKSPACES_DIR = "workspaces"
ACTIVE_SESSION_PATH = os.path.join(SESSIONS_DIR, "active_session.json")

client = anthropic.Anthropic()

def now_datestr():
    # EN: Return current date as YYYY-MM-DD string.
    # NL: Geeft de huidige datum terug als een string in formaat JJJJ-MM-DD.
    return datetime.datetime.now().strftime("%Y-%m-%d")

def now_stamp():
    # EN: Return compact timestamp used for auto workspace names.
    # NL: Geeft een compacte timestamp voor automatische workspacenamen.
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def log_path_for_today():
    # EN: Path to today's log file inside sessions/.
    # NL: Pad naar het logbestand van vandaag in sessions/.
    return os.path.join(SESSIONS_DIR, f"log_{now_datestr()}.txt")

def ensure_dir(path):
    # EN: Create directory if it does not exist.
    # NL: Maakt de map aan als die niet bestaat.
    os.makedirs(path, exist_ok=True)

def ensure_core_dirs():
    # EN: Ensure core folders (sessions, workspaces) exist.
    # NL: Zorgt dat de kernmappen (sessions, workspaces) bestaan.
    ensure_dir(SESSIONS_DIR)
    ensure_dir(WORKSPACES_DIR)

def is_text_file(path):
    # EN: Heuristic: decide if file should be treated as text.
    # NL: Heuristiek: bepalen of het bestand als tekst moet worden behandeld.
    text_ext = [
        ".py",".js",".ts",".tsx",".jsx",".json",".md",".txt",".sh",".bash",
        ".yml",".yaml",".toml",".ini",".cfg",".conf",".html",".css",".sql",
        ".env",".env.example",".dockerfile",".Dockerfile"
    ]
    p = pathlib.Path(path)
    if p.is_dir():
        # EN: Directories are not text files.
        # NL: Mappen zijn geen tekstbestanden.
        return False
    if p.suffix.lower() in text_ext:
        # EN: Known text extension.
        # NL: Bekende tekstextensie.
        return True
    try:
        # EN: Fallback check. Try reading first ~2KB as UTF-8.
        # NL: Alternatieve check. Probeer de eerste ~2KB als UTF-8 te lezen.
        with open(path, "r", encoding="utf-8") as f:
            f.read(2048)
        return True
    except:
        # EN: Reading failed -> treat as non-text.
        # NL: Lezen mislukt -> behandelen als niet-tekst.
        return False

def save_history(history, path=ACTIVE_SESSION_PATH):
    # EN: Persist chat history (list of (role, text)) to disk as JSON.
    # NL: Slaat de chathistorie (lijst van (rol, tekst)) op als JSON op schijf.
    ensure_core_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_history(path=ACTIVE_SESSION_PATH):
    # EN: Load chat history JSON from disk. Return [] if not found.
    # NL: Laadt de chathistorie als JSON van schijf. Geeft [] terug als niet gevonden.
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def append_log(role, text):
    # EN: Append a line to today's log file with role tag.
    # NL: Schrijft een regel naar het logbestand van vandaag met de roltag.
    ensure_core_dirs()
    with open(log_path_for_today(), "a", encoding="utf-8") as f:
        f.write(f"[{role.upper()}] {text}\n\n")

def build_messages(history, new_user_msg):
    # EN: Convert our internal (role,text) history + new user msg into Anthropic message format.
    # NL: Zet onze interne (rol,tekst)-geschiedenis + nieuwe user-boodschap om naar Anthropic message-formaat.
    msgs = []
    for role, text in history:
        msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": new_user_msg})
    return msgs

def ask_claude(history, user_msg):
    # EN: Send conversation + new user message to Claude. Return plain text answer.
    # NL: Stuurt de conversatie + nieuwe user-boodschap naar Claude. Geeft de tekstuele output terug.
    msgs = build_messages(history, user_msg)
    resp = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        messages=msgs,
    )
    out_chunks = []
    for block in resp.content:
        if block.type == "text":
            out_chunks.append(block.text)
    return "\n".join(out_chunks)

def make_workspace(name=None):
    # EN: Create or ensure workspace directory. Autoname if nothing passed.
    # NL: Maakt of controleert de workspace map. Genereert naam automatisch als er geen naam gegeven is.
    ensure_core_dirs()
    if name is None or name.strip()=="":
        name = f"proj-{now_stamp()}"
    ws_path = os.path.join(WORKSPACES_DIR, name)
    ensure_dir(ws_path)
    return os.path.abspath(ws_path), name

def list_dir_recursive(root_path):
    # EN: Walk a directory tree. Build a readable tree listing and collect text file paths.
    # NL: Loopt recursief door een map. Bouwt een leesbare structuur en verzamelt paden naar tekstbestanden.
    root = pathlib.Path(root_path)
    lines = []
    file_paths = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_dir():
            # EN: Tag directories.
            # NL: Markeer mappen.
            lines.append(f"[DIR]  {rel}")
        else:
            # EN: Tag files.
            # NL: Markeer bestanden.
            lines.append(f"[FILE] {rel}")
            if is_text_file(path):
                # EN: Keep only text files for later content dump.
                # NL: Bewaar alleen tekstbestanden voor latere inhoudsdump.
                file_paths.append(path)
    tree_str = "\n".join(lines)
    return tree_str, file_paths

def read_file_or_dir_for_context(ws_path, target_rel):
    # EN: Read file or directory from current workspace to inject it into context.
    # NL: Leest een bestand of map uit de actieve workspace om die in de context te steken.
    target_abs = os.path.abspath(os.path.join(ws_path, target_rel))

    # EN: Security check. Block paths escaping the workspace.
    # NL: Security check. Blokkeer paden die buiten de workspace gaan.
    if not target_abs.startswith(ws_path):
        return f"[SECURITY BLOCKED] path '{target_rel}' is outside workspace."

    if os.path.isdir(target_abs):
        # EN: If it's a directory: build directory tree and dump preview of each text file.
        # NL: Als het een map is: toon boomstructuur en een preview van elk tekstbestand.
        tree_str, file_paths = list_dir_recursive(target_abs)
        dump_parts = []
        dump_parts.append(f"[DIRECTORY TREE for {target_rel}]\n{tree_str}\n")
        for fpath in file_paths:
            try:
                relp = os.path.relpath(str(fpath), ws_path)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                if len(content) > 50000:
                    # EN: Truncate very large files for safety.
                    # NL: Knip zeer grote bestanden af voor veiligheid.
                    content_preview = content[:50000] + "\n[TRUNCATED]"
                else:
                    content_preview = content
                dump_parts.append(
                    f"\n--- FILE {relp} BEGIN ---\n{content_preview}\n--- FILE {relp} END ---\n"
                )
            except Exception as e:
                dump_parts.append(f"\n--- FILE {fpath} ERROR: {e} ---\n")
        return "\n".join(dump_parts)

    if not os.path.isfile(target_abs):
        # EN: Target path does not exist in workspace.
        # NL: Doelpad bestaat niet in de workspace.
        return f"[ERROR] path '{target_rel}' not found."

    if not is_text_file(target_abs):
        # EN: Skip binary or non-text files.
        # NL: Sla binaire of niet-tekstbestanden over.
        return f"[SKIP NON-TEXT FILE] {target_rel}"

    try:
        # EN: Inject a single file. Truncate if >50k chars.
        # NL: Injecteer één bestand. Knip af als >50k tekens.
        with open(target_abs, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 50000:
            content = content[:50000] + "\n[TRUNCATED]"
        relp = os.path.relpath(target_abs, ws_path)
        return f"--- FILE {relp} BEGIN ---\n{content}\n--- FILE {relp} END ---"
    except Exception as e:
        # EN: File read failed.
        # NL: Bestand kon niet gelezen worden.
        return f"[ERROR reading file '{target_rel}': {e}]"

def write_file_from_claude(ws_path, dest_rel, instruction, history):
    # EN: Ask Claude to generate full file content for dest_rel and write it in workspace.
    # NL: Vraagt Claude om de volledige inhoud voor dest_rel te genereren en schrijft die in de workspace.
    dest_abs = os.path.abspath(os.path.join(ws_path, dest_rel))

    # EN: Security check. Block path escape above workspace.
    # NL: Security check. Blokkeer paden die boven de workspace uitsteken.
    if not dest_abs.startswith(ws_path):
        return "[SECURITY BLOCKED] target outside workspace."

    parent_dir = os.path.dirname(dest_abs)
    ensure_dir(parent_dir)

    # EN: Instruction passed to Claude. 
    #     We explicitly request only raw file body. No markdown fences etc.
    # NL: Instructie voor Claude.
    #     We vragen expliciet alleen de ruwe bestandsinhoud. Geen markdown fences enz.
    request_for_file = (
        f"You are generating a source file for path `{dest_rel}`.\n"
        f"Instruction:\n{instruction}\n\n"
        "Return ONLY the complete file content to write. "
        "Do not add explanations, headers, or markdown fences."
    )

    file_content = ask_claude(history, request_for_file)

    # EN: Write generated file to disk.
    # NL: Schrijf het gegenereerde bestand naar de schijf.
    with open(dest_abs, "w", encoding="utf-8") as f:
        f.write(file_content)

    return f"[WROTE FILE] {dest_rel} ({len(file_content)} chars)"

def print_help():
    # EN: Show available console commands.
    # NL: Toon de beschikbare consolecommando's.
    print(
"""
Commands:
:new                 -> clear in-memory chat (start fresh)
:save                -> write current chat_history to sessions/active_session.json
:load                -> load sessions/active_session.json into memory
:use <name?>         -> switch/create workspace under workspaces/<name>
:read_file <path>    -> inject file OR directory content from workspace to chat context
:write_file <path>   -> generate/overwrite file in workspace using Claude
:ask                 -> multiline prompt mode. Finish by typing :end on its own line.
:exit                -> quit
"""
    )

def multiline_input():
    # EN: Collect multiple lines until user types ':end' alone on a line.
    # NL: Verzamelt meerdere regels tot de gebruiker ':end' op een losse regel typt.
    print("(multiline mode) paste your prompt. finish by typing ':end' on its own line.")
    lines = []
    while True:
        try:
            line = input("")
        except KeyboardInterrupt:
            # EN: User aborted multiline input.
            # NL: Gebruiker heeft de multiline input afgebroken.
            print("\n[cancelled]")
            return None
        if line.strip() == ":end":
            break
        lines.append(line)
    return "\n".join(lines)

def main():
    # EN: Init core dirs. Load previous chat. Create/activate a workspace.
    # NL: Initialiseert kernmappen. Laadt vorige chat. Maakt/activeert een workspace.
    ensure_core_dirs()
    chat_history = load_history()
    current_ws_path, current_ws_name = make_workspace()

    print(f"[workspace active] {current_ws_name} -> {current_ws_path}")
    print("blackbox-raven :: Claude 4.5 interactive console (Ctrl+C or :exit to quit)")
    print_help()

    while True:
        try:
            user_input = input("You > ").strip()
            if user_input == "":
                # EN: Ignore empty input.
                # NL: Negeer lege invoer.
                continue

            if user_input == ":exit":
                # EN: Graceful shutdown.
                # NL: Netjes afsluiten.
                print("[exit]")
                break

            if user_input == ":new":
                # EN: Reset in-memory chat history.
                # NL: Reset de chathistorie in RAM.
                chat_history = []
                print("[chat cleared in memory]")
                continue

            if user_input == ":save":
                # EN: Save chat history to sessions/active_session.json.
                # NL: Sla de chathistorie op naar sessions/active_session.json.
                save_history(chat_history)
                print("[session saved -> sessions/active_session.json]")
                continue

            if user_input == ":load":
                # EN: Load chat history from sessions/active_session.json.
                # NL: Laad de chathistorie uit sessions/active_session.json.
                chat_history = load_history()
                print("[session loaded <- sessions/active_session.json]")
                continue

            if user_input.startswith(":use"):
                # EN: Switch workspace (or create if missing).
                # NL: Wissel van workspace (of maak een nieuwe als die nog niet bestaat).
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    current_ws_path, current_ws_name = make_workspace()
                else:
                    wanted = parts[1].strip()
                    current_ws_path, current_ws_name = make_workspace(wanted)
                print(f"[workspace active] {current_ws_name} -> {current_ws_path}")
                continue

            if user_input.startswith(":read_file"):
                # EN: Inject file or directory content into chat context for Claude.
                # NL: Injecteer bestand- of mapinhoud in de chatcontext voor Claude.
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    print("[ERROR] usage: :read_file <relative_path_or_dir>")
                    continue
                rel_target = parts[1].strip()
                blob = read_file_or_dir_for_context(current_ws_path, rel_target)

                # EN: Store this injected context as if user said it.
                # NL: Sla deze geïnjecteerde context op alsof de gebruiker het zei.
                chat_history.append(("user", f"[PROJECT CONTEXT INJECTION from {rel_target}]\n{blob}"))
                append_log("user", f"[PROJECT CONTEXT INJECTION from {rel_target}]\n{blob}")
                print("[context injected into chat_history]")
                continue

            if user_input.startswith(":write_file"):
                # EN: Ask Claude to generate a file and write it to current workspace.
                # NL: Vraag Claude om een bestand te genereren en schrijf het in de huidige workspace.
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    print("[ERROR] usage: :write_file <relative_path>")
                    continue
                dest_rel = parts[1].strip()
                try:
                    instruction = input(f"(spec for {dest_rel}) > ").strip()
                except KeyboardInterrupt:
                    # EN: User cancelled before giving spec.
                    # NL: Gebruiker heeft geannuleerd vóór de specificatie.
                    print("\n[cancelled]")
                    continue

                result_msg = write_file_from_claude(
                    current_ws_path,
                    dest_rel,
                    instruction,
                    chat_history
                )

                # EN: Log request and result into chat_history and daily log.
                # NL: Log de aanvraag en het resultaat in de chathistorie en daglog.
                chat_history.append(("user", f"[WRITE_FILE REQUEST] {dest_rel}\n{instruction}"))
                chat_history.append(("assistant", result_msg))
                append_log("user", f"[WRITE_FILE REQUEST] {dest_rel}\n{instruction}")
                append_log("assistant", result_msg)

                print(result_msg)
                continue

            if user_input == ":ask":
                # EN: Multiline prompt mode. Send big block to Claude.
                # NL: Multiline prompt modus. Stuur een groot blok naar Claude.
                block = multiline_input()
                if block is None or block.strip() == "":
                    # EN: Nothing provided.
                    # NL: Niets ingevoerd.
                    print("[cancelled or empty]")
                    continue
                reply = ask_claude(chat_history, block)
                print("\nClaude > " + reply + "\n")

                # EN: Store Q/A in memory and log.
                # NL: Sla vraag/antwoord op in geheugen en log.
                chat_history.append(("user", block))
                chat_history.append(("assistant", reply))
                append_log("user", block)
                append_log("assistant", reply)
                continue

            # EN: Default branch. Treat input as normal chat to Claude.
            # NL: Standaardpad. Behandel invoer als normale chat voor Claude.
            reply = ask_claude(chat_history, user_input)
            print("\nClaude > " + reply + "\n")

            # EN: Persist this exchange in history and logs.
            # NL: Sla deze uitwisseling op in de historie en logs.
            chat_history.append(("user", user_input))
            chat_history.append(("assistant", reply))
            append_log("user", user_input)
            append_log("assistant", reply)

        except KeyboardInterrupt:
            # EN: Ctrl+C exits the loop.
            # NL: Ctrl+C sluit de loop af.
            print("\n[exit]")
            break

if __name__ == "__main__":
    # EN: Entry point.
    # NL: Startpunt.
    main()

