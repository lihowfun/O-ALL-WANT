# Known Limitations

> Track known bugs, workarounds, and limitations. Agents read this when debugging.

---

## Active Limitations

### Native Windows runtime still needs a real smoke test

**Symptom**: The CLI now includes a Windows file-lock backend, but the repo has
not yet been exercised on an actual Windows machine.
**Root Cause**: P0 validation was performed on macOS; Windows behavior was
covered with a mocked `msvcrt` smoke test rather than a native shell run.
**Workaround**: Treat Windows as provisionally supported and run `status`,
`memory add`, and `annotate` before public release.
**Status**: 🟡 Open — schedule one native Windows fixture run before launch

---

## Resolved

### `memory add` dropped the leading character after `[TAG]`

**Resolution**: Replaced the old `lstrip()` logic with a single-prefix regex so
tagged entries preserve their full text.

<!-- Move items here when fixed. Keep for historical reference. -->

---

## AI Annotations

<!-- Auto-appended by agents via: python3 scripts/context_hub.py annotate Known_Limitations "note" -->
