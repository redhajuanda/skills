---
name: second-brain
description: >
 File-based memory system using Tiago Forte's PARA method. Use this skill whenever
 you need to store, retrieve, update, or organize knowledge across sessions. Covers
 three memory layers: (1) Knowledge graph of labeled markdown notes in PARA folders,
 (2) Daily notes as raw timeline, (3) Tacit knowledge about user patterns. Notes
 carry OKF-style frontmatter (a `type` label) so recall is filter-then-read via the
 Obsidian CLI or ripgrep. Also handles planning files and weekly synthesis.
 Trigger on any memory operation: saving facts, writing daily notes, creating
 entities, running weekly synthesis, recalling past context, or managing plans.
 Also trigger on: "remember this", "take a note", "note this", "note that down".
---

# Second Brain

Persistent, file-based memory organized by Tiago Forte's PARA method. Three layers: a knowledge graph, daily notes, and tacit knowledge. All paths are relative to `$OBSIDIAN_VAULT_PATH`. PARA folders live directly under `$OBSIDIAN_VAULT_PATH`.

**Precondition:** If `$OBSIDIAN_VAULT_PATH` is unset or empty, stop and ask the user for the vault path before doing anything. Never write to relative paths (e.g. `0 Inbox/`, `MEMORY.md`) — an unset var resolves them against the filesystem root.

**Glossary:** A *heartbeat* is a checkpoint for flushing pending memory work — extracting durable facts from daily notes into the knowledge graph and updating access metadata. Run one at these concrete moments: when a task wraps up, before ending a turn or session, when the user says goodbye, or at session start if work is pending from last time.

**Dates:** Daily notes and fact timestamps are keyed by date. Always get today's date with `date +%F` — never assume it.

## Three Memory Layers

### Layer 1: Knowledge Graph (`$OBSIDIAN_VAULT_PATH/` -- PARA)

Entity-based storage. Each entity is a **labeled markdown note** (or a folder of them for bigger entities). Knowledge lives in the prose + frontmatter; links between notes are the graph edges. This is the OKF pattern: plain markdown, a `type` label, `[[wikilinks]]`.

```text
$OBSIDIAN_VAULT_PATH/
 0 Inbox/           # Unsorted captures, process into other folders
 1 Projects/        # Active work with clear goals/deadlines
   <name>/
     summary.md     # the entity note (or just <name>.md)
 2 Areas/           # Ongoing responsibilities, no end date
   people/<name>/
   companies/<name>/
 3 Resources/       # Reference material, topics of interest
   <topic>/
 4 Archives/        # Inactive items from the other three
 Daily Notes/       # Per-day timeline files (YYYY-MM-DD.md)
 Templates/         # Reusable templates. Check for a matching one before
                    # creating a new note (e.g. Templates/okf-note.md).
 index.md           # Top-level map: links to active projects and key entities.
                    # Rewrite during weekly synthesis.
```

**PARA rules:**

- **0 Inbox** -- unsorted captures. Process into Projects, Areas, or Resources promptly.
- **1 Projects** -- active work with a goal or deadline. Move to `4 Archives` when complete.
- **2 Areas** -- ongoing (people, companies, responsibilities). No end date.
- **3 Resources** -- reference material, topics of interest.
- **4 Archives** -- inactive items from any category.

#### Frontmatter (every note has a header)

Give every note a header so it's filterable without opening it — this is what makes [recall](#memory-recall----filter-by-label-then-read) cheap.

```yaml
---
type: reference        # required — from the fixed vocab below
title: "Short title"
timestamp: 2026-07-01  # date authored (get it with `date +%F`, never assume)
resource:              # optional — url/repo if the note points at a real asset
tags: [topic, project]
---
```

