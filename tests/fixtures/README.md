# Historical source fixture

`egm-registered-oaw-source.zip` contains only the OAW `scripts/` and `templates/`
registered by `evals/egm-local/spec.json` and `evals/egm-pilot/spec.json`, plus the
unchanged `pilot_common.py` needed to verify them. It was recovered from the
preserved pre-integration source snapshot and independently checked against both
registered tree digests: `a4ee3c46ac5fd15b45cd7218959bd4ea6d420da7c48b7493e3446a936705f0c7`.

The archive has 24 files, LF text, fixed ZIP timestamps and SHA-256
`744f2137a14cb9cf1e654c0d583e89ac55cae193c1de4be2eb5e76a4b53cd67c`.
No private traces, credentials, generated study answers, or model calls are in
this fixture. Original project licensing applies.

Tests restore this source to exercise the original contracts **without changing
their hashes**. They separately verify that attempting those historical runs
against the current V2 source fails closed. These tests do not measure the new
V2 product; its installer and complete EGM integration have their own tests.
