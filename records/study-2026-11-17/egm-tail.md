References are to **HEAD**, unless a commit is named. No repository code, tests, installers, or package managers were run.

**1. Designs and evidence of their own process**

The index describes these as canonical specifications; it is an inventory, not a review ledger (`docs/designs/README.md:3–26`).

For rows saying “no ledger,” I found no recorded review rounds or linked brief/draft/resolution reports. That is an **inspection finding**, not proof that reviews never happened.

| Document | Designs; status; evidence of process applied to itself |
|---|---|
| `architecture.md` | Overall architecture; **Current**. Shows the intended brainstorm→draft→review→resolve→human-review sequence, without its own execution ledger (`docs/designs/architecture.md:4,94–111`). |
| `brainstorm.md` | Early ideation and seven lenses; **Current**. Describes approval and refinement, not its own rounds (`docs/designs/brainstorm.md:4,55–98`). |
| `draft.md` | Sectional drafting and semantic ranges; **Current**. Describes brief→draft reconciliation and review handoff; no self-review ledger (`docs/designs/draft.md:4,96–137`). |
| `review.md` | Staged review, resolution, convergence; **Current**. Its rounds are prescribed behavior, not recorded self-review (`docs/designs/review.md:4,168–178`). |
| `synthesizer.md` | Swarm dispatch and aggregation; **Current**. Defines artifact contracts, without a self-review ledger (`docs/designs/synthesizer.md:4,60–110`). |
| `bootstrap.md` | Recursive README generation; **Current**. Contains verification plans/scenarios, not recorded design-review rounds (`docs/designs/bootstrap.md:4,776–796`). |
| `drift_report.md` | Specification/code divergence audits; **Current**. Records testing limitations, not its own review history (`docs/designs/drift_report.md:4,117–119`). |
| `runtime_packaging.md` | Runtime boundaries and permissions; **Implemented #136**. Directory approval and exact-artifact verification remain separate; no round ledger (`docs/designs/runtime_packaging.md:3,100–107`). |
| `releases.md` | Versioned archives/provenance; **Implemented #137**. Retains an older explicit disclaimer that it does not claim an EGM review run (`docs/designs/releases.md:3,99–100`). |
| `skill_icons.md` | Shared artwork; **Implemented**. Records merged artwork and verification limits, not review rounds (`docs/designs/skill_icons.md:3,44–51`). |
| `claude_release_branch_distribution.md` | Generated Claude release branch; **Draft**. Footer: “Revised after three EGM reviews”; additionally reviewed with `egm-review-loop` November 9. Open questions have owners/gates; one records an owner’s answer while still requiring portal verification. No linked brief/report chain (`docs/designs/claude_release_branch_distribution.md:4,76–101,586`). |
| `additional-harnesses.md` | Cursor/OpenCode/Copilot contracts; **Proposal**. Explicitly says full EGM review has not run; maintainer decisions remain (`docs/designs/additional-harnesses.md:4,235–242`). |
| `multi_harness_support.md` | Hermes/OpenClaw/Delta requirements; **Stage 1 proposal**. Native contracts/runs remain unverified; no completed review ledger (`docs/designs/multi_harness_support.md:4,45–59`). |
| `plugin_listing_presentation.md` | Listing/package presentation; **Proposed**. Earlier fresh-context Design Critic/Readiness review does not approve expanded scope; full protocol pending (`docs/designs/plugin_listing_presentation.md:4,319–324`). |
| `site_documentation.md` | Documentation website; **Proposed**. Records initial rubric reviews, comprehension resolution and readiness fixes; later Structural/Style/Design reviews. Explicitly denies full protocol completion/convergence (`docs/designs/site_documentation.md:4,442–456`). |
| `ask.md` | Read-only contextual help; **Draft**. Implementation and tests are prospective; no self-review ledger (`docs/designs/ask.md:4,256–285`). |
| `triz_integration.md` | Inventive Catalyst integration; **Draft**. Specifies workflow changes and verification, without recorded self-review rounds (`docs/designs/triz_integration.md:20,245–281,551–555`). |
| `windsurf_support.md` | Workspace routing/isolation; **Proposal**. Records Structural/Style/Design review and resolution of all Blocker/Major findings; no round count or artifact chain (`docs/designs/windsurf_support.md:4,229–243`). |

**Conclusion from the records:** none demonstrates a fully artifact-linked brainstorm→draft→review→resolve loop. Claude distribution explicitly claims **three reviews plus a later loop review**, not three documented complete loops. Website records **two review episodes**; Windsurf records a review session; neither supplies convergence counts (references above).

**2. Verification and benefit evidence**

Offline tests cover frontmatter, links, manifests, packaging and metadata on Ubuntu/Windows; they do not establish host workflow support (`TESTING.md:41–57`). `conftest.py` discovers nonhidden skill directories; scenario coverage checks YAML shape, skill-name matching, IDs, evaluation type and nonempty turns—not execution of behavioral assertions (`tests/conftest.py:23–38`; `tests/unit/test_scenario_coverage.py:23–53`).

