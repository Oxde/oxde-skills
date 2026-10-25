# marfitsynn — static image style (posts, carousels, covers)

Self-contained guide for any agent making still images for @marfitsynn: AI agents, Claude skills,
harness engineering, building with AI. It is the still-image version of the approved reel style
(2026-10-24). Follow it exactly. If something is not covered here, choose the quieter option.

**The world in one line:** a black terminal plate on a green dot grid. One green pixel agent mascot,
dot-matrix keywords, typed diagrams in frames with tags, and small colour marks only where they mean
something.

---

## 1. Formats

| use | size (px) | notes |
|---|---|---|
| Feed post (default) | **1080 × 1350** (4:5) | The profile grid crops to the centre 1080 × 1440 equivalent. Keep the title and hero inside y 120–1230. |
| Square | 1080 × 1080 | Only when asked. |
| Story / reel cover | 1080 × 1920 | Keep y 0–250 and y 1600–1920 free of text (Instagram UI). |
| Carousel | 1080 × 1350 per slide | Same frame on every slide; see §9. |

Margins: **72 px** on all sides for anything that matters. Nothing touches an edge except the dot grid.

## 2. Colour (palette A, green dominant)

| token | hex | job |
|---|---|---|
| `paper` | `#0b0d0b` | Background. Near-black with a hint of green. Never pure black, never a gradient. |
| `ink` (brand green) | `#5cff8a` | The agent, structure, lines, the keyword, verdict blocks, active dots. **The dominant colour.** |
| `ink-dim` | `rgba(92,255,138,.28)` | Frame borders, rules, dashed connectors. Never text. |
| `ink-soft` | `rgba(92,255,138,.60)` | Secondary mono labels (tags, dates, sources). |
| `grid` | `rgba(92,255,138,.14)` | The dot grid. |
| `text` | `#e8f0e8` | Words you read: titles, body. Off-white, slightly green. |
| `text-soft` | `#9fb3a6` | Secondary sentences. |
| `alert` | `#ff5c5c` | Wrong / old / broken / failure. **Only that.** |
| accents | `#ffe14d` yellow · `#3df2ff` cyan · `#ff4fd8` pink · `#ff9f43` orange | Small meaning marks only: one colour per item in a set (e.g. one per skill disk), a single highlight. **Never** for big fills, titles or backgrounds. At most 2 accents per image, unless it's a set of 4 marks. |

Rules:
- Green should be ≥ 80 % of all the coloured pixels in the image. If the image reads as "colourful", it's wrong.
- No gradients, no glass, no drop shadows, and no glow on type. A tight phosphor glow (≤ 12 px) is allowed on green **strokes** of the hero only.
- Dark only. There is no light theme.

## 3. Type

| role | face | size at 1080 wide | colour |
|---|---|---|---|
| Title, setup line | **Space Grotesk** 700, tracking −2 % | 56–72 px | `text` |
| Keyword (the one thing to remember) | **Doto** 800, tracking 0, line-height 1.05 | 110–150 px | `ink` (an accent colour only if the keyword *is* that item) |
| Body sentence (max 2 lines) | Space Grotesk 500 | 34–40 px | `text-soft`, one phrase in `text` bold |
| Labels, tags, data, paths, commands | **JetBrains Mono** 500/700 | 28–36 px (min 26) | `ink` / `ink-soft` |
| Source line | JetBrains Mono 500 | 24–26 px | `ink-soft` |

- Every image has **one** Doto keyword. Doto is a dot-matrix face and is unreadable below about 90 px.
- The title is a setup line plus the keyword: "Your agent has no" + **taste**, "Too many agents." + **Use one.**
- Fonts: Google Fonts `Doto`, `Space Grotesk`, `JetBrains Mono` (self-host for production).
- No other faces. No serif italic. No all-caps body text. Mono stays for data, never sentences.

## 4. Material

- **Dot grid:** `radial-gradient(rgba(92,255,138,.14) 1.6px, transparent 2px)` with a **16 px** pitch, covering the whole canvas. Fixed; everything sits on it.
- **Frame:** a 2 px `ink-dim` border (2 px survives Instagram compression) with corner radius 6 px. A mono **tag breaks the top edge**: `┤ ~/agents ├` on a `paper` background patch, 28 px JetBrains Mono, `ink-soft`. Frames hold diagrams, lists, files and screens.
- **Verdict block:** a `ink` fill with `paper` text (JetBrains Mono 700 or Space Grotesk 700). One per image at most.
- **Bracket button:** `[ comment AGENT ]`, mono, a 2 px `ink` border, or filled `ink` with `paper` text.
- **Connectors:** 2 px dashed `ink-dim` lines, with right angles or soft single curves. Show an active path in solid `ink` and a broken path in `alert` (a small zig-zag or ✗).
- **Typed rule:** a row of `═` in `ink-dim` (JetBrains Mono) to separate a header or footer band.
- **Pixel props:** floppy disks (= skills), a backpack (= skills pack), a clapperboard, a magnifier, a speech bubble (mono text in a 2 px `ink` box), "?" made of blocks. Use the same pixel size as the agent.

