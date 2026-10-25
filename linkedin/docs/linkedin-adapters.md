# LinkedIn adapters

## Reality check

LinkedIn has an official API, but personal creator read access is restricted. A complete creator workflow usually needs more than one adapter.

## 1. Publishing: OAuth / official API / managed provider

Use an OAuth flow. The user clicks a consent link once in their own browser. The provider stores the access token; the writing system never asks the user to paste a password into chat.

Useful official scopes:

- `w_member_social` for member publishing
- `w_member_social_feed` for member comments/reactions

Require exact user approval before every post or comment.

## 2. Own-post metrics and research: logged-in browser bridge

The free practical option for personal accounts.

The user logs into LinkedIn once in the browser profile used by the bridge. The bridge can then read visible posts, search results, comments, and own-post analytics slowly and read-only.

Pros: no additional data provider bill; user owns the login session.

Cons: UI/session can change; no high-volume scraping; stop on CAPTCHA/security challenges.

## 3. Structured third-party data API

Use this only when the product needs stable JSON, background jobs, or broader post/comment discovery. The user still needs an account/API key and the operator must review privacy, pricing, rate limits, and terms.

## 4. Official member read API

`r_member_social`, `r_member_social_feed`, and member analytics access are restricted/approval-gated in LinkedIn's ecosystem. Do not build a product that assumes every user can get these scopes.

## Recommended user onboarding

1. Install/import this system.
2. Fill `VOICE.md`.
3. Connect publish OAuth once.
4. Optionally connect a browser bridge by logging into LinkedIn once.
5. Choose whether comments are manual-paste only or an approval-gated write adapter.
6. Create first source-backed draft.

No passwords or cookies should ever travel through an agent chat.
