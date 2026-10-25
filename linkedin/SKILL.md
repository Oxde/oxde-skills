---
name: linkedin-growth-os
description: Use when researching, drafting, publishing, monitoring, or improving LinkedIn content. Build source-backed posts in the user's real voice; keep drafts durable; require approval for every external action.
---

# LinkedIn Growth OS

## Operating sequence

1. Read the voice profile and active draft index.
2. Classify the work: source/news, product launch, guide, field note, comment/reply, or performance review.
3. Research the primary source before drafting where a source exists.
4. Extract evidence: actor, event, concrete facts, quote/number, weirdest detail, tension, material caveat.
5. Select one angle. Do not turn one source into three vague takes.
6. Run a separate hook pass. Line 1 must make the subject clear and create a reason to read.
7. Draft in the user's voice. Preserve a good rough draft's rhythm instead of polishing it into analyst prose.
8. Run fact, anti-slop, and visual-fit passes.
9. Persist the result to a real Markdown draft file.
10. Ask for exact approval before any external action.
11. After publishing, measure performance and add one evidence-backed lesson.

## Non-negotiables

- Research is not a hook library. Hooks are priors; sources and account data are evidence.
- Do not fabricate outcomes, numbers, quotes, customers, or anecdotes.
- Do not make a long draft longer when feedback says it is not meaty. Rebuild around the strongest fact, table, mechanism, incident, or artifact.
- Do not repeat an unchanged draft in scheduled reminders.
- Do not publish, comment, DM, like, follow, or connect without exact approval.

## Draft statuses

`researching` → `drafting` → `needs-visual` → `waiting-for-user` → `approved` → `posted`

Use `parked` for good ideas that should not currently receive reminders, and `rejected` for ideas that should not return unless explicitly reopened.

## Research modes

### News/source-led

Use an official announcement, paper, changelog, primary X post, or reliable reporting. Lead with the strange verified detail and preserve the source's tension.

### Product launch

Inspect the product/repo/docs/demo. Lead with the real workflow pain. Show only the details that prove the tool works.

### Guide

Build the table, checklist, decision rule, or other saveable artifact first. Then write the body around it.

### Engagement

Scan read-only. Select a few posts where the user can add a real datum, disagreement, field receipt, correction, reframe, or hard question. Never default to generic praise.

## Research menu picks

When the topic comes from a research menu that the `feed-menu` job posted in this chat (numbered
items with lanes NEWS / SKILLS / REPOS), record the pick **before** researching, so the feed
never offers it again and the stats stay true:

```
bash ~/.hermes/profiles/writer/scripts/feed-ctl.sh pick <id> --note "<the user's words>"
```

The `id` is on the menu line (`id: <hex>`). If the ids are not in context, run
`bash ~/.hermes/profiles/writer/scripts/feed-ctl.sh list` (ids of offered, shown and picked
items) and match the title; never run `feed-ctl.sh menu` for this, it offers new items.
After the post is live, run `... set-status <id> posted`; on a skip, `... set-status <id> skipped`.
