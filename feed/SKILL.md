---
name: feed
description: Resolve Mark's pick from the latest research menu, mark it in the feed service, and hand it to the LinkedIn writer.
---

# feed — picking from the research menu

The `feed-menu` job sends a numbered research menu into this chat twice a day. Each item in that
message maps to a feed `id` (the menu job received them as `id: <hex>` lines). Mark replies in his
own words, often by voice: "news post about 2", "let's do the skill one", "video 3", "skip all".

## When Mark refers to a menu item

1. Find the most recent research menu in this chat and resolve the item he means: by number,
   by lane ("the skill one"), by topic words, or by the company name. If two items could match,
   ask one short question naming both; otherwise do not ask.
2. Record the pick, quoting his words:

   python3 -m feed.feedctl pick <id> --note "<Mark's words>"

   Run it from the oxde-skills checkout with `FEED_URL` and `FEED_TOKEN` in the environment.
3. Start the `linkedin-writer` flow with this brief: the item's title, url, the `Insight` and
   `Why you` lines from the menu, and Mark's note. The writer's own rules apply unchanged (voice,
   anti-slop pass, visual decision, exact approval before any publish).
4. When the post is published through the writer's publish step, run
   `python3 -m feed.feedctl set-status <id> posted`. When Mark says skip, drop, or no, run
   `python3 -m feed.feedctl set-status <id> skipped`. If he asks for a video from it, record
   `--note "video: ..."` on the pick and leave the status `picked`; Cutroom reads picked items.

## Never

- Publish, comment, react, connect, or DM. The writer's approval flow is the only path.
- Invent an id. If the menu is gone from context, run `bash feed/run_menu.sh` to print the
  current offered items, or ask Mark which one he meant.
- Reply with the whole menu again. One line confirming the pick is enough.
