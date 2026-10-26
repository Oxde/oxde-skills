---
name: skill-posts
description: Write LinkedIn posts about agent skills, repos and tools that people bookmark to use later. Use when a research-menu pick is in the SKILLS or REPOS lane, when the skill desk hands over a candidate, or when Mark asks for a post about a skill, repo, pack, or workflow tool.
---

# Skill posts — useful things people save

A skill post is not news and not documentation. The reader saves it because line one makes a
claim they want to be true, and the rest proves it with things they can install this week.
The measure is bookmarks, not likes. Every example in `examples.md` has more saves than likes
or thousands of likes; `examples.md` also holds the worked rewrite that sets the bar.

Read `VOICE.md` and `ANTI_AI_RULES.md` from the LinkedIn Writer first. They win on any conflict.
This file adds what is specific to skill posts.

## 1. The evidence ledger (before writing a word)

Fill all eight. If one is missing, the post is not ready; say which and stop.

| field | where it comes from | example |
|---|---|---|
| canonical link | the repo or skills page, not a tweet about it | github.com/cloudflare/security-audit-skill |
| one number with a source | stars, installs, downloads, count of skills, last-commit date | "40.9K stars", "74 skills", "7.5m downloads" |
| what it does when installed | 3–5 behaviours from the README, the SKILL.md, or a run; each one a thing the reader can picture | "deletes code written before tests" |
| what it replaces or beats | the paid tool, the known skill, or the manual chore it removes | "a free, local alternative to ElevenLabs" |
| what it does not do | one honest limit from the docs or the test | "no tutorial", "needs a Scenario account" |
| compatibility | which harnesses, in the repo's own words | "Claude Code (plugin), Codex, OpenCode" |
| the install line | exact command or path, copied, not typed from memory | `npx skills add owner/repo` |
| receipt | what Mark actually ran or saw, or `none yet`; never invent | "ran it on the feed service, 3 findings, 1 real" |

Rules on evidence: metadata and README are enough for a *breakdown*; a *receipt post* needs a real
run in a scratch dir with no secrets (see `radar/CRON.md` safety gates). Never install or execute a
skill you have not read. Numbers come from the page, with the day you read them.

## 2. The hook: a claim with a number, then whether it is true

Line one is the whole post for most readers. It carries one of these, in Mark's register:

| pattern | example from a post that worked |
|---|---|
| **the number + the claim** | "A GitHub repo with 40.9K stars just changed how my agents write code." |
| **free alternative to a paid thing** | "The #1 trending repo on GitHub is a free alternative to ElevenLabs that runs locally." |
| **new core skill + free source** | "Harness engineering is the new core AI skill. This repo teaches it for free." |
| **the tried-N, kept-K list** | "I tried 100+ repos for Claude. These 6 are the ones I kept." |
| **why it blew up** | "Why one repo gained 100K stars in a day." |
| **one behaviour, stated as a shock** | "This skill deletes any code my agent writes before the test exists." |
| **Mark's claim check** | "Your agent can now ship brand-consistent campaigns. Is it really true?" |

Rules: a named thing and a number or a behaviour in line one. The claim may sound too good; line
two then says exactly what it is in one sentence. Never "holy shit", "insane", "game-changer",
"must install", emoji sirens: on LinkedIn the number does that job. Never a question with no
answer in the post. Write three hooks, keep the one with the most specific noun.

## 2b. The reader has never heard of it (the comprehension rules)

The post fails if a smart friend who has never heard of the tool cannot say, after reading,
what it is and what they would use it for. Mark rejected a draft on exactly this: correct on
every ledger field, "sounds like AI, I don't understand the concept". So, before the structure:

