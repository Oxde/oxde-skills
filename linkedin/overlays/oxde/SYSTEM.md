---
title: LinkedIn Growth OS
source_type: note
captured: 2026-10-06
tags: [linkedin, system, research, publishing]
connections:
  - "[[LinkedIn content workspace]]"
  - "[[LinkedIn voice profile]]"
status: active
---

# LinkedIn Growth OS

## Goal

Produce source-backed, boss-voice LinkedIn posts; distribute them safely; measure what works; and turn the lessons into the next post.

## Four loops

### 1. Research

Use the right source for the question:

- **Source/news research:** official announcement, paper, changelog, X primary post, web reporting. Required for current news and model/product claims.
- **Build/product research:** repository, docs, demo, screenshots, firsthand test. Required for launch posts.
- **LinkedIn research:** recent posts, visible engagement, comment patterns, high-performing accounts in the AI/operator lane. Read-only by default.
- **Account research:** boss's own post analytics, comments, and archive.

Do not call generic hook formulas "research." A hook library is a prior. Sources and account data are evidence.

### 2. Editorial

1. Store each promising item as a real draft in `drafts/`.
2. Set its status and owner next action.
3. Extract an evidence ledger: source, 3-6 load-bearing facts, weirdest fact, tension, source-supported conclusion.
4. Run a **niche signal pass** before choosing the angle: when the authenticated LinkedIn browser is available, inspect a small live sample of relevant public feed/search posts. Use it to test whether the topic, hook shape, format, and tension are already saturated or visibly resonating. Record the signal; never copy post text, pretend unavailable counters are data, or turn a generic creator's structure into Mark's voice.
5. Choose one angle that has a Mark-specific operator claim.
6. Run a separate hook pass.
7. Draft in `VOICE.md` style.
8. Run fact pass, anti-slop pass, and visual fit pass.

### Two-post quality bar

Two daily posts are a ceiling, never a quota. Each candidate must independently clear all of these before it can be presented as publishable:

1. **Primary evidence:** an official source, paper, product artifact, repo/test, or direct field receipt — not a recycled news summary.
2. **A Mark-only claim:** a concrete operator observation, mechanism, disagreement, or result that a generic AI-content account could not honestly write.
3. **Specific load:** at least one named actor plus a number, mechanism, artifact, or compact comparison that carries the post.
4. **Distinctness:** the second post cannot be a paraphrase of the first topic, hook shape, visual, or conclusion.
5. **Reader value:** the reader can learn a decision rule, a failure mode, or a mechanism worth saving — not just hear an announcement.
6. **Human review:** separate hook pass, anti-slop pass, and a rendered visual QA when a visual is used.

If either post fails this gate, skip it. Do not force a second AI news summary because a slot exists.

### Research-led long articles

For comparisons, guides, market maps, or benchmark explainers, short feed copy cannot be the first deliverable. Follow `ARTICLE_PIPELINE.md` in this exact order:

1. scope contract
2. sourced fact matrix
3. separate benchmark matrix
4. personal-use receipts, if writing in first person
5. long-form article with tables and source/check date
6. fact, voice, reader-value, and claims passes
7. only then derive the feed post, carousel, or X adaptation

A long article is allowed to exceed normal LinkedIn post length. The short-post quality checker’s length warning is expected for this artifact.

### 3. Distribution

- Every post needs a visual decision: source image, product screenshot, HTML card, carousel, or no visual only with boss's explicit exception.
- Draft replies/comments can be generated, but no post/comment/DM/like/connect action without exact boss approval.
- Publishing requires explicit `post now`, exact-text SHA256, Maton publish, live verification, and archive.

### 4. Learning

- At +30m, +2h, and +24h: inspect impressions, reactions, comments, reposts, and saves when visible.
- Diagnose using hook, topic, format, visual, early comments, and audience stake. Do not over-index on posting time.
- Record one concrete lesson in the relevant writing reference or draft metadata.

## Capability matrix

| Capability | Current path | Current state |
|---|---|---|
| Official/news research | web_extract, web_search, X fetcher | working |
| Product/repo research | GitHub + docs + firsthand test | working |
| Draft persistence | MyBrain Markdown drafts | working |
| Publishing | Maton + SHA256 guard | working |
| Visual cards | HTML/card pipeline + QA | working |
| Own-post metrics | Authenticated OpenCLI browser bridge + custom visible-DOM collector | working: activity URN, impressions, and visible reactions collected every 30 minutes locally; dashboard ingestion/comparison pending |
| LinkedIn feed / competitor scan | Authenticated OpenCLI timeline/search + custom visible-DOM collector; paid structured API later | browser connection working; public feed and profile search proven; ranking/URL/counter normalization pending |
| Comment / reply action | exact draft + boss approval; browser interaction only after approval | no automated engagement; read collector and comment queue pending |

## LinkedIn observation rules

- Read-only by default.
- Never automate likes, comments, DMs, connections, or follows.
- Use OpenCLI/browser slowly and only for boss's own account or a small, deliberate list of relevant public posts.
- Stop on CAPTCHA/security challenge.
- Prefer paid structured data API only if browser reading is too brittle and the use case is worth it.

## Draft status vocabulary

- `researching` — source is not yet verified.
- `drafting` — angle/hook/body in progress.
- `needs-visual` — copy ready enough; visual artifact missing.
- `waiting-for-boss` — needs a decision/correction; cron should not repeat the entire draft.
- `approved` — exact copy/visual approved; waiting for `post now`.
- `posted` — live URL and archive verified.
- `parked` — potentially good, but not current priority.
- `rejected` — do not revive unless boss asks.

## Quality gates

- A news post cannot rely only on screenshot/text summary when a primary source can be opened.
- A guide cannot be all prose if a table/checklist would make it saveable.
- A build launch cannot read like documentation; lead with the actual pain.
- A draft marked "long and not meaty" must be rebuilt around a stronger fact/artifact, not cosmetically edited.
- No post is final without anti-slop pass and visual decision.