## 5. The mascot: the green pixel agent (use this, never another mascot)

A chunky pixel blob with two angled antennae, white eyes, little legs. **Always pixel-exact**: crisp squares, no anti-aliasing, no outlines, no gradients, every square on a whole-pixel position. Pixel size **12–24 px** on posts (16 px default). Each map character is one square:
`G` `#5cff8a` · `W` `#e8f0e8` · `l` `#b9ffcc` · `d` `#276237` · `k` `#0b0d0b` · `.` empty.

Body (17 × 12), with the legs (3 rows) and the shadow (1 row) under it:
```
...G.........G...
....G.......G....
...GGGGGGGGGGG...
..GlGGGGGGGGGGG..
..GGGGGGGGGGGGG..
..GGGGGGGGGGGGG..
..GGGGGGGGGGGGG..
..GGGGGGGGGGGGG..
..GGGGGGGGGGGGG..
..GGGGGGGGGGGGG..
..GGGGGGGGGGGGG..
...GGGGGGGGGGG...
.....GG...GG.....
.....GG...GG.....
....GGG...GGG....
.....ddddddd.....
```

Faces are drawn **over** the body from row 4 (the 5th row) down, same 17 columns. `.` keeps the body green:
```
normal            happy             surprised         proud
.................  .................  .....WW...WW.....  .................
.....WW...WW.....  .....WW...WW.....  ....WkkW.WkkW....  ....WWWW.WWWW....
.....WW...WW.....  ....W..W.W..W....  ....WkkW.WkkW....  ....WWWW.WWWW....
.....WW...WW.....  .................  .....WW...WW.....  .................
                   .......kkk.......  .................  ..........k......
                   ........k........  .......kkk.......  .......kkk.......
                                      .......kkk.......
```

Arms (2 px wide, attached at column 15 on the right; mirror for the left): `down` rows 8–9, `up` rows 4–7 (raised, holds a prop above its hand), `out` 3 px wide at rows 7–8 (pointing).

How to use it:
- The agent **acts out the idea**. It is a character, not a logo. One agent per image, unless the idea is "many agents"; then make small copies at px 8–10 in a grid.
- Not on every image. Use it for claims, feelings and jokes. Use a typed diagram or real proof for exact things.
- **Never** a white/round/smiley/robot/headphones mascot, a 3D robot, a brain or a lightbulb.

## 6. Composition (1080 × 1350)

- 72px margins.
- Header/tag at y≈72–150.
- Space Grotesk title around y≈150.
- One Doto keyword around y≈230.
- Hero diagram/frame between y≈420–1100.
- One-line takeaway/verdict around y≈1150.
- Source line around y≈1230.
- One idea per image. Hero fills 45–60% of the height. Align to the 16px grid.

## 7. Picking the picture

1. proof: real screen/terminal/number with source
2. literal thing
3. typed diagram for architecture/before-after/flow
4. green pixel agent acting out claim
5. metaphor only if it carries the information

To show a wrong idea, draw it fairly and kill it with `alert`. Never use generic AI clip-art.

## 8. Copy

- Headlines name a struggle or verdict: `Too many agents. Use one.`
- Short declarative sentences in second person.
- Source numbers with source/date.
- Never present image as another company’s asset; source line only. Signature is `@marfitsynn`.

## 9. Carousels

- Slide 1: hook.
- Subsequent slides: one point per slide with the same title position/frame.
- Last: takeaway + CTA bracket button.
- Progress mark top-right such as `02/05`.

## 10. Rendering

Write exact-size HTML and render via headless Chrome:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=1080,1350 --virtual-time-budget=4000 --screenshot=out.png file:///abs/path/post.html
```

## 11. Check before delivering

- [ ] Green dominates; accents small; red only means wrong.
- [ ] One Doto keyword ≥110px; title Space Grotesk; mono ≥26px.
- [ ] Visible dot grid; no gradients/shadows/glow on type.
- [ ] One idea; hero 45–60%; 72px margins.
- [ ] Mascot, if used, is the pixel agent above.
- [ ] Source attribution, not borrowed company branding.
- [ ] Rendered exact size and checked at phone scale.

## 12. Example: one main agent post

**Single image (1080 × 1350):**
- Header: `┤ agent architecture ├` with typed rule.
- Title: `Too many agents.` Keyword: **Use one.**
- One 936px wide frame split into halves by dashed divider.
  - Left tag `┤ before ├`: six tiny pixel agents (px 8) in team boxes (`sales`, `support`, `ops`, `hr`, `legal`, `eng`), tangled connectors, broken red paths. Caption: `6 contexts · 6 prompts · no shared memory`.
  - Right tag `┤ after ├`: one happy pixel agent at px16. Four floppy disks plug into it on short green connectors, labelled `search`, `plan`, `write`, `eval`. Verdict: `one context · skills on demand`.
- Takeaway: `subagents still win for: research · verification · parallel work · permission boundaries`.
- Source: `source: Anthropic (Oct 2026)` plus `@marfitsynn`.

**Carousel:** hook → old harness → broken handoffs → one agent with skills → when to keep subagents.
