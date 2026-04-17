# Examples

Two shipped examples. Start with **`minimal-project/`**.

## 🟢 `minimal-project/` — Start Here

A committed post-install snapshot. Open this first if you want to know:

- What does a freshly installed project look like?
- Which files are the harness vs. which files are my own work?
- Which commands does the smoke test run?

This is the smallest complete OAW footprint — the easiest thing to read.

## 📚 `public-hybrid-demo/` — Full-Featured Demo

A more populated example showing all four lanes in action:

- Operational lane (AI_CONTEXT / ROADMAP / VERSION / recent memory)
- Wiki lane (compiled `docs/knowledge/` topic pages with `index.md` + `log.md`)
- Execution lane (reusable `.agents/skills/`)
- Raw-source fallback (`docs/raw/` source notes that feed the wiki)

Open this when you want to see `scripts/wiki_sync.py build` produce real
compiled pages, or to study how raw notes map to knowledge topics.

## Which should I copy from?

If you're not sure, copy from **`minimal-project/`** and only look at
`public-hybrid-demo/` when you actually want the raw→wiki pipeline.
Most projects never need `docs/raw/`.
