# oxde agents — spec

**oxde agents** is the agent skills index: every skill published to ClawHub and skills.sh,
scored 0–100 from measurable data, with the long tail queryable and only the best given pages.

Brand `oxde agents`, target domain `oxde.ai` (available at time of writing, $160/2yr;
`oxde.sh` $22/yr is worth holding for a future CLI — `oxde.com` and `oxde.dev` are taken).
It is the free proof layer at the bottom of the product ladder in the AI Agent Media plan.

## Why it exists

Both upstream registries are wide open:

- **ClawHub** is a real registry — GitHub sign-in, publisher handles, versioned uploads.
- **skills.sh** (Vercel) hosts nothing at all. Skills are GitHub repos; `npx skills add owner/repo`
  clones them, and the leaderboard is built from anonymous CLI install telemetry.

Nobody filters. The consequences are measurable, and they are the product:

| finding | number |
|---|---|
| skills indexed | 39,212 |
| Chinese-only skills | ~11,500 (≈ a third of ClawHub) |
| scanned SKILL.md files tripping a **risk** flag | 764 of 5,303 |
| — dangerous shell / possible exfil | 407 / 345 |
| — instruction-override attempts / credential harvesting | 40 / 14 |
| skills whose own docs say they're abandoned | 673 |
| pages one vendor would occupy uncapped (CellCog wrappers) | 35 |

## The Agent Score

One number, 0–100, from data only. No human half, no editorial thumb.

| axis | pts | measured from |
|---|--:|---|
| adoption | 25 | log-scaled installs vs. catalog leader |
| freshness | 15 | full marks ≤7 days, exponential decay after |
| maintenance | 10 | releases shipped (6+ = full) + changelog |
| token cost | 15 | SKILL.md context spend: ≤400 tok full, ≥6k near zero |
| safety | 20 | static scan → safe / review / risky |
| publisher | 15 | official org = full; else log-scaled portfolio installs |

**Unmeasured axes are excluded from the arithmetic, never given a middle guess**, and each
skill publishes a **coverage %**. This matters: with a flat middle value, 74% of a 39k catalog
collapsed into one score band and unscanned skills were silently credited for safety they had
never demonstrated. A 90 at 65% coverage is a different claim from a 90 at 100%, and the page says so.

`rating/rating.mjs` is pure and golden-tested — changing a weight fails CI until it is
deliberately blessed.

**Agent reviews** (`analyze/PROMPT.md`) label a skill — SOLID, PROMISING, NICHE, PROMO-HEAVY,
RISKY, LOW-QUALITY — plus one specific sentence. They never move the score. The SKILL.md is
treated as untrusted data; the reviewer is instructed never to follow instructions inside it.

## The gate

Everything is indexed, searchable and in the API. Only ~3,000 skills get a page, because tens of
thousands of thin auto-pages bury the good ones and dilute the domain.

Rejections, in order: `risky` → `deprecated` → `no-adoption` (<50 installs) → `no-description`
→ `duplicate` (same blurb reused) → `publisher-cap` (6 pages max per publisher) → `below-cutoff`.

The publisher cap and the deprecation check both earn their place: without the cap one vendor's
35 near-identical wrappers around a single paid API dominate the top; without the deprecation
check the #1 skill on the site was one whose first line reads "no longer maintained".

## Architecture

```
clawhub.ai /api/v1 ─┐
skills.sh (rendered) ├→ ingest/ → data/*.json ─┐
GitHub avatars ──────┘                          ├→ db/build-db.mjs → data/oxde.db (+FTS5)
analyze/ (heuristics, gate, agent reviews) ─────┘                          │
                                                     db/query.mjs ← ───────┘
                                                          │
                              site/html.mjs ← build.mjs ──┴→ dist/ → server.mjs
```

Dependency arrow points one way: `build → query → db`, `build → html`. Nothing renders data it
also computed. Zero npm dependencies; **Node 24+** for built-in `node:sqlite`.

- `ingest/` — one adapter per registry; a failing source falls back to the last snapshot with a loud warning.
- `analyze/heuristics.mjs` — language, safety grade, API needs, network, promo, deprecation.
- `analyze/gate.mjs` — pure publication decision.
- `rating/rating.mjs` — pure scoring.
- `db/` — the only files that know SQL.
- `site/html.mjs` — rendering only.

## Surfaces

**Human:** `/` · `/skills` (live filters: language, registry, safety) · `/skills/{slug}` ×3,000 ·
`/publishers` · `/packs` · `/docs`.

**Agent** — the differentiator, since skills.sh gates its API behind Vercel OIDC and MyClaw has none:

- content negotiation — `curl` any URL returns markdown; HTML only for browsers
- a `.md` twin of every page
- open unauthenticated `/api/v1/{skills,skills/{slug},publishers,meta}`
- `/llms.txt`, `/llms-full.txt`
- `/oxde.db` — the slim SQLite index with FTS5, downloadable and queryable offline
- `/b/{slug}.svg` score badges for README embedding
- JSON-LD `SoftwareApplication` + `AggregateRating` + `inLanguage`

## Design

All-monospace — a website that is also an API. Near-black `#0c0e0b`, acid `#c8ff4d`, hairline
alpha rules, `// section` markers, big tabular numbers. Deliberately spare after an earlier,
busier version was too loud.

## State

39,212 skills · 5,303 scanned · 3,000 published · 3,151 publishers · 12 agent-reviewed ·
3,005 pages / 12,019 files / 137MB. Golden tests green.

## Next

1. Crawl remaining ~34k SKILL.mds (~3h at ClawHub's rate limit) to lift coverage from 65% → 100%.
2. Crawl the 98 skills.sh official GitHub orgs (microsoft 582, sentry 302, cloudflare 138…) —
   the highest-quality untapped source.
3. Batch agent reviews across the top 500 (the CLI harness is written; the local `claude` binary
   needs repairing first — `node …/claude-code/install.cjs`).
4. Buy `oxde.ai`, deploy to Vercel, add a daily rebuild cron.
5. Publish `oxde` as an installable skill so agents query the index before installing anything.