- **Say what it is in plain words, in the first two lines.** The category first ("an image
  generator", "a code reviewer that runs in your terminal", "a pack of instructions your agent
  reads"), then the name. If the thing sits on top of another product, name that product and
  what it does too: "Scenario is a platform that generates images and video with AI models; this
  repo teaches your coding agent to use it like a designer would".
- **One picturable example with a real object.** Not "turns one product shot into platform
  formats" but "you give it one photo of your sneaker; it makes the Instagram, the banner and the
  story version, keeps the sneaker identical in all of them, and tells you which three came out
  broken". One example beats four categories.
- **The jargon test.** Every phrase from the README that an operator friend might not know gets
  replaced or explained in the same sentence: payload, dry-run, pass/fail criteria, identity
  drift, reference slots, MCP, baseline, pipeline, orchestration, schema. "MCP" becomes "the
  connector that lets your agent call it". If a phrase cannot be made plain, it is not a post
  line; it is a ledger line.
- **Behaviour, then why it matters.** Each arrow is a behaviour the reader can picture and, when
  it is not obvious, the money or time it saves in the same breath: "prices every model before
  it generates, so a 30-image run does not cost you $40 by accident".
- **Mark's claim-check voice.** The post sounds like Mark telling a friend what he found, with
  one blunt opinion at the end, not like a changelog. "Is it really true?" is the frame: here is
  the claim, here is what it actually does, here is the catch.

## 3. The structure: Mark's story shape (the default)

Mark's own published posts are not feature lists. They are a story told in short lines, one
thought per line, with a twist in line two and one bold number in the middle. His single-agent
post (in `examples.md`) is the anchor: claim → "Not because X" → the failure pattern everyone
recognizes → the mechanism → the number → "That is the important change." → the rule. A skill
post follows the same arc; the install line is just the last beat.

```
<line 1: the claim, as a thing that is now true>
<line 2: the twist: "Not because…", "Is it really true?", or the catch>

<the failure everyone recognizes, told as a scene in 2–4 short lines:
 what people do today, what goes wrong, what it costs>

<what the thing is, in plain words: category, name, what it sits on>

<the mechanism, 3–5 short lines or arrows: what the agent now does differently,
 each a behaviour you can picture, with the money or time in the same breath>

<the number, bold, from the source: a before/after, a cost, a count>

<the limit, one line, honest>

<"That is the important change." style line: the one-sentence takeaway>
<the rule: when to use it, when not>
<install line or link>
```

Every line stands alone. No paragraph longer than two sentences. Bold one number only.

Hard caps still apply, but length follows the story: Mark's anchor post is ~1,500 characters
and reads fast because of the line breaks, so 1,200–1,600 is fine for this shape; 900 for the
arrows-only breakdown. If the ledger has no failure scene and no number, the post is thinner;
say so in the hand-off.

Hard caps: 900 characters for a breakdown, 60 words for an endorsement, one line per item in a
list, 100 words for a pack. If the ledger has more than fits, cut behaviours, never the number
story or the limit. Bold labels on arrows are fine; paragraphs under each arrow are not.

For a multi-skill workflow pack, lead with one costly operator pain, then use three or four
named scenarios. Each scenario must show the input, the concrete workflow behaviour, and the
decision or artifact it produces; do not substitute a feature-category list for use cases.
Meaty means higher evidence density, not more copy. Cut a generic final moral when the scenarios,
one limitation, and the install/link already let the reader act.

## 4. The five shapes (pick one, never blend)

1. **Breakdown** — one skill or repo, as behaviour. The structure above. Default for the feed's
   SKILLS and REPOS items. Superpowers on X: 6.1k likes, 14.5k saves; harness repo on LinkedIn: 3.1k likes.
2. **Endorsement + rule** — three to six lines: the claim, the link, the one usage rule that
   makes it work. Cloudflare audit: 8.7k likes, 16.4k saves from five sentences. Only when
   Mark has used it; the rule *is* the receipt.
3. **Ranked list** — 5–10 items in one real reader problem, one line each: name, what it does,
   link. "I tried 100+, kept 6" on LinkedIn: 343 likes from a small account. Order by what Mark
   would install first and say so; close with one workflow that chains three of them.
4. **Pack / collection** — "if you do X, save this": count, coverage, harnesses, link. Gamedev
   pack: 3.3k / 6.5k. Works when the count is big and the scope is specific.
5. **Receipt** — what Mark built or shipped with it, then the open-source link. Designer skill:
   7.8k / 12.3k, carried by the proof image. Needs a visual of the output, not of the repo.

## 5. The number story

Every post that performed has one concrete comparison the reader can repeat: "$9 and 20 minutes
for a broken game, $200 and 6 hours for a playable one" (from Anthropic's own test), "50K stars,
2.6M downloads, 8 engines", "one minute to set up: download, record a few seconds, press a
hotkey". Find it in the README, the docs, or the run. If there is none, the post is thinner;
say so in the hand-off rather than inventing one.

## 6. Body rules

- One arrow = one behaviour the reader can picture. "Enforces TDD" is a label; "writes the
  failing test, watches it fail, then writes the code" is a behaviour.
- Say what it replaces or removes: the paid tool, the manual chore, the prompt nobody can maintain.
- Say the limit. A post with no limit reads like an ad and gets fewer saves.
- Compatibility in the repo's own words. If it says "works with any harness", quote that.
- Put the install line or the link after the arrows, before any opinion.
- Close with the usage rule, honest limitation, or first thing to try. No question, no CTA, unless
  the pack genuinely needs a "comment X and I send it" (Mark's reel pattern), and then only once.
- A personal tie-in of one line beats a paragraph of context: "it's how I built my reel-editing
  skill: show the agent 30 examples, let it work backwards".

## 7. Visual

Default: a product screenshot or terminal output of the thing running. Second choice: the
`STYLE-STATIC.md` card with the number as the keyword. Never a logo wall, never a stock image.
For a ranked list, a carousel with one item per slide beats a wall of links.

## 8. Quality check before handing to Mark

- A reader who has never heard of the tool can say what it is and what they'd use it for.
- There is one example with a real object in it, and no README phrase left unexplained.
- Line one has a named thing and a number or a behaviour.
- Every number has a source and a date; the number story is from the source.
- Every arrow maps to a line in the README, SKILL.md, or the run log, and is under 15 words.
- It says what the thing replaces, and what it cannot do.
- Under the length cap. Zero words from the banned lists in VOICE.md and ANTI_AI_RULES.md.
- Read it as an operator on a phone: would you save this to use on Monday? If not, which
  ledger field is weak?

## 9. Hand-off

Return: the shape chosen and why, the filled ledger, three hooks with the chosen one marked,
the draft, the visual decision, and the open questions for Mark (receipt, opinion). Then follow
the writer's normal approval flow.
