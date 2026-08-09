// site/html.mjs — layout, CSS, components. Rendering only: no fetching, no scoring.
export const esc = (s = '') => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const fmt = (n) => n == null ? '—' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'k' : String(n);
export const tok = (t) => t?.count == null ? '—' : fmt(t.count);

export const SAFETY = {
  safe: { label: 'SAFE', cls: 'safe', title: 'Static scan of SKILL.md found no risky patterns' },
  review: { label: 'REVIEW', cls: 'review', title: 'Scan found agent directives or promotional content — read before installing' },
  risky: { label: 'RISKY', cls: 'risky', title: 'Scan found dangerous shell, possible exfiltration, credential harvesting, or instruction-override attempts' },
};
export const AI_LABEL = { solid: 'SOLID', promising: 'PROMISING', niche: 'NICHE', 'promo-heavy': 'PROMO-HEAVY', risky: 'RISKY', 'low-quality': 'LOW-QUALITY' };

// registry marks — ClawHub's claw, skills.sh's Vercel triangle
export const MARK = {
  clawhub: `<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M3 2c2 0 3 1.4 3 3.2 0 1-.5 1.8-1.3 2.3M13 2c-2 0-3 1.4-3 3.2 0 1 .5 1.8 1.3 2.3M8 6.5c2.5 0 4 1.9 4 4.2S10.5 15 8 15s-4-2-4-4.3S5.5 6.5 8 6.5Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  'skills.sh': `<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true"><path d="M8 1.5 15 14H1L8 1.5Z" fill="currentColor"/></svg>`,
};
export const registryChip = (r) => `<span class="reg ${r === 'skills.sh' ? 'ssh' : 'claw'}">${MARK[r] ?? ''}${r === 'skills.sh' ? 'skills.sh' : 'clawhub'}</span>`;

const ICON_RULES = [
  [/research|news|search|arxiv|paper|academ/i, '🔬'], [/email|imap|smtp|gmail|outlook/i, '✉️'],
  [/browser|playwright|chrome|crawl|scrap/i, '🕸️'], [/pdf|docx?|excel|xlsx|document|sheet|slide/i, '📄'],
  [/crypto|trading|solana|market|wallet|defi|stock|finance/i, '📈'], [/image|photo|design|art|draw/i, '🎨'],
  [/video|youtube|film|抖音/i, '🎬'], [/audio|voice|music|speech|sound|tts/i, '🎙️'],
  [/git|github|deploy|docker|kubernetes|\bcode\b|\bdev\b|\bapi\b/i, '💻'], [/memory|knowledge|graph|ontolog|\brag\b/i, '🧠'],
  [/slack|telegram|discord|whatsapp|chat|messag/i, '💬'], [/calendar|task|todo|productiv|notion|obsidian|note/i, '✅'],
  [/time|clock|beat|schedule/i, '🕐'], [/health|fitness|sleep|medical|健康/i, '🫀'],
  [/home|iot|smart|sonos|hue/i, '🏠'], [/security|password|auth|vault|安全/i, '🔒'],
  [/weather|climate/i, '🌦️'], [/file|storage|drive|backup/i, '📦'], [/phone|call|sms/i, '📞'],
  [/travel|flight|hotel|map/i, '🗺️'], [/game|play/i, '🎮'], [/write|humaniz|text|translat|career/i, '✍️'],
];
export const iconFor = (s) => {
  if (s.icon && /\p{Emoji}/u.test(s.icon) && s.icon.length <= 5) return s.icon;
  const hay = `${s.name} ${s.topics?.join(' ')} ${s.summary}`;
  for (const [re, e] of ICON_RULES) if (re.test(hay)) return e;
  return '⚡';
};

