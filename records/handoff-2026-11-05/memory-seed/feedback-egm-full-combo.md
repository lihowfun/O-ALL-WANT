---
name: feedback-egm-full-combo
description: "When reviewing or digesting, use EGM's full Elephant -> Goldfish -> owner combination, and build the Elephant from recorded decisions"
metadata:
  type: feedback
---

Use the full EGM pattern: an Elephant agent with full project context drafts (proposals, absorption plans), two or more zero-context Goldfish agents blind-review THAT draft, the Elephant resolves their findings, and the owner decides. Goldfish-reviewing only the external food, or using an adversarial fact-checker in place of a goldfish, is not enough.

**Why:** on 2026-11-03 the user noticed the digestion workflow used only goldfish review on the foods and no Elephant, so our own proposals got no blind review; the user asked why the best combination was skipped.

**How to apply:** before an Elephant step, write the owner's decisions into a dated, sourced decision record (OAW evidence) so a fresh agent can be the Elephant without the chat transcript; do not rely on prompt-pasting from controller memory. See [[oaw-catalog-intake-rules]] and [[oaw-v2-definition]].
