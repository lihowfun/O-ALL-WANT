---
name: feedback-taste-before-judging
description: OAW skill intake must actually run (taste) a food in a safe tasting area before deciding to absorb it; reading its code is not enough
metadata:
  type: feedback
---

Never judge whether to absorb a skill/food from reading its code alone. Run it first in a tasting area: a local detached worktree of OAW 2 (no new branch, never pushed), the food in its own environment (e.g. a separate venv or conda env), no API keys, its installer/hooks only when tasting them is the point. Network cut-off is not needed. Then compare three arms on the same questions (native / food as-is / OAW version), zero-token checks first, and end in absorb, plug in, or decline. Recorded as D25 (2026-11-04), refining D17.

**Why:** On 2026-11-04 the owner found that graphify, claude-mem and TokenEconomizer had never been executed, yet absorption decisions had been made ("你從來就沒有graphify 執行過 那你怎麼判斷該不該吸收的"; "試吃就是在安全環境吃看看啊"; "為啥要斷網 就OAW 2 拉一個worktree or brance"). The first real tasting of graphify took minutes and overturned the static picture.

**How to apply:** Before any absorb/decline verdict, check the food has a tasting record; if not, taste it first. Don't over-isolate (no network cut needed). Related: [[oaw-intake-flow-v1]], [[oaw-catalog-intake-rules]], [[reference-oaw-handoff]].
