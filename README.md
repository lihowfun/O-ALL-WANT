# O-ALL-WANT (OAW)

Portable project evidence and native skills for coding agents. **v2.0.0 is proposed in a PR; it is not a published release.**

[繁體中文](README.zh.md) · [Upgrade guide](docs/UPGRADING.md) · [CLI reference](docs/CLI_Reference.md) · [Execution plan](docs/plans/v2.0.0-execution.md)

OAW keeps the project knowledge that code alone cannot explain: decisions, external constraints, experiments and their evidence. Claude Code, Codex, or your chosen host continues to manage the agent loop, sessions, compaction, personal memory, permissions, and skill discovery.

## Start small

Requires Python 3.10+; runtime uses only the standard library. From the framework checkout:

```bash
python3 scripts/oaw.py init --target /path/to/project
python3 scripts/oaw.py doctor --target /path/to/project
```

Codex is the default skill destination. Use `--host claude` or `--host both`
on init/migrate to install native skill folders for Claude Code or both hosts.

The default installs five framework files: a short AGENTS.md, a Claude compatibility import, one native evidence skill, and Context Hub with its shared helper. It creates no memory log, placeholder architecture, roadmap, root VERSION.json, or mandatory session workflow. Existing different content is protected.

The Bash shortcut, run from the target project, is:

```bash
bash /path/to/O-ALL-WANT/install.sh
```

Additional capabilities are explicit:

```bash
# Deterministic raw-to-wiki rendering and the wiki skill
python3 scripts/oaw.py init --target /path/to/project --profile knowledge

# Optional evidence-driven improvement proposals; no background agent
python3 scripts/oaw.py init --target /path/to/project --with-improve
```

`--profile knowledge` and `--with-improve` are additive on an existing v2 installation. [Minimal example](example/minimal-project/) · [Knowledge and improvement example](example/public-hybrid-demo/)

## Upgrade an existing OAW project

```bash
python3 scripts/oaw.py migrate --target /path/to/project           # preview only
python3 scripts/oaw.py migrate --target /path/to/project --apply   # backups + proposals
```

Known unmodified framework files can update. Custom policy and skills conflicts become proposals; they are not overwritten. Existing memory, knowledge, raw notes, AI_CONTEXT.md, ROADMAP.md and root VERSION.json remain project-owned. Unchanged legacy flat skills/adapters can retire into recoverable backups. Review unresolved proposals before treating migration as complete. See [UPGRADING](docs/UPGRADING.md).

## Use evidence when it helps

Run these from an installed project:

```bash
python3 scripts/context_hub.py memory recall "cache decision" --json --max-chars 12000
python3 scripts/context_hub.py memory add "[DECISION] Keep the cache local — evidence: docs/experiment.md"
python3 scripts/context_hub.py get Cache_Decision
```

Recall returns bounded records with source locations, truncation and continuation. Project notes are unverified evidence to check against current code and authoritative sources, not instructions that override the user. Record durable information selectively; native personal memories remain the host's responsibility.

The knowledge profile adds `python3 scripts/wiki_sync.py refresh Topic` and `lint`. This is a deterministic renderer, not an LLM summarizer or an autonomous knowledge curator.

## Self-improvement with a stopping condition

The opt-in workflow stores a hypothesis, concrete candidate diff and fixed evaluation specification. Compare matched baseline/candidate run artifacts before recording an accept/reject decision. Quality regressions, excessive resource regressions, missing evidence or mismatched runs block acceptance. Accepting never applies a patch.

[Self-improvement guide](docs/SELF_IMPROVEMENT.md) · [Native ablation contract](evals/native-ablation/spec.json)

This replaces mandatory memory nudges, manual skill counters and a skill-review after every multi-step task. A task that teaches nothing reusable needs no permanent record.

## Native integrations and limits

Skills use `<skill>/SKILL.md`. Codex uses `.agents/skills`; `--host claude` routes skills to `.claude/skills`, and `--host both` installs both from one authored source. The Claude compatibility import shares project policy. See the [skill guide](docs/Skill_Guide.md). OAW does not silently edit host settings or claim that memories are enabled. Doctor reports host capability/enablement separately.

The design targets current Claude Code with Opus 5.5 and Codex with GPT-6.1 Sol without hardcoding a model into the toolkit. Local schema tests do not prove live discovery in either host, and no native model A/B improvement is claimed. The old 86–87% figure compared selected Markdown with loading everything; it is a historical illustration, not a v2 benchmark.

## Development

```bash
python3 scripts/harness_check.py
python3 scripts/harness_check.py --json
python3 scripts/sync_examples.py --write
```

The gate exercises meaningful behavior regressions, installer migration, native skill validation, CLI contracts, and complete generated example content. CI uses the same entry point on Ubuntu, macOS and Windows with Python 3.10 and 3.13. See [CONTRIBUTING](CONTRIBUTING.md) and [CHANGELOG](CHANGELOG.md).

## Source lineage

The original project drew on [Context Hub](https://github.com/andrewyng/context-hub), [MemPalace](https://github.com/MemPalace/mempalace), and [Karpathy's LLM wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). v2 borrows bounded tool-output and lifecycle boundaries from current harness designs, including [Pi](https://github.com/earendil-works/pi), [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview), and [Hermes](https://hermes-agent.nousresearch.com/docs/). It does not embed those runtimes. Historical attribution remains in [Architecture Origins](docs/Architecture_Origins.md).

MIT License.
