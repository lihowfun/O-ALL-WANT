# LLM Wiki Topic Board

Use this board to make wiki work visible. Keep it lightweight: one topic, one
owner, one next action.

## High-Value Gaps

| Topic | Status | Why It Matters | Next Action |
|-------|--------|----------------|-------------|
| `New_Project_Onboarding` | Proposed | Fresh installs need a better first prompt and project-mapping flow | Add raw source from installer/README decisions |
| `Multi_Agent_Worktrees` | Proposed | OAW users often run parallel agents and need conflict-safe branch rules | Capture current worktree conventions |
| `Wiki_Quality_Gates` | Proposed | LLM-wiki pages need source, freshness, and anti-slop checks | Document lint rules and examples |
| `Skill_Promotion_Policy` | Proposed | Teams need to know when a repeated workflow should leave wiki and become a skill | Draft promotion criteria |
| `Agent_Adapter_Field_Reports` | Proposed | Claude Code, Codex, Cursor, Copilot, Gemini, and Windsurf may need different startup behavior | Collect field reports in raw notes |

## Stale Or Source-Needed Topics

| Topic | Signal | Next Action |
|-------|--------|-------------|
| `Release_Learnings` | Manual page with no `source_refs` | Add a raw source note or stable source metadata |
| `OAW_Session_Continuity_Test` | Contains intentional placeholder examples | Keep as test evidence; avoid strict lint unless placeholders are expected |

## Skill Candidates

| Candidate Skill | Trigger | Source Topic |
|-----------------|---------|--------------|
| `wiki-quality-review` | "review wiki quality" | `Wiki_Quality_Gates` |
| `skill-promotion` | "turn this repeated workflow into a skill" | `Skill_Promotion_Policy` |
| `worktree-collaboration` | "split this across worktrees" | `Multi_Agent_Worktrees` |

## How To Use This Board

1. Pick one row and create or update a raw source note.
2. Refresh the corresponding topic with `wiki_sync.py`.
3. Update the status in this board only after the topic is discoverable.
4. If the topic becomes a repeatable procedure, move it to Skill Candidates.