- **`type` vocabulary (fixed — reuse, don't invent):** `prd, plan, reference, area, project, daily-log, tacit, note`.
- Link related notes with `[[wikilinks]]` — that's the graph. A plan links to its project; a summary links to its area.

**Knowledge rules:**

- Save durable knowledge to its entity note immediately; capture raw events to the daily note.
- Never delete a fact that turns out wrong -- correct it in place and note what changed, or mark it superseded. Losing the record is worse than a stale line.
- When an entity goes inactive, move its folder to `$OBSIDIAN_VAULT_PATH/4 Archives/`.

**When to create an entity:**

- Mentioned 3+ times, OR
- Direct relationship to the user (family, coworker, partner, client), OR
- Significant project or company in the user's life.
- Otherwise, note it in daily notes.

For the frontmatter schema, see [references/schemas.md](references/schemas.md).

### Layer 2: Daily Notes (`$OBSIDIAN_VAULT_PATH/Daily Notes/YYYY-MM-DD.md`)

Raw timeline of events -- the "when" layer.

- Write continuously during conversations.
- Extract durable facts to Layer 1 during heartbeats.

### Layer 3: Tacit Knowledge (`$OBSIDIAN_VAULT_PATH/Tacit Knowledge.md`)

How the user operates -- patterns, preferences, lessons learned.

- Not facts about the world; facts about the user.
- Update whenever you learn new operating patterns.
- Distinct from any agent-level memory files the harness maintains outside the vault (e.g. Claude Code's auto-memory). This layer lives inside the vault and is plain prose. Do not conflate the two.

## Worked Example

User says: *"Had a 1:1 with my manager Jeff at Acme today — he wants me to lead the billing migration, due end of Q3."*

1. **Capture to the daily note** (`Daily Notes/2026-06-09.md`): append a timeline entry — `- 1:1 with Jeff (manager). Asked me to lead the billing migration, due end of Q3.`
2. **Decide on entities.** Jeff (direct relationship → manager) and Acme (significant company) both qualify. The billing migration is a project with a goal + deadline.
3. **Create/update entities** (each a labeled markdown note with frontmatter):
  - `2 Areas/people/jeff/summary.md` (`type: area`) → "Jeff is the user's manager at Acme." Link `[[Acme]]`.
  - `1 Projects/billing-migration/summary.md` (`type: project`) → "User leads the billing migration, due end of Q3 2026." Link `[[Jeff]]`, `[[Acme]]`.
4. **At the next heartbeat**, confirm the notes were written and the links resolve.

When the migration ships, move `1 Projects/billing-migration/` to `4 Archives/`.

## Write It Down -- No Mental Notes

Memory does not survive session restarts. Files do.

- Want to remember something -> WRITE IT TO A FILE.
- "Remember this" / "take a note" / "note this" / "note that down" -> update `$OBSIDIAN_VAULT_PATH/Daily Notes/YYYY-MM-DD.md` or the relevant entity file.
- Learn a lesson about how the user operates -> update `$OBSIDIAN_VAULT_PATH/Tacit Knowledge.md`.
- Make a mistake -> document it in the daily note so future-you does not repeat it.
- On-disk text files are always better than holding it in temporary context.

## Memory Recall -- filter by label, then read

Every note carries a `type` label (see [Frontmatter](#frontmatter-every-note-has-a-header)), so recall is: **narrow to filenames by property, then read only the hits.**

**Preferred: Obsidian CLI** (the `obsidian` command; requires the Obsidian app to be running).

```bash
obsidian search query='["type":plan]' format=text     # by property — NOTE the bracket form
obsidian search query='billing migration' format=text  # word-based content search
obsidian backlinks file="Acme" format=tsv              # what links to an entity
obsidian tags                                           # list all tags
```

- The property filter **must** use the bracket form `["type":plan]`. Plain `type:plan` errors.
- `format=text` returns bare file paths — cheap to scan; open only the matches.
- If `obsidian` is not installed (`command -v obsidian` fails), **ask the user whether to install it**. Until then, use the fallback.

**Fallback: ripgrep** (works with the app closed / in scripts):

```bash
rg -l '^type: plan' "$OBSIDIAN_VAULT_PATH"              # by label
rg -l '\[\[Acme\]\]' "$OBSIDIAN_VAULT_PATH"             # backlinks (text match)
rg -n 'ACL|permission' "$OBSIDIAN_VAULT_PATH"           # content with line numbers
```

`$OBSIDIAN_VAULT_PATH` has spaces — always quote it, and never `$(rg -l ...)` unquoted (it word-splits on the path). Use `rg -l --null ... | while IFS= read -r -d '' f; do ...; done`.

## Weekly Synthesis

Run roughly once a week (or when the user asks):

1. Process anything left in `0 Inbox/` into Projects, Areas, or Resources.
2. For each active entity, trim its `summary.md` to what's still relevant — drop stale detail (it stays in the daily notes / git history if ever needed).
3. Move completed projects and inactive entities to `4 Archives/`.
4. Rewrite `index.md` so it reflects current active projects and key entities.

## Planning

Keep plans in timestamped files in `plans/` at the root of the code repository you are working in -- not in the vault -- so other agents working on the same project can access them. Plans go stale: if a newer plan exists, do not confuse yourself with an older version. If you notice staleness, add a note to the old file naming the plan that supersedes it.

