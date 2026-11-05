---
name: feedback-budget-and-consent
description: Paid model runs only inside the D13 standing budget; stop and ask beyond it; credentials and logins are the owner's alone
metadata:
  type: feedback
---

D13 standing policy: 10M logical tokens (input + output + cache) per food for tasting, 10M digestion overhead per round (question designers, graders, goldfish). Subscription billing only: unset ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL and check that every run's init event shows `apiKeySource: none`. Anything beyond the cap, or any other billing source, stops and asks the owner first.

**Why:** the owner stopped an earlier step with "F1是我要花錢?? 如果是請停止"; they also want as few logins as possible ("儘量減少我登入什麼有的沒的操作").

**How to apply:** track tokens per food in the records; never type passwords, tokens or OAuth codes for the owner - write a kit with exact commands and expected output instead; execution of food code is allowed only in the tasting area ("可以執行 不然你怎麼測 我允許"). Related: [[oaw-catalog-intake-rules]], [[feedback-github-codev-handoff]].
