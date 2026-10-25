---
title: LinkedIn Intelligence and Content System
source_type: note
captured: 2026-10-25
tags: [linkedin, growth, intelligence, news, skills]
connections:
  - "[[LinkedIn Growth OS]]"
  - "[[Research-led Long Article Pipeline]]"
status: active
---

# LinkedIn Intelligence and Content System

## Goal

Create one useful daily candidate for Mark’s AI engineer/operator audience, while continuously learning from:

1. high-signal AI news
2. high-performing posts in the niche
3. useful agent skills/repos/workflows
4. Mark’s own post performance and comments

This is not an auto-posting system. Every publish, comment, reaction, connection, or DM remains approval-gated.

## What Pierre Herubel’s model gets right

Pierre’s 95/5 model has three distinct layers:

1. **Content for the learning majority** — useful, zero-click material at different levels of depth.
2. **Distribution motions** — founder-led content first, then brand/team/community layers when appropriate.
3. **Signals** — detect who engaged and what they care about, then use the signal deliberately.

For Mark, the equivalent is not B2B agency outbound. It is an operator-content loop:

- publish useful AI/operator material
- detect the news, skills, and post patterns worth learning from
- use performance/comments to improve the next artifact
- engage only where Mark has a real operator observation to add

## Four independent queues

### Queue A — AI News Desk

**Purpose:** Turn high-signal AI news into one strong daily post candidate.

**Inputs:**

- Data Secrets as a lead source
- official model/company announcement pages
- research papers and benchmarks
- selected X accounts / launch posts
- large compute, safety, security, labor, or infrastructure news

**Output:** one candidate only:

| Field | Requirement |
|---|---|
| Event | named actor + exact change |
| Proof | 3 verified facts and primary URLs |
| Tension | why a builder/operator should care |
| Mark angle | real judgment, not a generic summary |
| Format | text / visual / carousel / long article |
| Decision | draft / deeper / skip |

**Rule:** Data Secrets supplies energy and leads. The original company/paper source supplies facts.

### Queue B — Niche Feed Intelligence

**Purpose:** Find high-performing posts in Mark’s lane and learn the mechanism, not copy the text.

**Niche definition:**

- AI agents and agent work
- Claude Code / Codex / coding agents
- model launches and model economics
- agent skills and workflows
- AI infrastructure, compute, security, and labor impact

**Output:** maximum 3 posts per scan:

| Field | Requirement |
|---|---|
| URL / author | canonical public post URL and author |
| Hook | exact first lines |
| Visible performance | reactions, comments, reposts, or views when source exposes them |
| Why it worked | tension, proof, format, timing, audience fear/status/control stake |
| Mark angle | a different, operator-grounded interpretation |
| Comment opportunity | only if Mark can add a genuine datum, disagreement, or field receipt |

**Never:** auto-comment, copy hooks line-for-line, or make claims about algorithm performance without observed data.

### Queue C — Skills and Workflow Review Desk

**Purpose:** Find useful new agent skills, repos, tools, and workflows, then test what is worth talking about.

**Inputs:**

- ClawHub / skills.sh
- Hermes skill ecosystem
- GitHub releases and agent repos
- Claude Code, Codex, and Hermes workflow tools

**Output:** maximum 3 items weekly:

| Item | What it actually does | Evidence/test status | Who it helps | Why it may be content | Next action |
|---|---|---|---|---|---|

After Mark picks one: inspect → test safely → identify what works/breaks → create a field-note post only when there is a real artifact.

### Queue D — Own-Post Performance and Community

**Purpose:** Make every published post improve the next one.

**After post:**

- +30 min: check meaningful early comments
- +2h: first traction signal
- +24h: compare reach, reactions, comments, reposts, and visual/hook fit

**Output:**

- metrics only when real read data is available
- up to 3 approval-gated reply drafts
- one concrete lesson written into the relevant hook/format reference

No recent post or no authenticated read adapter = `[SILENT]`.

## Required data architecture

### Publishing

Use official OAuth / Maton. This is already wired.

### Public LinkedIn feed intelligence

Use a paid structured provider. Recommended trial order:

1. **AgntData** — likely best first pilot for search-posts, profile posts, comments/reactions, and pay-per-request testing.
2. **ScrapeCreators** — good public post search and known-post enrichment, but discovery is Google-indexed rather than a complete feed.
3. **Bright Data / Apify** — bulk or custom collection when the first two cannot provide a needed field.

Test before committing: run the same 20-query niche scan through the selected provider and judge coverage, freshness, post URLs, engagement fields, comment availability, cost, and stability.

### Personal LinkedIn analytics

Use either:

- opt-in persistent browser bridge for Mark’s own account, or
- a provider that can reliably expose owner-visible post metrics.

Do not promise private-feed or owner-only analytics from a public-data API until a real response proves it.

## Schedule after paid data adapter is connected

| Schedule | Job | Output |
|---|---|---|
| 08:30 daily | source collector | deterministic source snapshot; no LLM |
| 09:00 daily | AI news desk | one daily candidate |
| 11:30 Mon/Wed/Fri | niche feed intelligence | up to three analyzed niche posts |
| 15:00 Tue/Thu | skills/workflow review desk | up to three testable skills/repos |
| after each post: +30m, +2h, +24h | post performance/community | metrics, replies, one lesson |

The jobs must write durable queue files. Chat delivery is a summary, never the only state.

## Definition of working

The system is working only when, in one week, it produces:

- five verified daily news candidates
- at least six analyzed niche posts with URLs/metrics/lessons
- two reviewed skills/workflows with actual test notes
- one published post with a 24-hour performance review
- zero autonomous social actions

## Current blockers

- No paid LinkedIn public-data provider/API key connected.
- Browser read path is not logged in.
- Existing daily news and performance crons are restored, but they are not yet backed by a durable feed-intelligence adapter.
