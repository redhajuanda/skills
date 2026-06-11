# /lean-fable

A token-frugal orchestration protocol designed specifically for Claude.

`/lean-fable` solves the problem of "context bloat" in agentic workflows by structuring prompts for **Prompt Caching**, restricting verification to **Line-Bounded file views**, and enforcing **compact subagent payloads**.

---

## Why `/lean-fable`?

While `/efficient-fable` splits tasks between orchestrators and subagents, it still suffers from:
* **Cache Misses:** Dynamic fields placed early in prompts invalidating Claude's 1024-token cache prefix.
* **Token Bloat:** Fable reading full files to verify minor subagent claims.
* **Narrative Overhead:** Subagents returning paragraphs of explanation instead of structured, high-signal data.

`/lean-fable` fixes these inefficiencies, reducing token costs by **up to 70%** and preventing context exhaustion in long debugging/coding sessions.

---

## Core Guidelines

1. **Deterministic Prompts**: Order prompts strictly (System instructions $\rightarrow$ Static tools $\rightarrow$ Stable context $\rightarrow$ Dynamic data) to maximize prompt caching hits.
2. **Line-Bounded Reading**: Never view full files for validation. Retrieve only the exact lines cited by subagents using `StartLine` and `EndLine`.
3. **Structured Handoffs & Compaction**: Mandate JSON, diffs, or bulleted lines as subagent return formats. Enforce early-termination on search tools.
4. **Active Thread Resets**: Save state to `task.md` and reset chat context when conversations grow too long, clearing historical message tokens.

---

## Installation

Install the skill to your project using the Skills CLI:

```bash
npx skills add redhajuanda/skills --skill lean-fable
```
