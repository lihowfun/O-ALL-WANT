---
name: egm-review-loop
description: "Executes the Antagonistic-Review process from the Elephant-Goldfish Model (EGM) via an automated multi-agent review loop to audit documents against qualitative standards and structural templates, and automatically apply approved fixes. Use when reviewing design docs, READMEs, feature specifications, implementation plans, or verifying document completeness and tone."
license: Apache-2.0
disable-model-invocation: true
---

# egm-review-loop

Read the complete, unmodified upstream entry before using this skill:

`../../../.oaw/integrations/egm/skills/egm-review-loop/SKILL.md`

Resolve that path from this SKILL.md directory (works for both native host layouts). Resolve the upstream entry's relative references from its own directory, not this bridge. The runtime includes all personas, standards, host instructions and licenses.

Project-install bindings: resolve the upstream runtime root to an absolute path. In upstream text, `${CLAUDE_PLUGIN_ROOT}` means that resolved root; the host does not substitute it in project files. Plugin-qualified `egm:egm-*` names map to the project's `egm-*` skill/agent names. Read the corresponding bundled entry when the workflow calls another manual skill. Standalone marketplace installation instructions describe an alternative installation; this project already has the complete pinned runtime. Preserve all upstream stage, tool, isolation and human checkpoint requirements. If the host cannot provide them, report the missing capability and stop that workflow.

This is an OAW v2 entrypoint adapter, not a rewritten EGM workflow. Source: https://github.com/google/elephant-goldfish-model/tree/f0ba151b252c9abf1318d9fe857a43265d06de89; manifest 0.1.0; Apache-2.0. The installed OAW_SOURCE.json records exact upstream file hashes.