A scenario supplies a skill, user turns and required/forbidden regexes: the missing-SLO example accepts “SLO,” “latency,” “consistency,” or “replication lag” (`skills/egm-review/test_scenarios.yaml:67–77`). Suites describe drafting approvals, brainstorm gates, resolution, convergence, bootstrap grounding and drift; drift’s design explicitly says **“no in-repo runner executes the assertion”** (`skills/egm-draft/test_scenarios.yaml:31–68`; `skills/egm-brainstorm/test_scenarios.yaml:19–50`; `skills/egm-resolve/test_scenarios.yaml:19–42`; `skills/egm-review-loop/test_scenarios.yaml:31–53`; `skills/egm-bootstrap/test_scenarios.yaml:43–59`; `docs/designs/drift_report.md:119`).

Opt-in Claude probes check actual persona reads, denied-read behavior and context markers—not the full workflow (`TESTING.md:89–102`). Codex tests inspect native starts/completions, isolation flags, installed reads, artifacts, draft equality and absence of implementation code. Its fixture preapproves human gates; interactive behavior and nesting are explicitly excluded (`tests/integration/test_codex.py:99–130,273–320`).

Recorded workflow evidence covers Antigravity, Claude Code, Codex and Muse; Cowork/ChatGPT remain partial, omp discovery-only. OpenCode uses a scripted local model; Cursor/Copilot discovery probes do not establish live workflows (`TESTING.md:145–152`; `docs/opencode.md:130–149`; `docs/cursor.md:156–160`; `docs/copilot.md:148–160`).

I found **no measured benefit** in quality, defects or cost. The FAQ says: “Completing the EGM workflow alone does not demonstrate a productivity improvement.” Runtime/token costs are explicitly unmeasured; recorded seconds measure fixtures, **not benefit**—an inference (`docs/faq.md:45–46`; `docs/designs/multi_harness_support.md:41`; `TESTING.md:149`). The homepage supplies an illustrative plan/findings, not evaluation results (`site/src/components/Home.astro:44–51`).

**3. Hosts**

Install the whole package: skills require personas and standards. `.plugin/plugin.json` supplies compatibility metadata, not a separate execution engine (`docs/harnesses.md:24–26,54–75`; `.plugin/plugin.json:1–12`).

The following invocation patterns apply to the seven shipped skill names (`tests/unit/test_harnesses.py:28–31`):

| Host | Start and requirements/differences |
|---|---|
| Antigravity | `/egm:egm-*`; native `invoke_subagent`, named personas/nesting. Standalone IDE lacks required delegation; App/extension command forms remain unverified (`skills/egm-draft/SKILL.md:320`; `docs/harnesses.md:32–50,93–111`). |
| Claude Code | `/egm:egm-*`; subordinate skills read in-thread because `Skill` refuses them. ≥2.1.271; adapters inherit model, allow Read/Grep/Glob and omit instruction files (`docs/claude.md:8–24,131–163`). |
| Cowork | Install then **Try in chat**; command form unrecorded. Direct dispatch because children cannot delegate (`docs/claude.md:41–43,174–182`; `docs/harnesses.md:161`). |
| Codex/ChatGPT | Codex skill picker; workspace ChatGPT `@egm`. General-purpose children read personas; inspect actual spawn schema and disable inherited turns. Host instructions may still leak (`docs/codex.md:19–28,49–79`; `docs/harnesses.md:161`). |
| omp/Muse | omp `/skill:egm-*`; Muse `plugin:egm:egm-*`. Muse named spawning fails in tested runtime; fallback works, but Claude tool restrictions do not (`docs/harnesses.md:163`; `docs/muse.md:36–38,59–75`). |
| Cursor | Experimental slash selection or explicit skill-file read; fresh Tasks, inherited model, read-only configuration, parent synthesis. Runtime enforcement unverified (`docs/cursor.md:23–34,75–115`). |
| Copilot | Experimental `egm:egm` entry agent plus named skill request; reviewer read/search allowlist; direct dispatch (`docs/copilot.md:40–56,82–118`). |
| OpenCode | Experimental ordinary-message request; fresh V1 `task`, no `task_id`; read/glob only. Slash arguments undergo shell preprocessing (`docs/opencode.md:44–55,66–108`). |
| Windsurf | Seven thin workflows/shared-file routing; swarm stops without fresh read-only children; parent writes after approval. CLI evidence reaches no final artifact; IDE untested (`.windsurf/workflows/egm-review.md:5–9`; `.windsurf/rules/egm.md:8–12`; `docs/harnesses.md:167`). |

Human gates survive missing question widgets: ask in chat and wait. Uninterrupted review removes checkpoints **between stages**, preserving sequential dependencies (`docs/designs/additional-harnesses.md:84–95`; `docs/claude.md:44–47`).

