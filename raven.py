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
    return datetime.datetime.now().strftime("%Y-%m-%d")

def now_stamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def log_path_for_today():
    return os.path.join(SESSIONS_DIR, f"log_{now_datestr()}.txt")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def ensure_core_dirs():
    ensure_dir(SESSIONS_DIR)
    ensure_dir(WORKSPACES_DIR)

def is_text_file(path):
    text_ext = [
        ".py",".js",".ts",".tsx",".jsx",".json",".md",".txt",".sh",".bash",
        ".yml",".yaml",".toml",".ini",".cfg",".conf",".html",".css",".sql",
        ".env",".env.example",".dockerfile",".Dockerfile"
    ]
    p = pathlib.Path(path)
    if p.is_dir():
        return False
    if p.suffix.lower() in text_ext:
        return True
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.read(2048)
        return True
    except:
        return False

def save_history(history, path=ACTIVE_SESSION_PATH):
    ensure_core_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_history(path=ACTIVE_SESSION_PATH):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def append_log(role, text):
    ensure_core_dirs()
    with open(log_path_for_today(), "a", encoding="utf-8") as f:
        f.write(f"[{role.upper()}] {text}\n\n")

def build_messages(history, new_user_msg):
    msgs = []
    for role, text in history:
        msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": new_user_msg})
    return msgs

def ask_claude(history, user_msg):
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
    ensure_core_dirs()
    if name is None or name.strip()=="":
        name = f"proj-{now_stamp()}"
    ws_path = os.path.join(WORKSPACES_DIR, name)
    ensure_dir(ws_path)
    return os.path.abspath(ws_path), name

def list_dir_recursive(root_path):
    root = pathlib.Path(root_path)
    lines = []
    file_paths = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_dir():
            lines.append(f"[DIR]  {rel}")
        else:
            lines.append(f"[FILE] {rel}")
            if is_text_file(path):
                file_paths.append(path)
    tree_str = "\n".join(lines)
    return tree_str, file_paths

def read_file_or_dir_for_context(ws_path, target_rel):
    target_abs = os.path.abspath(os.path.join(ws_path, target_rel))
    if not target_abs.startswith(ws_path):
        return f"[SECURITY BLOCKED] path '{target_rel}' is outside workspace."
    if os.path.isdir(target_abs):
        tree_str, file_paths = list_dir_recursive(target_abs)
        dump_parts = []
        dump_parts.append(f"[DIRECTORY TREE for {target_rel}]\n{tree_str}\n")
        for fpath in file_paths:
            try:
                relp = os.path.relpath(str(fpath), ws_path)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                if len(content) > 50000:
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
        return f"[ERROR] path '{target_rel}' not found."
    if not is_text_file(target_abs):
        return f"[SKIP NON-TEXT FILE] {target_rel}"
    try:
        with open(target_abs, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 50000:
            content = content[:50000] + "\n[TRUNCATED]"
        relp = os.path.relpath(target_abs, ws_path)
        return f"--- FILE {relp} BEGIN ---\n{content}\n--- FILE {relp} END ---"
    except Exception as e:
        return f"[ERROR reading file '{target_rel}': {e}]"

def write_file_from_claude(ws_path, dest_rel, instruction, history):
    dest_abs = os.path.abspath(os.path.join(ws_path, dest_rel))
    if not dest_abs.startswith(ws_path):
        return "[SECURITY BLOCKED] target outside workspace."
    parent_dir = os.path.dirname(dest_abs)
    ensure_dir(parent_dir)
    request_for_file = (
        f"You are generating a source file for path `{dest_rel}`.\n"
        f"Instruction:\n{instruction}\n\n"
        "Return ONLY the complete file content to write. "
        "Do not add explanations, headers, or markdown fences."
    )
    file_content = ask_claude(history, request_for_file)
    with open(dest_abs, "w", encoding="utf-8") as f:
        f.write(file_content)
    return f"[WROTE FILE] {dest_rel} ({len(file_content)} chars)"

def print_help():
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
    # collect lines until user types :end on a line by itself
    print("(multiline mode) paste your prompt. finish by typing ':end' on its own line.")
    lines = []
    while True:
        try:
            line = input("")
        except KeyboardInterrupt:
            print("\n[cancelled]")
            return None
        if line.strip() == ":end":
            break
        lines.append(line)
    return "\n".join(lines)

def main():
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
                continue

            if user_input == ":exit":
                print("[exit]")
                break

            if user_input == ":new":
                chat_history = []
                print("[chat cleared in memory]")
                continue

            if user_input == ":save":
                save_history(chat_history)
                print("[session saved -> sessions/active_session.json]")
                continue

            if user_input == ":load":
                chat_history = load_history()
                print("[session loaded <- sessions/active_session.json]")
                continue

            if user_input.startswith(":use"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    current_ws_path, current_ws_name = make_workspace()
                else:
                    wanted = parts[1].strip()
                    current_ws_path, current_ws_name = make_workspace(wanted)
                print(f"[workspace active] {current_ws_name} -> {current_ws_path}")
                continue

            if user_input.startswith(":read_file"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    print("[ERROR] usage: :read_file <relative_path_or_dir>")
                    continue
                rel_target = parts[1].strip()
                blob = read_file_or_dir_for_context(current_ws_path, rel_target)
                chat_history.append(("user", f"[PROJECT CONTEXT INJECTION from {rel_target}]\n{blob}"))
                append_log("user", f"[PROJECT CONTEXT INJECTION from {rel_target}]\n{blob}")
                print("[context injected into chat_history]")
                continue

            if user_input.startswith(":write_file"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    print("[ERROR] usage: :write_file <relative_path>")
                    continue
                dest_rel = parts[1].strip()
                try:
                    instruction = input(f"(spec for {dest_rel}) > ").strip()
                except KeyboardInterrupt:
                    print("\n[cancelled]")
                    continue
                result_msg = write_file_from_claude(
                    current_ws_path,
                    dest_rel,
                    instruction,
                    chat_history
                )
                chat_history.append(("user", f"[WRITE_FILE REQUEST] {dest_rel}\n{instruction}"))
                chat_history.append(("assistant", result_msg))
                append_log("user", f"[WRITE_FILE REQUEST] {dest_rel}\n{instruction}")
                append_log("assistant", result_msg)
                print(result_msg)
                continue

            if user_input == ":ask":
                block = multiline_input()
                if block is None or block.strip() == "":
                    print("[cancelled or empty]")
                    continue
                reply = ask_claude(chat_history, block)
                print("\nClaude > " + reply + "\n")
                chat_history.append(("user", block))
                chat_history.append(("assistant", reply))
                append_log("user", block)
                append_log("assistant", reply)
                continue

            reply = ask_claude(chat_history, user_input)
            print("\nClaude > " + reply + "\n")
            chat_history.append(("user", user_input))
            chat_history.append(("assistant", reply))
            append_log("user", user_input)
            append_log("assistant", reply)

        except KeyboardInterrupt:
            print("\n[exit]")
            break

if __name__ == "__main__":
    main()
