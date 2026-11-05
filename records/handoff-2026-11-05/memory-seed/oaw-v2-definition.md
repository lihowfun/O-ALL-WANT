---
name: oaw-v2-definition
description: "What \"OAW V2\" means for the user, and wording to avoid"
metadata:
  type: project
---

OAW V2 = OAW v1 upgrade (old flat skills retired) + bundled EGM (google/elephant-goldfish-model, pinned f0ba151). Never write "V2+EGM" or "OAW+EGM" in new docs; historical/frozen records keep their original wording.

**Why:** the user defined V2 this way on 2026-10-30; Codex implemented it in commit 341b450 (EGM installed under .oaw/integrations/egm with bridge skills), and a duplicate Claude branch was deleted.

**How to apply:** describe bundling EGM as a product decision, not a measured gain (an earlier Codex study found no detection gain over native). Related: [[oaw-catalog-intake-rules]].
