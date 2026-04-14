---
name: experiment-report
description: "Condense an experiment into a reusable finding"
triggers: ["experiment report", "summarize experiment", "write findings"]
params:
  EXPERIMENT_FILE: "path to the experiment markdown file"
requires:
  - AI_CONTEXT.md
optional_reads:
  - docs/knowledge/Experiment_Findings.md
outputs:
  - .agents/memory.md entry
---

# /experiment-report — Condense Findings

1. Read the experiment record
2. Extract question, result, and next decision
3. Update `docs/raw/experiment_findings_source.md`
4. Run `python3 scripts/wiki_sync.py refresh Experiment_Findings`
5. Write the decision to `.agents/memory.md`
