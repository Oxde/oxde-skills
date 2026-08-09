# oxde agents

The agent skills index. Every skill from ClawHub and skills.sh, scored 0–100 from data.

**Requires Node 24+** (`node:sqlite` is built in). Zero dependencies.

```bash
NODE=~/.nvm/versions/node/v24.18.0/bin/node

$NODE ingest/clawhub.mjs          # full ClawHub catalog  -> data/catalog.json
$NODE ingest/skillssh-deep.mjs    # skills.sh + topics    -> data/skillssh.json
$NODE ingest/fetch-details.mjs 5000  # owners + SKILL.md  -> data/details/   (resumable)
$NODE analyze/llm-harness.mjs 20  # agent reviews         -> analyze/llm-labels.json
$NODE db/build-db.mjs             # everything            -> data/oxde.db
$NODE build.mjs                   # render                -> dist/
node server.mjs                   # serve on :4871 (any Node)
node --test rating/               # scoring golden tests
```

## Layout

| path | role |
|---|---|
| `ingest/` | one adapter per registry; failures fall back to the last snapshot |
| `analyze/heuristics.mjs` | static scan of SKILL.md: language, safety, API needs, promo |
| `analyze/gate.mjs` | which skills earn a page (pure, testable) |
| `analyze/PROMPT.md` | agent-review rubric; treats SKILL.md as untrusted data |
| `rating/rating.mjs` | the Agent Score — pure, golden-tested |
| `db/build-db.mjs` | folds all sources into `data/oxde.db` (+ FTS5) |
| `db/query.mjs` | the only file that knows SQL |
| `site/html.mjs` | rendering only |
| `build.mjs` | DB → `dist/` |
| `server.mjs` | static server with markdown content negotiation |

## The score

`adoption 25 · freshness 15 · maintenance 10 · token cost 15 · safety 20 · publisher 15`

Unmeasured axes are **excluded from the arithmetic**, never given a middle guess; each skill
publishes a **coverage %**. Agent reviews add a label and never move the score.

## The gate

~39k skills are indexed, searchable and in the API. Only the top 3,000 get a page, after
removing risky scans, sub-50-install skills, duplicate descriptions, and anything past a
6-page-per-publisher cap (one vendor ships 35 near-identical wrappers around one paid API).

## For agents

Every page has a `.md` twin, and a plain `curl` gets markdown — HTML only for browsers.
Open, unauthenticated: `/api/v1/skills`, `/api/v1/skills/{slug}`, `/api/v1/publishers`,
`/api/v1/meta`, `/llms.txt`, `/llms-full.txt`, and `/oxde.db` (slim SQLite with FTS5).
