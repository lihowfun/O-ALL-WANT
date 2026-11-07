# R checklist (frozen 2026-11-08, before any X2 case is written)

Source: the REVIEW-mode audit vectors of the upstream EGM reviewers (`agents/comprehension.md`,
`design_critic.md`, `implementation_readiness.md`, `codebase_details.md`, `zoom_out.md`) and
`resources/document_standards/implementation-readiness-standard.md`, google/elephant-goldfish-model @ f0ba151.
Style and heading-structure vectors are left out: they are not design defects. The case authors never see this
file. The text between the markers is appended to the R arm's review prompt, word for word.

<!-- R:begin -->
Before writing the report, check the design against each point below. A point that does not apply is skipped.
1. Paraphrase what the design proposes and how the existing system works according to it. A part you cannot
   paraphrase is a gap.
2. Every project-specific component, service or term the design relies on is defined or pointed to.
3. No step assumes setup, prerequisites or side effects the sources do not state.
4. Claims about behavior, performance, capacity or external systems are justified by the sources.
5. Failure modes, scaling limits, single points of failure, security and operational risks the design introduces
   are addressed.
6. Statements about the current system match the source code, and every file, function, endpoint or table cited
   as existing exists.
7. The design addresses the root problem, fits the project's existing direction and reuses what already exists.
8. The plan leaves no design decision to the implementer: it names the files to change, the concrete steps, the
   tests, and phases that each leave the system working.
9. Nothing is added for speculative future needs or optimized without a stated reason.
<!-- R:end -->
