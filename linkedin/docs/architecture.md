# Architecture

## The four loops

### Research

Use primary sources first: product docs, repositories, papers, changelogs, official announcements, or direct X posts. LinkedIn observation is a separate adapter, not a replacement for source research.

### Editorial

Turn evidence into one angle, one strong hook, a draft in the user's voice, and a visual decision. A hook formula can help, but it cannot substitute for a concrete fact, pain, cost, contradiction, or incident.

### Distribution

Posts, comments, DMs, likes, follows, and connections are always exact-approval actions. The system can prepare payloads and verify a publish, but cannot decide to act socially by itself.

### Learning

Use the account's own results when available. Compare top/bottom posts by engagement rate, comment ratio, reach multiple, saves/sends, hook, topic, visual, and opinion timing. Do not blame posting time before looking at the post itself.

## Folder model

```text
VOICE.md                 reusable voice source
ACTIVE.md                current priority list
drafts/                  one Markdown file per post
queues/COMMENT_QUEUE.md  candidate comments and approvals
archive/                 exact published payloads + metadata
```

## Scheduled-agent rule

Scheduled jobs run without the live conversation. They must read `ACTIVE.md` and the active draft before scanning new news. If nothing changed and a draft is waiting on the user, send a short pointer or remain silent, never a duplicate full draft.