// exported so build.mjs can write it once to /style.css — at 39k pages, inlining it
// would cost roughly a gigabyte of duplicated bytes.
export const CSS = `
:root{--bg:#0c0e0b;--panel:#131610;--line:rgba(230,255,190,.10);--ink:#f2f5e9;--dim:#8d967f;
--acid:#c8ff4d;--amber:#ffc66d;--red:#ff6e5e;--max:1120px}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
font-feature-settings:"ss02" 1,"zero" 1;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}a:hover{color:var(--acid)}
a:focus-visible,button:focus-visible{outline:2px solid var(--acid);outline-offset:3px}
.wrap{max-width:var(--max);margin:auto;padding:0 24px}
/* header */
header{position:sticky;top:0;z-index:20;background:rgba(12,14,11,.93);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.hd{display:flex;align-items:center;gap:26px;min-height:58px}
.logo{font-weight:700;letter-spacing:-.02em}.logo b{color:var(--acid)}
nav{display:flex;gap:20px;margin-left:auto}
nav a{color:var(--dim);font-size:13px;display:inline-flex;align-items:center;min-height:34px}
nav a[aria-current]{color:var(--ink)}
/* type */
.eyebrow{font-size:11px;letter-spacing:.18em;color:var(--dim);text-transform:uppercase}
.eyebrow b{color:var(--acid);font-weight:500}
h1{font-size:clamp(30px,5.4vw,60px);line-height:1.02;letter-spacing:-.045em;margin:14px 0 0;font-weight:700;text-wrap:balance}
h1 em{font-style:normal;color:var(--acid)}
h2{font-size:clamp(20px,2.6vw,30px);letter-spacing:-.03em;margin:12px 0 0;font-weight:700}
p.lede{color:var(--dim);max-width:600px;font-size:15px;margin:18px 0 0;text-wrap:pretty}
section{padding:64px 0;border-bottom:1px solid var(--line)}
section.tight{padding:36px 0}
/* stat row — Versed-style, big numbers on hairlines */
.stats{display:grid;grid-template-columns:repeat(4,1fr);margin-top:44px;border-top:1px solid var(--line)}
.stats>div{padding:20px 20px 20px 0}
.stats .n{font-size:34px;letter-spacing:-.04em;color:var(--acid);font-variant-numeric:tabular-nums;line-height:1}
.stats .k{font-size:11px;letter-spacing:.14em;color:var(--dim);text-transform:uppercase;margin-top:8px}
/* score */
.score{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums}
.bar{width:100%;max-width:96px;height:4px;background:rgba(255,255,255,.07);margin-bottom:5px}
.bar i{display:block;height:100%;background:var(--acid)}
.bar.good i{background:var(--acid)}.bar.fair i{background:var(--amber)}.bar.weak i{background:var(--dim)}
/* pills */
.pill{display:inline-flex;align-items:center;height:19px;padding:0 7px;font-size:10px;letter-spacing:.06em;
border:1px solid var(--line);color:var(--dim);white-space:nowrap}
.pill.safe{color:var(--acid);border-color:rgba(200,255,77,.3)}
.pill.review{color:var(--amber);border-color:rgba(255,198,109,.35)}
.pill.risky{background:var(--red);color:#12140f;border-color:var(--red);font-weight:700}
.pill.ai{color:#12140f;background:var(--acid);border:0;font-weight:700}
.pill.ai.warn{background:var(--amber)}.pill.ai.bad{background:var(--red)}
.pill.lang{border-style:dashed}
.reg{display:inline-flex;align-items:center;gap:4px;font-size:10.5px;color:var(--dim)}
.reg.claw{color:#ff8b63}.reg.ssh{color:#dfe3d8}
/* table */
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);text-align:left;font-weight:400;
padding:12px 14px 12px 0;border-bottom:1px solid var(--line);position:sticky;top:58px;background:var(--bg);z-index:2}
td{padding:14px 14px 14px 0;border-bottom:1px solid var(--line);vertical-align:middle}
tr:hover td{background:rgba(200,255,77,.025)}
.rk{color:var(--dim);width:34px;font-size:12px}
.num{text-align:right;white-space:nowrap}
.sk{display:flex;gap:11px;align-items:center}
.ic{width:30px;height:30px;min-width:30px;display:flex;align-items:center;justify-content:center;font-size:15px;
background:rgba(255,255,255,.035);border:1px solid var(--line)}
.sk b{font-weight:700}
.sk .by{font-size:11px;color:var(--dim);display:flex;gap:7px;align-items:center;margin-top:2px}
.av{width:14px;height:14px;border-radius:50%;background:rgba(255,255,255,.08)}
.tagrow{display:flex;gap:5px;flex-wrap:wrap}
/* filters */
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0 4px}
.filters button,.filters a{background:transparent;border:1px solid var(--line);color:var(--dim);
padding:7px 13px;font:inherit;font-size:12px;cursor:pointer;min-height:34px;display:inline-flex;align-items:center}
.filters button:hover{color:var(--ink)}
.filters button.on{background:var(--acid);color:#12140f;border-color:var(--acid);font-weight:700}
input.search{width:100%;max-width:420px;background:transparent;border:0;border-bottom:1px solid var(--line);
color:var(--ink);font:inherit;padding:11px 0;margin-top:8px}
input.search:focus{outline:0;border-bottom-color:var(--acid)}
input.search::placeholder{color:var(--dim)}
/* skill page */
.two{display:grid;grid-template-columns:1.25fr .75fr;gap:48px;align-items:start}
.side{border:1px solid var(--line);padding:22px}
.kv{width:100%;border-collapse:collapse}
.kv td{padding:7px 0;border-bottom:1px solid var(--line);font-size:12.5px}
.kv td:last-child{text-align:right;color:var(--dim)}
.axes td{padding:9px 0;border-bottom:1px solid var(--line);font-size:12.5px}
.axes .lab{color:var(--dim);font-size:11px}
.axes tr.off td{opacity:.45}.axes tr.off .bar{border:1px dashed var(--line);background:transparent}
.cov{font-size:10px;color:var(--dim);letter-spacing:.04em}
pre.term{background:#080a07;border:1px solid var(--line);padding:13px 15px;overflow-x:auto;font-size:12.5px;margin:0}
pre.term .c{color:var(--dim)}
.tabs{display:flex;gap:0;margin-bottom:-1px}
.tabs button{background:transparent;border:1px solid var(--line);border-bottom:0;color:var(--dim);
padding:8px 13px;font:inherit;font-size:11px;letter-spacing:.06em;cursor:pointer;min-height:34px}
.tabs button.on{background:#080a07;color:var(--acid)}
.tabwrap{min-height:112px}
.tabpane{display:none}.tabpane.on{display:block}
details{border:1px solid var(--line)}
details summary{padding:13px 16px;cursor:pointer;color:var(--dim);font-size:11px;letter-spacing:.12em;text-transform:uppercase}
details pre{margin:0;padding:16px;border-top:1px solid var(--line);white-space:pre-wrap;font-size:12px;color:#c3c9b6;max-height:440px;overflow:auto}
.note{border-left:2px solid var(--acid);padding:2px 0 2px 15px;margin:20px 0}
footer{padding:44px 0;color:var(--dim);font-size:12px}
footer .wrap{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.r{text-align:right}
.hidden{display:none!important}
@media(max-width:820px){.two{grid-template-columns:1fr;gap:28px}.stats{grid-template-columns:repeat(2,1fr)}
th{top:0}.m-hide{display:none}nav{gap:14px}nav a{font-size:12px}.hd{gap:14px}}
`;

