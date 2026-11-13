Trimmed real evidence supplied for 2026-11-14 host fixes. No model calls.

`egmcal-3-web.jsonl`: the original MCP start/completion, identifiers, server,
tool, arguments, status, error and result.content; only result._meta (duplicated
webpage plus account/debug metadata) removed. Example Domain text is retained.
`u2-codex-2-attempts.jsonl`: the original completed native CommandExecution
leaves for the outside Python read and curl. Kept command argv, call ID, output,
exit, status and event envelope type; dropped clocks, process and session IDs.
No assistant narrative, study tasks, key or historical reports were copied.

Fifth host fix evidence:
`u2-codex-2-workspace.jsonl` retains just the supplied U2 `item.completed`
`ls -la` record (command, output, exit/status and event envelope). It lists empty
read-only `.aws`, `.codex`, `.git`; `.agents` already contains packet skills.
`codex-0.167.2-protected-paths.json` records the installed Linux x86_64 CLI binary
SHA-256 and a 406-byte machine-code excerpt with file offsets. Static inspection
of that builder shows four successive protected-name allocations: `.git`,
`.agents` (stores `.age` + `ents`), `.codex` (stores `.cod` + `ex`), `.aws`.
The npm package version is 0.167.2. This confirms the complete name list without
an inference request. The installed binary is under the CLI npm package's
`node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex`.
To recheck, hash that file and inspect the recorded byte range; all four literal
store sequences appear in the excerpt. Only newly added empty top-level
directories are exempted, including the CLI's empty directory mount stubs.
No evidence supports regular-file/symlink stubs or nonempty directories; they
are rejected. Existing packet `.agents` and every other existing entry are
checked for changes/removal. A synthetic nested bubblewrap test exercises
creating all four missing protected mounts, source/report writes, and detection.
CLI help/standalone sandbox inspection used fresh HOME and no auth/model calls;
the standalone command stopped at its app-server socket-directory validation,
so it supplies no successful command-execution evidence for the real preflight.
