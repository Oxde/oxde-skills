---
name: skill-posts
description: Write LinkedIn posts about agent skills, repos and tools that people bookmark to use later. Use when a research-menu pick is in the SKILLS or REPOS lane, or when Mark asks for a post about a skill, repo, pack, or workflow tool.
---

# Skill posts — useful things people save

A skill post is not news. The reader saves it because it hands them something they can install or
copy this week: a skill, a repo, a pack, a workflow. The measure is bookmarks, not likes. Every
example in `examples.md` has more bookmarks than likes; that ratio is the target.

Read `VOICE.md` and `ANTI_AI_RULES.md` from the LinkedIn Writer first. They win on any conflict.
This file adds what is specific to skill posts.

## The evidence ledger (before writing a word)

Fill all eight. If one is missing, the post is not ready; say which and stop.

| field | where it comes from | example |
|---|---|---|
| canonical link | the repo or skills page, not a tweet about it | github.com/cloudflare/security-audit-skill |
| one number with a source | stars, installs, downloads, count of skills, last-commit date | "40.9K stars", "74 skills", "7.5m downloads" |
| what it does when installed | 3–5 bullets from the README, the SKILL.md, or a run; each bullet one concrete behaviour | "deletes code written before tests" |
| what it does not do | one honest limit from the docs or the test | "no tutorial", "Node only" |
| compatibility | which harnesses, in the repo's own words | "Claude Code (plugin), Codex, OpenCode" |
| one usage rule | the single operator instruction a reader would otherwise miss | "run it with the free models; run it even after a model audit" |
| the install line | exact command or path, copied, not typed from memory | `npx skills add owner/repo --skill name` |
| receipt | what Mark actually ran or saw, or `none yet`; never invent | "ran it on the feed service, 3 findings, 1 real" |

Rules on evidence: metadata and README are enough for a *breakdown*; a *receipt post* needs a real
run in a scratch dir with no secrets (see `radar/CRON.md` safety gates). Never install or execute a
skill you have not read. Numbers come from the page, with the day you read them.

## The five shapes (pick one, never blend)

1. **Breakdown** — one skill or repo, explained as behaviour. Hook: actor + number + what changes.
   Body: "here is what happens when you install it" → 3–5 arrows/bullets → one limit → compat +
   license → link. The superpowers post is the template: 6.1k likes, 14.5k bookmarks.
2. **Endorsement + rule** — three to six lines. The claim, the link, then the one usage rule that
   makes it work. Cloudflare audit: 8.7k likes, 16.4k bookmarks from five sentences. Only when
   Mark has used it; the rule *is* the receipt.
3. **Ranked list** — 5–10 items in one category, each with author, link, one phrase. Anti-slop
   list: 3.5k / 7.3k. The category must be a real reader problem ("my agent writes like AI"),
   not a theme. Order by what Mark would install first, and say so.
4. **Pack / collection** — "if you do X, save this": count, coverage list, engines or harnesses,
   link. Gamedev pack: 3.3k / 6.5k. Works when the count is big and the scope is specific.
5. **Receipt** — what Mark built or shipped with it, then the open-source link. Designer skill:
   7.8k / 12.3k, carried by the proof image. Needs a visual of the output, not of the repo.

## Hook standard for this lane

Line 1 carries a named thing and a number or a behaviour, in Mark's register:

- `A GitHub repo with 40.9K stars just changed how my agents write code.`
- `Cloudflare open-sourced the security audit skill their own team runs.`
- `74 gamedev skills in one repo. Unity, Godot, Unreal.`
- `This skill deletes any code my agent writes before the test exists.`

Never: "Holy shit", "insane", "game-changer", "must install", emoji sirens. On X those carry the
X posts; on LinkedIn, in Mark's voice, the number and the behaviour carry it. The energy comes from
specificity, not adjectives.

## Body rules

- One bullet = one behaviour the reader can picture. "Enforces TDD" is a label; "writes the
  failing test, watches it fail, then writes the code" is a behaviour.
- Put the install line or the link where the reader's thumb stops: after the bullets, before any
  opinion.
- Say the limit. A post with no limit reads like an ad and gets fewer saves.
- Compatibility in the repo's own words. If it says "works with any harness", quote that.
- Close with the usage rule or the first thing to try. No question, no CTA, unless the pack
  genuinely needs a "comment X and I send it" (Mark's reel pattern), and then only once.
- Length: breakdown 120–220 words; endorsement under 60; list one line per item plus a two-line
  intro; pack under 100; receipt under 80 plus the image.

## Visual

Default: a product screenshot or terminal output of the thing running. Second choice: the
`STYLE-STATIC.md` card with the number as the keyword. Never a logo wall, never a stock image.
For a ranked list, a carousel with one item per slide beats a wall of links.

## Quality check before handing to Mark

- Every number has a source and a date.
- Every bullet maps to a line in the README, SKILL.md, or the run log.
- The limit is real and from the docs or the run.
- The link resolves and is canonical (repo or skills page).
- Zero words from the banned lists in VOICE.md and ANTI_AI_RULES.md.
- Would an operator save this to use on Monday? If not, which field in the ledger is weak?

## Hand-off

Return: the shape chosen and why, the filled ledger, the draft, the visual decision, and the
open questions for Mark (receipt, opinion). Then follow the writer's normal approval flow.