export function layout({ title, desc, path, body, jsonLd = null, current = '', script = '' }) {
  const nav = [['skills', '/skills'], ['publishers', '/publishers'], ['packs', '/packs'], ['docs', '/docs']];
  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="https://oxde.ai${path}">
<link rel="alternate" type="text/markdown" href="https://oxde.ai${path === '/' ? '/index' : path}.md">
<meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(desc)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230c0e0b'/%3E%3Crect x='7' y='10' width='4' height='12' fill='%23c8ff4d'/%3E%3Crect x='14' y='10' width='4' height='12' fill='%23c8ff4d'/%3E%3Crect x='21' y='10' width='4' height='12' fill='%23c8ff4d' opacity='.35'/%3E%3C/svg%3E">
${jsonLd ? `<script type="application/ld+json">${JSON.stringify(jsonLd)}</script>` : ''}
<link rel="stylesheet" href="/style.css"></head><body>
<header><div class="wrap hd">
<a class="logo" href="/">oxde <b>agents</b></a>
<nav>${nav.map(([l, h]) => `<a href="${h}"${current === h ? ' aria-current="page"' : ''}>${l}</a>`).join('')}</nav>
</div></header>
${body}
<footer><div class="wrap">
<span>oxde agents · one score for every agent skill<br>sources: clawhub.ai · skills.sh</span>
<span class="r"><a href="/api/v1/skills">open API</a> · <a href="/llms.txt">llms.txt</a> · <a href="${path === '/' ? '/index' : esc(path)}.md">this page as markdown</a><br>curl any URL and you get markdown, not HTML</span>
</div></footer>
<script>
document.querySelectorAll('button[data-copy]').forEach(b=>b.addEventListener('click',async()=>{await navigator.clipboard.writeText(b.dataset.copy);const t=b.textContent;b.textContent='COPIED';setTimeout(()=>b.textContent=t,1100)}));
document.querySelectorAll('.tabs').forEach(g=>{const btns=[...g.querySelectorAll('button')];const panes=[...g.parentElement.querySelectorAll('.tabpane')];
btns.forEach((b,i)=>b.addEventListener('click',()=>{btns.forEach((x,j)=>{x.classList.toggle('on',j===i);panes[j]?.classList.toggle('on',j===i)})}))});
${script}
</script>
</body></html>`;
}

export const avatar = (p) => p?.image
  ? `<img class="av" src="${esc(p.image)}" alt="" loading="lazy" width="14" height="14">`
  : `<span class="av"></span>`;

export const byline = (p) => !p ? '<span class="by">unknown publisher</span>'
  : `${avatar(p)}<span>${esc(p.handle)}${p.official ? ' ✓' : ''}</span>`;

export const safetyPill = (s) => {
  const g = s.analysis?.safety?.grade;
  if (!g) return `<span class="pill" title="SKILL.md not fetched yet">UNSCANNED</span>`;
  const v = SAFETY[g];
  return `<span class="pill ${v.cls}" title="${esc(v.title)}${s.analysis.safety.flags.length ? ' — flags: ' + esc(s.analysis.safety.flags.join(', ')) : ''}">${v.label}</span>`;
};

export function pills(s, { max = 4 } = {}) {
  const out = [];
  if (s.ai) {
    // a warning must not be styled like an endorsement
    const tone = { risky: 'bad', 'low-quality': 'bad', 'promo-heavy': 'warn', niche: 'warn' }[s.ai.label] ?? '';
    out.push(`<span class="pill ai ${tone}" title="${esc(s.ai.note ?? '')}">AI: ${AI_LABEL[s.ai.label] ?? s.ai.label}</span>`);
  }
  out.push(safetyPill(s));
  if (s.analysis) {
    if (s.analysis.language.code !== 'en') out.push(`<span class="pill lang">${esc(s.analysis.language.label)}</span>`);
    out.push(s.analysis.apiNeeded.flag ? `<span class="pill">API KEY</span>` : `<span class="pill safe">NO KEY</span>`);
    if (s.analysis.promo) out.push(`<span class="pill review">PROMO</span>`);
  }
  return out.slice(0, max).join('');
}

export const bar = (r) => `<div class="bar ${r.tier === 'strong' ? 'good' : r.tier}" aria-hidden="true"><i style="width:${r.score}%"></i></div>`;

export function table(rows, { start = 1, filterable = false } = {}) {
  return `<table><thead><tr>
<th class="rk">#</th><th>skill</th><th class="m-hide">labels</th>
<th class="num m-hide">ctx</th><th class="num">installs</th><th class="num">score</th>
</tr></thead><tbody>${rows.map((s, i) => `<tr${filterable ? ` data-lang="${s.analysis?.language?.code ?? 'unknown'}" data-reg="${s.source.registry}" data-safe="${s.analysis?.safety?.grade ?? 'unscanned'}" data-q="${esc((s.name + ' ' + s.summary + ' ' + (s.publisher?.handle ?? '')).toLowerCase().slice(0, 200))}"` : ''}>
<td class="rk">${start + i}</td>
<td><div class="sk"><span class="ic">${iconFor(s)}</span><div><a href="/skills/${s.slug}"><b>${esc(s.name)}</b></a>
<div class="by">${registryChip(s.source.registry)} ${byline(s.publisher)}</div></div></div></td>
<td class="m-hide"><div class="tagrow">${pills(s, { max: 3 })}</div></td>
<td class="num m-hide">${tok(s.tokens)}</td>
<td class="num">${fmt(s.signals.downloads)}</td>
<td class="num">${bar(s.rating)}<span class="score">${s.rating.score}</span>${s.rating.coverage < 100 ? `<div class="cov" title="${s.rating.unknowns.join(' + ')} not measured yet — excluded from the score">${s.rating.coverage}% cov</div>` : ''}</td>
</tr>`).join('')}</tbody></table>`;
}
