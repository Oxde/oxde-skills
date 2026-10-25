# Skill-post examples with numbers (read 2026-10-25 via FxTwitter)

All X posts; LinkedIn posts in this lane are rarer and shorter, so these set the *ingredients*, not
the register. Bookmarks above likes in every case: the save-to-use signal this lane is judged on.

| # | author | likes | bookmarks | views | shape | what carries it |
|---|---|---|---|---|---|---|
| 1 | @ihteshamali on obra/superpowers | 6,157 | 14,459 | 953k | breakdown | "40.9K stars" + five "here is what happens when you install it" arrows, each a behaviour + limit-free but honest philosophy line + compat + MIT |
| 2 | @milesdeutscher on Taste skill | 4,144 | 10,423 | 846k | endorsement | three claims and a link; works because the author has a large audience, not because of the text |
| 3 | @mattpocockuk on his skills repo | 7,373 | 10,711 | 595k | creator walkthrough | "160K stars, 7.5m downloads, and no tutorial" + list of five commands + video |
| 4 | @juampitech anti-slop ranking | 3,534 | 7,264 | 605k | ranked list | ten items, each author + install link; quoted the earlier post that "got traction" |
| 5 | @jurbed on cloudflare/security-audit-skill | 8,722 | 16,362 | 598k | endorsement + rule | the link plus one operating rule: run on everything, with free models, even after a model audit; "works in all agent harnesses and is model independent" |
| 6 | @peko1487584 on awesome-gamedev-agent-skills | 3,331 | 6,513 | 245k | pack | "74 skills", engine list, coverage list, harness compat, link; opens with "friends doing X can bookmark this" |
| 7 | @elayadesigns on ai-design-skills | 7,820 | 12,348 | 394k | receipt | "all of these landing pages in two months" + image + open-source link |

## What the numbers say

- The highest bookmark ratio (1.9) is the shortest post (#5). Length is not the lever; the usage
  rule is.
- Breakdown (#1) is the only shape that works without the author's own audience or output. It is
  the default for the feed's SKILLS and REPOS items.
- Every post names the harnesses it works with. Readers save what they can run.
- Lists (#4) and packs (#6) win on count and coverage, not on opinion.

## Full texts

### 1. Superpowers breakdown (6.2k / 14.5k)

> 🚨 Holy shit...A developer on GitHub just built a full development methodology for AI coding
> agents and it has 40.9K stars on GitHub. It's called Superpowers, and it completely changes how
> your AI agent writes code. Right now, most people fire up Claude Code or Codex and just… let it
> go. The agent guesses what you want, writes code before understanding the problem, skips tests,
> and produces spaghetti you have to babysit. Superpowers fixes all of that. Here's what happens
> when you install it: → Before writing a single line, the agent stops and brainstorms with you…
> → Once you approve the design, it creates an implementation plan so detailed that "an
> enthusiastic junior engineer with poor taste and no judgement" could follow it. → Then it
> launches subagent-driven development. Fresh subagents per task. Two-stage code review after each
> one… → It enforces true test-driven development. Write failing test → watch it fail → write
> minimal code → watch it pass → commit. It literally deletes code written before tests. → When
> tasks are done, it verifies everything, presents options (merge, PR, keep, discard), and cleans
> up. The philosophy is brutal: systematic over ad-hoc. Evidence over claims… Works with Claude
> Code (plugin install), Codex, and OpenCode. This isn't a prompt template. It's an entire
> operating system for how AI agents should build software. 100% Opensource. MIT License.

Mark's version drops the siren and "Holy shit", keeps the number, the five behaviours, the compat
line and the license, and adds the one thing the X post lacks: a limit.

### 5. Cloudflare security audit (8.7k / 16.4k)

> I highly recommend cloudflare's security audit skill: github.com/cloudflare/security-audit-skill
> Run it on all your software. Run it with the free models. Use it even if you used a model to
> audit something - it will find much more things. Works in all agent harnesses and is model
> independent.

### 4. Anti-slop ranking (3.5k / 7.3k)

> Post got a lot of traction, so I made a rank with the anti-slop skills people need to install.
> 1. stop-slop - @hvpandya skills.sh/hardikpandya/stop-slop 2. no-ai-slop - @petergyang … 10.
> anti-ai-slop-writing - @jalaal_tweets …

### 6. Gamedev pack (3.3k / 6.5k, Chinese)

> Friends building games with AI can bookmark this. An open-source project on GitHub collects 74
> game-dev skills, supports Unity, Godot, Unreal… covers art, character animation, performance,
> Steam release, and auto-matches the right skill. Works in Claude Code and Codex. [link]

### 3, 2, 7

Pocock: "My skills repo has 160K stars, 7.5m downloads... and no tutorial. So, here it is." + five
slash commands + video. Deutscher: "This is an insane Fable 5 UI/UX hack. This 'Taste' skill
completely kills generic AI-slop…" + link. Elaya: "I designed all of these landing pages in the
last two months, using Claude and Cursor with my custom AI designer skill. The skill is open
source: [repo]" + image grid.

## Worked example in Mark's voice (breakdown shape, from a feed item)

Item: hashgraph-online/hol-guard, 997 stars, Apache-2.0, pushed 2026-10-25, read 2026-10-25.
Ledger filled from the README only, so the receipt field is `none yet` and the post says so.

> A 997-star repo wants to review every command my agent runs before it runs.
>
> hol-guard calls itself antivirus for AI agents. It is a local policy layer: no account, pipx
> install, a wizard that finds the agents on the machine.
>
> What it does once it is in the loop:
> – reviews shell commands, file access, package installs and MCP tool calls before they execute
> – flags secret exposure, destructive operations, prompt injection in tool results, and risky packages
> – allows, blocks, or asks you, per your policy, and keeps a local receipt of every decision
> – scans plugins, skills and MCP server config for changes before launch
>
> Limit, from the docs: coverage depends on the hooks each agent exposes. Codex gets native
> pre-tool hooks; check the support matrix for yours before trusting it.
>
> Codex, Claude Code, Cursor, Gemini CLI, Hermes, OpenCode and ten more. Apache-2.0.
> github.com/hashgraph-online/hol-guard
>
> I have not run it on my own agents yet. When I do, the post is the findings.

Every bullet maps to the README's "What HOL Guard Protects" table and install section; the limit
is the README's own sentence about per-agent coverage. Number in line 1, four behaviours, a real
limit, compat and license, the link, and an honest receipt line instead of a fake one.
