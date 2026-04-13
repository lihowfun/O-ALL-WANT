# Agent Memory Architecture — Design Origins

> This document explains the three architectural influences behind the Agent Memory Framework
> and how they integrate into a unified system.

---

## 📚 Design Origins

### 1. Andrew Ng's Context Hub

**Source**: [github.com/andrewyng/context-hub](https://github.com/andrewyng/context-hub)

**Core concepts**:
- **Versioned documents**: Knowledge preserved in structured files across sessions
- **Annotation mechanism**: AI agents can annotate knowledge files, accumulating findings
- **Context layer**: Dedicated layer manages agent context to reduce hallucination

**What we adopted**:
- ✅ `context_hub.py` — CLI tool for knowledge management (8 commands)
- ✅ Knowledge files (`docs/knowledge/*.md`) — topic-indexed permanent knowledge
- ✅ Rolling memory (`.agents/memory.md`) — cross-session decision log
- ✅ Versioned context (`VERSION.json`) — version tracking + experiment control

---

### 2. MemPalace

**Source**: [github.com/milla-jovovich/mempalace](https://github.com/milla-jovovich/mempalace)

**Core concepts**:
- **Anti-amnesia mechanism**: Force AI agents to record after every task
- **Structured reports**: Fixed format, not free text
- **Cross-session continuity**: Ensure knowledge persists between sessions

**What we adopted**:
- ✅ Mandatory Session End reports (4-section format in agent rules)
- ✅ Self-improving skill (3 mandatory rules: report, log failures, capture corrections)
- ✅ Structured TAG system (`[BUG]`, `[DECISION]`, `[EXPERIMENT]`, `[INSIGHT]`, `[WORKAROUND]`, `[ARCHITECTURE]`)
- ✅ Skills with built-in memory write steps

---

### 3. Garry Tan's "Thin Harness, Fat Skills"

**Source**: [greptile.com/blog/agents](https://greptile.com/blog/agents) (Daksh Gupta / Garry Tan)

**Core concepts**:
- **Fat Skills**: Markdown workflow files encoding domain judgment + process knowledge
- **Thin Harness**: Minimal orchestration layer (~100 lines) that routes tasks to skills
- **Resolvers**: Context routing tables — task type X auto-loads documents Y
- **Learning Loop**: Skills accumulate edge cases and improve over time

**What we adopted**:
- ✅ Skills directory (`.agents/skills/`) with reusable workflow files
- ✅ Thin agent rules file (`CLAUDE.md` < 100 lines) with task routing table
- ✅ Edge Cases learning blocks in every skill
- ✅ Skills-First Principle (follow skills before going ad-hoc)

---

## 🏗️ Integrated Architecture

### Three-Layer Memory System

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Session Memory (Built-in)                     │
│  Agent-native memory (Claude /memory, Cursor rules)     │
│  Scope: same session only                               │
│  Source: MemPalace (Rule 3: user corrections)            │
└─────────────────────────────┬───────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Rolling Memory (.agents/memory.md)            │
│  Last 20-50 important decisions/findings                │
│  Scope: cross-session, recent context                   │
│  Source: Andrew Ng + MemPalace                           │
└─────────────────────────────┬───────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Knowledge Base (docs/knowledge/*.md)          │
│  Permanent topic-indexed knowledge                      │
│  Scope: project lifetime                                │
│  Source: Andrew Ng Context Hub                           │
└─────────────────────────────────────────────────────────┘
```

### Agent Session Flow

```
Agent starts
    ↓
Read agent rules (lazy-read protocol)         ← Garry Tan: Thin Harness
    ↓
Read AI_CONTEXT.md (SSOT)                     ← Andrew Ng: Context Layer
    ↓
Read VERSION.json (version + do_not_rerun)    ← Andrew Ng: Versioned Docs
    ↓
On demand: memory.md last 5 entries           ← Andrew Ng + MemPalace
    ↓
Match task to skill (if available)            ← Garry Tan: Fat Skills
    ↓
Execute task (follow skill or ad-hoc)
    ↓
Session End: 4-section report                 ← MemPalace: Forced Reports
    ↓
Write to memory.md                            ← MemPalace: Anti-Amnesia
    ↓
If significant: annotate knowledge            ← Andrew Ng: Annotation
```

---

## 🎯 How the Three Sources Complement Each Other

| Concern | Andrew Ng | MemPalace | Garry Tan |
|---------|-----------|-----------|-----------|
| **Structure** | ✅ File organization, CLI tooling | — | ✅ Skills format spec |
| **Discipline** | — | ✅ Forced reports, failure logging | — |
| **Execution** | — | — | ✅ Reusable workflows |
| **Retention** | ✅ Knowledge files, annotations | ✅ Memory entries, TAG system | ✅ Edge case accumulation |
| **Routing** | — | — | ✅ Task routing table, resolvers |

**Combined effect**:
- Andrew Ng Context Hub provides the **infrastructure** (search, annotate, bootstrap)
- MemPalace provides the **discipline** (forced reports, structured tags, cross-session persistence)
- Garry Tan Skills provides the **execution** (turning knowledge into repeatable action)

Together they form a complete **Agent Long-Term Memory + Executable Knowledge** system.

---

## 📊 Measured Impact

### Before (no framework)
- ❌ Agent forgets decisions across sessions
- ❌ Same bugs investigated repeatedly
- ❌ Knowledge scattered across git commits, unsearchable
- ❌ No standard report format
- ❌ ~999 lines read at every session startup

### After (framework deployed)
- ✅ Rolling memory with 50+ structured entries
- ✅ Topic-indexed knowledge files with annotation support
- ✅ All skills force memory writes
- ✅ Session End 4-section report is standard
- ✅ ~212 lines at startup (-79%), rest read on demand
- ✅ ~73% token reduction on simple queries

---

## 🎓 Lessons Learned

1. **The three sources don't conflict — they complement each other**
   - Context Hub manages structure
   - MemPalace enforces discipline
   - Garry Tan enables execution

2. **Lazy-read is critical**
   - Memory.md can't grow infinitely — archive old entries
   - Knowledge is read on demand, not at startup
   - Agent rules provide the routing table

3. **Skills are the upgrade path for knowledge**
   - Knowledge says "what"
   - Skills say "how"
   - They complement, not duplicate

4. **Forced > suggested**
   - Mandatory Session End reports: enforced ✅
   - Memory writes in skills: enforced ✅
   - Edge case accumulation: suggested (still manual) — next improvement target

5. **Start small, grow organically**
   - Begin with 2-3 skills for your most repetitive tasks
   - Add knowledge files as you discover recurring topics
   - Edge cases accumulate naturally over time
