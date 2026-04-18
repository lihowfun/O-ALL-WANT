# Security Policy

## Reporting a Vulnerability

OAW is a shell-based installer + Python CLI for managing local agent
context files. It does not ship network daemons, does not handle
credentials, and runs entirely on the user's machine.

That said, if you find anything that looks like a security issue —
command injection in scripts, unexpected file writes outside the
target project, or credential leakage through logs — please email
**lihowfun@gmail.com** with the subject line `[OAW security]`
instead of opening a public issue.

You should expect an acknowledgement within **72 hours**. A fix
timeline will depend on severity.

## Scope

In scope:
- `install.sh` (shell safety, overwrite protection)
- `scripts/context_hub.py` + `scripts/wiki_sync.py` (file handling,
  path traversal, YAML frontmatter parsing)
- Anything in `templates/` that would be copied into user projects

Out of scope:
- Vulnerabilities in dependencies pulled by user's AI agent
  (Claude Code, Codex, etc.)
- Behavior of third-party repos referenced in `Source Lineage`
