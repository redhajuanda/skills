# Frontmatter Schema

Every note in the vault carries a YAML frontmatter header. This is what makes recall cheap — an agent filters by `type`/`tags` without opening the file (see the Memory Recall section in SKILL.md).

```yaml
---
type: reference        # REQUIRED. From the fixed vocabulary below.
title: "Short title"   # human-readable name
timestamp: 2026-07-01  # date authored (get with `date +%F`, never assume)
resource:              # optional — url or repo path if the note points at a real asset
tags: [topic, project] # optional — cross-cutting categorization
---
```

## `type` vocabulary (fixed — reuse, never invent per-note)

| type        | use for                                            |
|-------------|----------------------------------------------------|
| `prd`       | product requirement docs                           |
| `plan`      | implementation / work plans                        |
| `project`   | a project entity note (1 Projects)                 |
| `area`      | an ongoing entity: person, company (2 Areas)       |
| `reference` | reference material, how-tos, repo summaries        |
| `daily-log` | daily timeline notes                               |
| `tacit`     | user operating patterns / preferences              |
| `note`      | catch-all when nothing else fits                   |

A single fixed vocabulary is the whole point: two notes with the same `type` are guaranteed comparable. If a real need appears that none of these cover, add it here first, then use it — don't coin one-off types inline.

## Links are edges

Relationships are plain `[[wikilinks]]` in the body or frontmatter (e.g. `project: "[[Capio - Garuda Food]]"`), not a separate schema. A plan links up to its project; an entity links to related entities. Broken links are allowed (OKF permits them) — a link to a note that doesn't exist yet just marks intent.

## No deletion

Correct wrong facts in place (note what changed) or move inactive entities to `4 Archives/`. The full history lives in git and the daily notes — never destroy the record.