**4. Changes after the vendored commit**

Themes are website/presentation, distribution/releases, host adapters, CI/security/triage, contribution documentation, dependencies, and workflow behavior. The behavior-changing commits and principal runtime files are:

- `de27902`: authorship fallback and evidence-backed rejection attribution—brainstorm/draft skills, draft template, feature standard (`skills/egm-brainstorm/SKILL.md:106–109,204`; `skills/egm-draft/SKILL.md:164,211`; `resources/document_standards/feature-spec-standard.md:19–21`).
- `36343a1`: host-correct handoffs—brainstorm/draft (`skills/egm-brainstorm/SKILL.md:256–263`; `skills/egm-draft/SKILL.md:320`).
- `6efc127`: calibrated caveats and explicit implementation file boundaries—Style persona/readiness standard (`agents/style.md:38–48`; `resources/document_standards/implementation-readiness-standard.md:29–33`).
- `3dba384`: private scratch directories—execution instructions/bootstrap (`resources/execution_instructions.md:7–14`; `skills/egm-bootstrap/SKILL.md:57–59`).
- `85da146`, `9f61952`: outside artifact-directory confirmation; synthesizer writes only requested artifacts—host guides/Claude adapter (`docs/codex.md:30–35`; `.claude-plugin/agents/synthesizer.md:14–20`).
- `244292c`, `113a3af`: approve outside links, materialize URLs, propagate context—review/review-loop (`skills/egm-review/SKILL.md:101–120`; `skills/egm-review-loop/SKILL.md:54–65`).
- `84dad26`: preserve Blocker/Major/Nit—resolve (`skills/egm-resolve/SKILL.md:98`).
- `6a8001e`: TRIZ persona, seventh brainstorm lens, Stage-5 pairing and host registrations (`agents/synthesizer.md:29–34`; `skills/egm-review/SKILL.md:287–289`; `.claude-plugin/plugin.json:24`).
- `51cfc42`, `2665d1f`: broader source extensions and .NET verification detection—bootstrap (`skills/egm-bootstrap/SKILL.md:81,133–139,297`).
- `5220a0b`, `8450f11`, `86125d1`, `964a4f1`: Cursor/OpenCode/Copilot/Windsurf adapters described above; `69fb200` adds VS Code discovery (`.vscode/settings.json:2–6`).

**5. Upstream’s own PR review**

Triage uses trusted default-branch code and separates read-only planning from posting (`.github/workflows/pr-triage-review.yml:18–19,57–68,119–143`). It hunts changed-line Blocker/Major defects, then sends candidates to a separate fresh-context **disproof** request; default maximum is five comments (`.github/scripts/review_pr.py:53,1127–1134,1183–1196,1652–1664`).

It skips drafts, bots, duplicate SHAs and already-human-reviewed PRs unless overridden; clean results route to maintainers, not approval (`.github/scripts/review_pr.py:706–744,1050–1069`). Scope advice is explicitly nonblocking; Stage-1 verification asks for review, resolve and remaining findings (`.github/workflows/pr-scope-advisory.yml:106–112`; `.github/PULL_REQUEST_TEMPLATE.md:34`). **Inference:** intended use includes challenging AI findings and preserving human judgment.

**6. Scope, cost and stopping**

Use skills fluidly; simple fixes need not follow design-first. Prioritize consequential work (`docs/getting_started.md:40–53`; `docs/faq.md:35–43`). No universal design page budget was found; drafting is sectional. The 24,000-byte limit concerns skill loading (`docs/designs/draft.md:39–50`; `tests/unit/test_skill_load_limits.py:15–20`).

Loops require two consecutive clean rounds, flag missing reviewers, and ask at five rounds/churn; humans may halt (`skills/egm-review-loop/SKILL.md:159–187`). `egm-ask` is designed but unshipped; TRIZ is shipped despite its Draft design status (`docs/designs/ask.md:52–70,260–268`; `tests/unit/test_harnesses.py:28–35`).

## What a careful adopter would miss by using only one non-interactive egm-review pass

- Upstream problem exploration, explicit alternatives and section approvals (`docs/designs/brainstorm.md:55–98`; `docs/designs/draft.md:39–50`).
- Resolution, accepted risks and convergence: uninterrupted mode produces reports; looping has separate stopping rules (`skills/egm-review/SKILL.md:280–313`; `skills/egm-review-loop/SKILL.md:159–187`).
- Human architecture/peer-review responsibility and later drift reconciliation (`docs/designs/architecture.md:149–169`).
- Host-specific isolation limits and missing-read failures (`docs/codex.md:58–79`).
- Newer context safeguards/TRIZ, absent from the vendored behavior, plus the need to measure benefit on actual tasks (`skills/egm-review/SKILL.md:101–120,287–289`; `docs/faq.md:45–46`).