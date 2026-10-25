---
title: Platform adapters and authentication
source_type: note
captured: 2026-10-10
tags: [linkedin, platforms, auth, api]
connections:
  - "[[LinkedIn Growth OS]]"
status: active
---

# Platform adapters and authentication

The writing system is platform-neutral. It can be shared and installed elsewhere. The platform adapter changes.

## Shared core

Portable to LinkedIn, X, Threads, Reddit, Bluesky, newsletters, or a blog:

- `VOICE.md`
- source/evidence research
- draft files + statuses
- hook and anti-slop review
- visual/card workflow
- approval gates
- post archive + learning loop

## LinkedIn adapters

### 1. Maton managed OAuth — publishing

Best default for individual publishing in this system.

- User completes OAuth once in a browser through Maton's connection URL.
- The writer can create text/image/video/document posts after explicit `post now`.
- The current writer already uses this path.
- It is not a complete personal-feed research API.

### 2. Official LinkedIn API — real, but restricted for personal read data

LinkedIn has an API. It is not a broadly open personal-feed API.

- `w_member_social`: publish/manage posts for the authenticated member.
- `w_member_social_feed`: write comments/reactions for the authenticated member.
- `r_member_social` / `r_member_social_feed`: read member posts, comments, reactions. Restricted / approved-developer access.
- `r_member_postAnalytics`: member post analytics. Community Management program access applies.

For company pages, the official Community Management API is much more practical: organization posts, comments, reactions, and analytics are supported when the user has the relevant page role.

Conclusion: official API is great for approved publishing; it is not the easy, universal solution for reading a personal creator account or scouting arbitrary public posts.

### 3. Logged-in browser bridge / OpenCLI — observation

Best free path for an individual account.

- User logs into LinkedIn in the persistent Chrome/Chromium profile once.
- Browser Bridge/OpenCLI reuses that normal browser session for slow, read-only observation.
- Enables own-post metrics, timeline/search, and visible comments where the UI exposes them.
- No password/cookie is pasted into chat or stored by the writing system.
- Read-only by default; stop on CAPTCHA/security challenge.

Current local status: OpenCLI exists, but the persistent LinkedIn session is logged out (`li_at` cookie missing). A normal LinkedIn login in that browser is needed to enable this route.

### 4. Structured third-party data API — reliable research at a cost

Use only if browser reading is brittle or the system needs dependable JSON/search at scale.

Candidates previously evaluated:

- LinkedAPI.io — post comments/reactions and profile-post monitoring.
- AgntData — pay-per-request LinkedIn data endpoints.
- Apify — one-off actors / experiments.

These services still require an account/API key; they are not zero-login magic. Evaluate privacy, cost, rate limits, and terms before adopting one.

## Recommended setup for a normal user

1. Use the writing system locally or in a hosted agent.
2. Connect LinkedIn to Maton once for safe publishing.
3. Log into LinkedIn once in the browser bridge for read-only research and own-post monitoring.
4. Keep comments/DMs/likes manual or exact-approval gated.
5. Upgrade to a structured data API only after the free browser route proves too weak.

## Other platforms

The same Growth OS can support other platforms by adding one adapter per platform:

- X: use primary-source fetcher + X posting adapter if configured.
- Bluesky: official API adapter.
- Reddit: API/read adapter, stricter community rules.
- Newsletter/blog: direct CMS adapter.

Never make the portable core depend on browser cookies, Maton, or one social network's API. Those belong only in adapters.
