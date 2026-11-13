# Release polish design — #10 / #12

2026-11-13. Product base `c2d9852bf8cabf13fd86a4340ab89f69044cae5a`.
This work prepares the remaining release requirements while FIXCHECK stays pinned to that base. It does not change the preregistration, run a new experiment or decide release.

## Evidence and scope

GitHub #12 requires upstream EGM documentation pointers, consent before writing settings outside the target repo, and shorter doctor output. #10 requires benefit/capability evaluation tracks and D38/D41/D42 references; this differs from maintainer/user installation routes.

[FEEDBACK_PROBE.json](FEEDBACK_PROBE.json) reproduces an isolated both-host install: init/doctor exit 0, doctor prints 141 lines with 136 PASS checks, checkout locator is written outside the project without explicit opt-in. All 14 EGM bridges and four upstream guide files resolve inside the installed project. No model answers.

## External checkout locator: explicit opt-in

- Add `--remember-checkout` to `init`, `migrate` and `add`. Default false. Neither a writable config directory nor `OAW_CONFIG_HOME` implies permission.
- The flag authorizes only the existing OAW checkout locator (`checkout.json`), at the concrete path derived by `config_home()`. It does not authorize other global settings.
- Default install still fully works by explicit OAW checkout path. Existing locator files are left unchanged when the flag is absent; no silent refresh or delete.
- A migrate/add preview reports the external destination and proposed locator content if selected, without creating directories or writing it. Actual write requires the existing apply action too. init already applies by definition.
- The add terminal's existing install question includes the outside-project destination and opt-in choice. No second mandatory question. Noninteractive calls carry explicit `--remember-checkout` through the generated apply command.
- The consent choice is separate from hooks/MCP/scripts consent and does not expand those permissions.
- Restrict the existing `remember_checkout` call sites in `oaw.py` and `user_install.py` to this choice. Report selected write failure as a warning; do not pretend registration succeeded. Project installation results remain truthful.
- Help and CLI/upgrade docs list default locations by OS plus override. The oaw-add skill documents the optional locator and its existing explicit-checkout fallback.

## Doctor: summarize presentation, preserve checks

- Default human output: health, total PASS/WARN/FAIL counts, every WARN/FAIL with its path and detail, and concise host discovery state. Do not dump individual PASS entries.
- `doctor --verbose` gives the current full check details. `--json` retains the full structured contract, irrespective of verbose.
- Keep health/exit-code logic, validators and capability facts unchanged. Unknown native discovery is still UNKNOWN. The summary must not turn a packaged adapter into a verified host runtime.
- Print the full-detail command in the concise output. Other commands retain their current output.

## EGM guide pointers

- Add stable links to the bundled upstream getting-started and host guides from README and upgrade/CLI docs. Explain the installed paths under `.oaw/integrations/egm/docs/` and the pinned upstream revision.
- Do not modify vendored upstream bytes or add startup rules. Current bridge paths work; this is discoverability/documentation repair.
- Check both native host layouts and the referenced documents in an actual temporary install.

## Intake SOP and release copy

- Incorporate benefit/capability tracks from value-check `4, using native + identical underlying tools for capability controls, mechanical artifact checks, and installed-but-idle costs.
- Distinguish the purpose axis from maintainer defaults versus user install choice.
- Capability candidates can be optional or rejected, never default; incomplete/infrastructure/ceiling-limited evidence has no verdict under its preregistration.
- D38 states the purposes and draft capability gates; D41 selects PPT/video and allows draft tests before execution; D42 is specifically H1's declared ceiling-fill amendment, not a general license to change frozen tasks.
- OAW itself faces the same outcome gate. H1 remains combined inconclusive; FIXCHECK is diagnostic regression evidence only.
- Resolve stale blanket prototype statements against current code. Leave genuinely unverified limits explicit.
- Version remains unchanged until FIXCHECK disposition and final release checks. README candidate wording is in RELEASE_COPY.md and needs final conditional paragraph only after results.

## Acceptance criteria

1. Default init/migrate/add never create or refresh the external locator, even with OAW_CONFIG_HOME set. Explicit selected apply writes only the expected locator; preview never writes; failures are visible.
2. The existing add question and generated noninteractive command preserve the exact selected consent. Hooks/MCP/scripts authorization is unaffected.
3. Default doctor hides PASS rows but retains every warning/failure and UNKNOWN discovery; verbose and JSON retain complete facts and exit behavior.
4. Both-host installed EGM references resolve, vendored hashes stay unchanged, and docs accurately distinguish the two purpose/installation axes with source decisions.
5. Focused regressions and the full product gate pass. No new model trial, no FIXCHECK input mutation, no automatic merge/tag.

Implementation is prepared on a separate worktree. Integrate only into the final release candidate after FIXCHECK's keep/revert disposition; rerun final gate and CI as D45 requires.
