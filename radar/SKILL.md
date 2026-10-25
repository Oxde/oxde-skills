---
name: skill-radar
description: Discover, vet, test, and turn agent skills into content.
---

# Skill Radar

Use this workflow to scout new agent skills, workflow repositories, and registry packs without blindly installing or amplifying them.

```text
Discovery → source verification → static vet → isolated proof test
→ content candidate or catalog intake → human approval
```

## Rules

1. Use GitHub, official docs/releases, skills.sh, ClawHub, and trusted public sources as leads. Do not treat registry ranking as proof.
2. Before a recommendation, establish the concrete operator job, maintainer/source, license, activity, permission surface, and an observable payoff.
3. Before any download, installation, or execution, load and follow `skill-vetter`.
4. Scheduled runs surface at most one strong content lead, one catalog lead, and one explicit skip. `[SILENT]` is correct when nothing clears the bar.
5. Never auto-install skills, alter a website, deploy, or post socially.
6. A claimed test is only valid when it was executed in a named isolated environment and the observable output was captured.

See `CRON.md` for the live source collector, schedule, prompt contract, and handoff details.
