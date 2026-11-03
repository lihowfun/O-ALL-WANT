# PRE-06: zero-context goldfish launch (D15) — probe record, 2026-11-03

## Finding
- Workflow/Agent-tool subagents inside the desktop app always receive the user's
  auto-memory index (3 lines) and may receive CLAUDE.md/AGENTS.md of folders they
  read. They cannot meet D15. Both goldfish reviews of revision 3 are therefore
  "context: inherited (documented), not zero-context".
- The bundled CLI `claude.exe` 2.1.309 can launch an isolated goldfish, but
  `auth status` reports `loggedIn: false`. Only the owner can log in.
- `--bare` would be the cleanest recipe, but it reads only `ANTHROPIC_API_KEY`
  (API billing), never the subscription login. D13 gives trials no API key by
  default, so `--bare` is not used.

## Recipe (subscription login, no API key)
Run from a fresh empty folder outside every project, so no CLAUDE.md is found in
its parents (checked: none in C:\Users\User, AppData, AppData\Local, Temp, or
~/.claude) and its auto-memory folder is new and empty:

```
claude -p --tools "" --strict-mcp-config --disable-slash-commands \
  --setting-sources project --output-format stream-json --verbose < packet.md
```

- The packet embeds every cited line, since the goldfish has no tools.
- Init-event check (recorded per goldfish): `tools`, `mcp_servers`, `slash_commands`,
  `skills`, `plugins` and `agents` are empty, and `cwd` is the fresh folder.
- Canary check: the packet asks the goldfish to list any project rule it knows;
  a correct zero-context answer is "none".
- Each record stores launch argv, host version, init event and canary answer.

## Cost
Init probe < 0.1M logical tokens; PRE-02 review of revision 3 about 0.4-1M.
Both run on the subscription quota once the owner logs in (`claude auth login`).
