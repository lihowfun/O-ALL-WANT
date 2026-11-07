---
name: oaw-add
description: Add, list or remove other people's skills in this project through OAW (oaw.py add, list, remove), with one question and a receipt. Run it only when the user asks.
disable-model-invocation: true
---

# Add skills with OAW

1. Find the OAW checkout: the `path` in `checkout.json` inside `$OAW_CONFIG_HOME`, or else `~/.config/oaw/`
   (Linux), `~/Library/Application Support/oaw/` (macOS), `%APPDATA%\oaw\` (Windows). `oaw.py init` writes
   it. If it is missing, ask the user where OAW is checked out and tell them that one
   `python3 <OAW>/scripts/oaw.py init --target .` records it; do not search the disk.
2. Preview, which is free and writes nothing:
   `python3 <OAW>/scripts/oaw.py add SOURCE... --target . --json`. A SOURCE is a GitHub URL (optionally
   `URL@ref`), a local folder, or a name from OAW's tasting results.
3. Ask the user one question built from the preview's `question`: the choice (1 OAW plus these, 2 only these,
   3 recommended), every listed conflict, and consent for each hook, MCP server and bundled script. Never
   give consent on their behalf.
4. Only for choice 3, or when the user asks: read the new SKILL.md files next to the installed ones and say in
   one line each where they contradict or duplicate each other. Read text only; never run fetched code.
5. Apply with their answer: the preview's `apply_command`, edited to match it (`--choice`, `--consent`,
   `--on-conflict NAME=ACTION`, `--apply`). Show the receipt it prints; do not ask a follow-up question.

- `python3 <OAW>/scripts/oaw.py list --target .` prints the receipt again.
- `python3 <OAW>/scripts/oaw.py remove NAME --target .` undoes one addition exactly.
- 未試吃 means no tasting record exists. Tasting is the maintainer process in OAW's docs/SKILL_INTAKE.md.
