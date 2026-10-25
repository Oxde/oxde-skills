# LinkedIn Growth OS

A portable, source-backed content system for LinkedIn. It is designed for an agent or a human operator, not a generic prompt pack.

## What it does

- turns sources, product launches, and rough ideas into posts in a real voice
- stores drafts as Markdown files with explicit statuses
- separates research, editorial, publishing, and learning loops
- creates comment queues for deliberate engagement
- keeps all external social actions behind exact human approval
- supports LinkedIn now, with adapters for other platforms later

## Start here

1. Copy `templates/VOICE.md` to your workspace and fill it with real examples.
2. Read `docs/architecture.md`.
3. Copy `templates/draft.md` into `drafts/` for each promising post.
4. Read `docs/linkedin-adapters.md` and choose an integration path.
5. Use `scripts/quality_check.py` as a read-only preflight before signoff.

## Core vs adapters

The core is portable:

- voice profile
- source/evidence research
- draft files and status
- hook and anti-slop review
- visual decision
- archive and learning loop

Adapters are platform-specific:

- authentication
- publishing
- feed/search observation
- comments/replies
- analytics

## Safety

Never publish, comment, like, follow, connect, or DM without exact user approval of the payload.

This repo does not include secrets, browser cookies, API keys, or credentials.

## License

MIT
