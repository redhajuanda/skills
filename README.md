# Agent Skills

Agent Skills — markdown instructions that extend the agent with specialized workflows.

## Skills

| Skill | What it's for |
|-------|---------------|
| **second-brain** | File-based memory using PARA (Projects, Areas, Resources, Archives). Stores facts, daily notes, and user patterns in an Obsidian vault across sessions. Triggers on "remember this", note-taking, recall, and weekly synthesis. Requires `$OBSIDIAN_VAULT` to be set. |

## Install

Uses the [Skills CLI](https://github.com/vercel-labs/skills) — no global install needed.

```bash
# List available skills in this repo
npx skills add redhajuanda/skills --list

# Install all skills (project scope)
npx skills add redhajuanda/skills

# Install one skill
npx skills add redhajuanda/skills --skill second-brain
```
