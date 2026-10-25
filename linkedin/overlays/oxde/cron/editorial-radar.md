# LinkedIn Editorial Radar — sources to candidates

**Purpose:** Produce at most one evidence-backed LinkedIn candidate per run. It is the editorial job for news, primary-source leads, and niche signals. It is not the Skill Radar job and it never publishes.

## Canonical schedule

```cron
0 10,16 * * *
```

Two slots are a ceiling, not a quota. The 16:00 candidate must be independently strong and distinct from the morning candidate. Skip a slot rather than manufacture a second post.

## Runtime model

The scheduler runs an agent with a source script. The agent does **not** receive a stale prebuilt feed.

```text
cron fires
  → daily_linkedin_topic_sources.py fetches current Telegram/RSS leads
  → its compact output is injected into the editorial-agent run
  → agent verifies a primary source and, where available, checks LinkedIn niche signals
  → agent returns one candidate or [SILENT]
```

## Source-script contract

Script: `linkedin/overlays/oxde/scripts/daily_linkedin_topic_sources.py`

Input lanes:

- Telegram: `@data_secrets`, `@ai_machinelearning_big_data`, `@human20`, `@NeuralShit`
- RSS: TechCrunch AI, The Verge AI, VentureBeat AI, Artificial Intelligence News, MIT News AI

Telegram/RSS are discovery leads only. A lead must never become a factual post claim without an original source, primary announcement, paper, repository, or direct artifact.

## Editorial-agent contract

1. Take current source-script output as leads.
2. Verify the original source before making a factual claim.
3. When the authenticated browser is available, inspect 3–5 relevant public LinkedIn cards as a compact niche-signal pass:
   - identify saturated topics/hook shapes;
   - notice visible, defensible tension or format signals;
   - never copy text or manufacture engagement data from blank counters.
4. Rank across these content lanes, not news alone:
   - **News** — model/company announcements, papers, launches, incidents.
   - **Tools + skills** — only when a repo/MCP/skill has been inspected or safely tested.
   - **Operator signals** — workflow failure, security friction, niche observation, or a real field receipt.
5. Apply the anti-slop / Mark-specific gate:

```text
Why Mark?
Why now?
What could a generic AI creator not honestly write here?
```

6. Return exactly one candidate or `[SILENT]`. Never draft, publish, comment, react, connect, or DM without the separate approval flow.

## Required output

```text
1. Topic — named actor + event
2. Proof — 3 short verified facts, with source URLs
3. Niche signal — one concise observed hook/format/tension signal, or `unavailable`
4. Mark's angle — one blunt judgment a generic creator could not write
5. Hook — one concrete first line
6. Best format — text / image / carousel / long article
7. Next action — draft / skip / deeper
```

## Operational boundary

The local Hermes registration has an environment-specific job ID, tool permissions, and delivery destination. Do not commit those values as portable configuration. The Git version above is canonical behavior; each host recreates its own scheduler registration from it.
