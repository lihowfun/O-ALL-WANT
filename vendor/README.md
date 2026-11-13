# Vendored EGM runtime

OAW V2 includes the complete runtime selected by Google's official
`scripts/pack_plugin.py` at
[`f0ba151b252c9abf1318d9fe857a43265d06de89`](https://github.com/google/elephant-goldfish-model/tree/f0ba151b252c9abf1318d9fe857a43265d06de89),
manifest 0.1.0, licensed under Apache-2.0. The license is retained in
`egm/LICENSE`. Upstream runtime files retain their exact Git-blob bytes,
copyright material and host manifests. `egm/OAW_SOURCE.json` records each hash;
its own independent hash is pinned in `scripts/oaw.py`.

OAW modifications are outside that upstream inventory: seven lightweight native
skill entrypoints, Codex invocation-policy metadata and nine Claude agent path
adapters. They bind plugin-qualified names to native project names while preserving upstream workflow text, tools and fresh-context policy.
The packaging selection in `scripts/sync_egm.py` is adapted from the cited
Google Apache-2.0 packager. Regenerate from a local pinned clone with
`python3 scripts/sync_egm.py --repo /path/to/EGM --write`; verify committed files
without network using `--check-bundled`.

V2 ships the runtime, not upstream development tests or upstream Git history.
The future external-skill catalog and automatic recommendation pipeline remain
unimplemented. Inclusion is not proof of host discovery or model quality gain.
