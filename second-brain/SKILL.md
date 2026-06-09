---
name: second-brain
description: >
 File-based memory system using Tiago Forte's PARA method. Use this skill whenever
 you need to store, retrieve, update, or organize knowledge across sessions. Covers
 three memory layers: (1) Knowledge graph in PARA folders with atomic YAML facts,
 (2) Daily notes as raw timeline, (3) Tacit knowledge about user patterns. Also
 handles planning files, memory decay, weekly synthesis, and recall via qmd.
 Trigger on any memory operation: saving facts, writing daily notes, creating
 entities, running weekly synthesis, recalling past context, or managing plans.
 Also trigger on: "remember this", "take a note", "note this", "note that down".
---

# Second Brain

Persistent, file-based memory organized by Tiago Forte's PARA method. Three layers: a knowledge graph, daily notes, and tacit knowledge. All paths are relative to `$OBSIDIAN_VAULT`. PARA folders live directly under `$OBSIDIAN_VAULT`.

**Precondition:** If `$OBSIDIAN_VAULT` is unset or empty, stop and ask the user for the vault path before doing anything. Never write to relative paths (e.g. `0 Inbox/`, `MEMORY.md`) — an unset var resolves them against the filesystem root.

**Glossary:** A *heartbeat* is a periodic lull in the conversation (e.g. when the user steps away or a task wraps up) used to flush pending memory work — extracting durable facts from daily notes into the knowledge graph and updating access metadata.

## Three Memory Layers

### Layer 1: Knowledge Graph (`$OBSIDIAN_VAULT/` -- PARA)

Entity-based storage. Each entity gets a folder with two tiers:

1. `summary.md` -- quick context, load first.
2. `items.yaml` -- atomic facts, load on demand.

```text
$OBSIDIAN_VAULT/
 0 Inbox/           # Unsorted captures, process into other folders
 1 Projects/        # Active work with clear goals/deadlines
   <name>/
     summary.md
     items.yaml
 2 Areas/           # Ongoing responsibilities, no end date
   people/<name>/
   companies/<name>/
 3 Resources/       # Reference material, topics of interest
   <topic>/
 4 Archives/        # Inactive items from the other three
 Daily Notes/       # Per-day timeline files (YYYY-MM-DD.md)
 Templates/         # Reusable templates for entities and notes
 index.md           # Top-level map of the vault: links to active projects,
                    # key entities, and where things live. Rewrite during weekly synthesis.
```

**PARA rules:**

- **0 Inbox** -- unsorted captures. Process into Projects, Areas, or Resources promptly.
- **1 Projects** -- active work with a goal or deadline. Move to `4 Archives` when complete.
- **2 Areas** -- ongoing (people, companies, responsibilities). No end date.
- **3 Resources** -- reference material, topics of interest.
- **4 Archives** -- inactive items from any category.

**Fact rules:**

- Save durable facts immediately to `items.yaml`.
- Weekly: rewrite `summary.md` from active facts.
- Never delete facts. Supersede instead (`status: superseded`, add `superseded_by`).
- **Superseding vs. decay are different:** supersede when a fact becomes *wrong* (correctness); decay only lowers a still-true fact's retrieval priority as it ages (see [references/schemas.md](references/schemas.md)). Never use one for the other.
- When an entity goes inactive, move its folder to `$OBSIDIAN_VAULT/4 Archives/`.

**When to create an entity:**

- Mentioned 3+ times, OR
- Direct relationship to the user (family, coworker, partner, client), OR
- Significant project or company in the user's life.
- Otherwise, note it in daily notes.

For the atomic fact YAML schema and memory decay rules, see [references/schemas.md](references/schemas.md).

### Layer 2: Daily Notes (`$OBSIDIAN_VAULT/Daily Notes/YYYY-MM-DD.md`)

Raw timeline of events -- the "when" layer.

- Write continuously during conversations.
- Extract durable facts to Layer 1 during heartbeats.

### Layer 3: Tacit Knowledge (`$OBSIDIAN_VAULT/Tacit Knowledge.md`)

How the user operates -- patterns, preferences, lessons learned.

- Not facts about the world; facts about the user.
- Update whenever you learn new operating patterns.
- **Distinct from Claude Code's own `MEMORY.md` auto-memory** (under `~/.claude/...`), which has a different frontmatter/index format. This layer lives inside the vault and is plain prose. Do not conflate the two.

## Worked Example

User says: *"Had a 1:1 with my manager Jeff at Acme today — he wants me to lead the billing migration, due end of Q3."*

1. **Capture to the daily note** (`Daily Notes/2026-06-09.md`): append a timeline entry — `- 1:1 with Jeff (manager). Asked me to lead the billing migration, due end of Q3.`
2. **Decide on entities.** Jeff (direct relationship → manager) and Acme (significant company) both qualify. The billing migration is a project with a goal + deadline.
3. **Create/update entities:**
  - `2 Areas/people/jeff/items.yaml` → fact: `"Jeff is the user's manager at Acme"` (category: `relationship`).
  - `1 Projects/billing-migration/items.yaml` → facts: `"User leads the billing migration"` (category: `status`), `"Billing migration is due end of Q3 2026"` (category: `milestone`). Add `related_entities: [people/jeff, companies/acme]`.
  - Write a short `summary.md` for the project if it doesn't exist.
4. **At the next heartbeat**, confirm the facts landed in `items.yaml` and bump access metadata on any entity referenced this session.

When the migration ships, move `1 Projects/billing-migration/` to `4 Archives/`.

## Write It Down -- No Mental Notes

Memory does not survive session restarts. Files do.

- Want to remember something -> WRITE IT TO A FILE.
- "Remember this" / "take a note" / "note this" / "note that down" -> update `$OBSIDIAN_VAULT/Daily Notes/YYYY-MM-DD.md` or the relevant entity file.
- Learn a lesson -> update AGENTS.md, TOOLS.md, or the relevant skill file.
- Make a mistake -> document it so future-you does not repeat it.
- On-disk text files are always better than holding it in temporary context.

## Memory Recall -- Use qmd

Use `qmd` rather than grepping files:

```bash
qmd query "what happened at Christmas"   # Semantic search with reranking
qmd search "specific phrase"              # BM25 keyword search
qmd vsearch "conceptual question"         # Pure vector similarity
```

Index your personal folder: `qmd index $OBSIDIAN_VAULT`

Vectors + BM25 + reranking finds things even when the wording differs.

## Planning

Keep plans in timestamped files in `plans/` at the project root (outside personal memory so other agents can access them). Plans go stale -- if a newer plan exists, do not confuse yourself with an older version. If you notice staleness, update the file to note what it is supersededBy.

