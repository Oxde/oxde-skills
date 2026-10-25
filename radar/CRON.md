# Skill Radar cron contract

> **Superseded on 2026-10-25** by the research feed: see `feed/CRON.md`. Kept for one proving week as rollback.

## Purpose

Find fresh, potentially useful agent skills and workflow packs **without** turning registry rankings into content spam or auto-installing untrusted code.

## Active schedule

- **Profile:** main/default Hermes agent
- **Schedule:** `30 10 * * *` (daily, local profile timezone)
- **Active job:** `dfbc156f55c1` — `Skill Radar — multi-source scout`
- **Source collector installed at:** `~/.hermes/scripts/skill_radar_multisource.py`
- **Canonical version:** `radar/skill_radar_multisource.py` in this repository

## Collector sources

1. **GitHub API** — recent repos matching agent skills, Claude skills, and agent workflows; plus a small watchlist.
2. **ClawHub public API** — targeted query results for `agent`, `video`, `copywriting`, and `research`.
3. **skills.sh public pages** — `trending` and `hot` listing URLs. Its direct API currently requires authentication, so the collector intentionally uses public HTML, not a bypass.

The repository already has deeper catalog ingestors:

```bash
NODE=~/.nvm/versions/node/v24.18.0/bin/node
$NODE ingest/clawhub.mjs
$NODE ingest/skillssh-deep.mjs
```

Use those for full catalog/index refreshes. Use the Python collector for a lightweight daily lead feed.

## Agent prompt contract

The scheduled main agent must return at most three items:

- **A — post-worthy:** a specific skill/workflow plus a sharp, non-generic operator angle.
- **B — catalog candidate:** something potentially worthy of Oxde's website after review.
- **C — skip:** a hyped or weak candidate with an explicit reason.

Every item must include canonical source URL, what is demonstrated versus merely claimed, safety/test state, and next action.

## Safety gates

- Discovery is metadata/README/source inspection only.
- Never install or execute a skill during scheduled scouting.
- Run `skill-vetter` before downloading, installing, or executing a selected candidate.
- A real test must use an isolated scratch/worktree, no browser session, no production checkout, and no secrets unless the user explicitly approves a scoped credential path.
- No automatic LinkedIn posting, website modification, deployment, or catalog publication.

## Metric discipline

- stars/downloads/installs are signals, not proof of utility;
- skills.sh pack installs can make several individual skills look equally popular;
- one exact workflow, evidence, and a visual proof path beat a generic "top skills" list.

## Running locally

```bash
python3 radar/skill_radar_multisource.py
# or the active installed link:
python3 ~/.hermes/scripts/skill_radar_multisource.py
```
