// build.mjs — renders dist/ from data/oxde.db. Requires Node 24+ (node:sqlite).
//   ~/.nvm/versions/node/v24.18.0/bin/node build.mjs
// Pages exist only for gated skills; the full catalog lives in the API and llms-full.txt.
import { writeFileSync, mkdirSync, rmSync, statSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { WEIGHTS, MAX } from './rating/rating.mjs';
import { open } from './db/query.mjs';
import { TARGET, PER_PUBLISHER_CAP } from './analyze/gate.mjs';
import { layout, table, esc, fmt, tok, iconFor, registryChip, avatar, pills, safetyPill, CSS } from './site/html.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const DIST = join(ROOT, 'dist');
const SITE = 'https://oxde.ai';

const S = open(join(ROOT, 'data', 'oxde.db'));
const { counts, langCounts, registryCounts, gateReasons, meta } = S;
const RUNTIMES = JSON.parse(meta.runtimes ?? '[]');
const published = S.publishedSkills();
const everything = S.allSkills();
const byRank = published; // already score-ordered

// ——— install commands (registry-specific) ———
const installs = (s) => s.source.registry === 'skills.sh'
  ? [['skills CLI', `npx skills add ${s.source.url.split('/').slice(3, 5).join('/')}`],
     ['prompt', `Install skills from ${s.source.url.split('/').slice(3, 5).join('/')} with the skills CLI, then use "${s.slug}".`]]
  : [['OpenClaw / Hermes', `openclaw skills install ${s.slug}`],
     ['clawhub CLI', `npx clawhub@latest install ${s.slug}`],
     ['Claude Code', `curl -s https://clawhub.ai/api/v1/skills/${s.slug} \\\n  | jq -r .skill.description > ~/.claude/skills/${s.slug}/SKILL.md`]];

// ——— collections from FTS ———
const COLLECTIONS = [
  ['research', 'research & search', 'research OR news OR search OR arxiv OR academic'],
  ['email', 'email', 'email OR imap OR smtp OR gmail OR outlook'],
  ['browser', 'browser automation', 'browser OR playwright OR chrome OR scraping OR crawler'],
  ['documents', 'documents & PDF', 'pdf OR docx OR excel OR spreadsheet OR document'],
  ['crypto', 'crypto & trading', 'crypto OR trading OR solana OR wallet OR defi'],
  ['media', 'image, video & audio', 'image OR video OR audio OR voice OR music'],
  ['devtools', 'developer tools', 'github OR gitlab OR deploy OR docker OR kubernetes'],
  ['memory', 'memory & knowledge', 'memory OR knowledge OR ontology OR rag'],
].map(([slug, label, q]) => { try { return { slug, label, skills: S.search(q, 24) }; } catch { return { slug, label, skills: [] }; } })
  .filter(c => c.skills.length >= 5);

const PACKS = [
  { slug: 'research', name: 'Research', thesis: 'Find, read, and summarize the outside world.', q: 'research OR search OR news OR transcript' },
  { slug: 'ops', name: 'Ops', thesis: 'Email, calendar, notes — the boring loop.', q: 'email OR calendar OR notion OR obsidian OR task' },
  { slug: 'build', name: 'Build', thesis: 'Ship code: repos, deploys, reviews.', q: 'github OR gitlab OR deploy OR docker OR review' },
].map(p => { const skills = S.search(p.q, 5); return { ...p, skills, ctxCost: skills.reduce((a, s) => a + (s.tokens.count ?? 0), 0), unknown: skills.filter(s => s.tokens.count == null).length }; })
  .filter(p => p.skills.length >= 3);

// ——— fs ———
rmSync(DIST, { recursive: true, force: true });
const out = (p, c) => { const f = join(DIST, p); mkdirSync(dirname(f), { recursive: true }); writeFileSync(f, c); };
const page = (p, html, md) => {
  out(p === '/' ? 'index.html' : `${p.slice(1)}/index.html`, html);
  out(p === '/' ? 'index.md' : `${p.slice(1)}/index.md`, md);
};
out('style.css', CSS);

const mdHead = (t, p) => `# ${t}\n\n> oxde agents — one Agent Score for every agent skill, from data.\n> HTML ${SITE}${p} · JSON ${SITE}/api/v1/skills · method ${SITE}/docs.md\n`;
const mdRow = (s, i) => `| ${i + 1} | [${s.name}](${SITE}/skills/${s.slug}.md) | ${s.rating.score} | ${s.rating.coverage}% | ${s.source.registry} | ${s.publisher?.handle ?? '—'} | ${s.lang.code} | ${s.analysis?.safety?.grade ?? '—'} | ${tok(s.tokens)} | ${fmt(s.signals.downloads)} |`;
const mdTable = (r) => `| # | skill | score | cov | registry | publisher | lang | safety | ctx | installs |\n|--:|---|--:|--:|---|---|---|---|--:|--:|\n${r.map(mdRow).join('\n')}`;

// ——— skill page ———
function skillPage(s) {
  const r = s.rating, a = s.analysis, inst = installs(s);
  const AX = [
    ['adoption', r.parts.adoption, WEIGHTS.adoption, `${fmt(s.signals.downloads)} installs`],
    ['freshness', r.parts.freshness, WEIGHTS.freshness, s.signals.updatedAt ? `updated ${new Date(s.signals.updatedAt).toISOString().slice(0, 10)}` : 'release date unknown'],
    ['maintenance', r.parts.maintenance, WEIGHTS.maintenance, `${s.signals.versions} release${s.signals.versions === 1 ? '' : 's'}${s.signals.hasChangelog ? ' + changelog' : ''}`],
    ['token cost', r.parts.tokenCost, WEIGHTS.tokenCost, s.tokens.count == null ? 'not measured — SKILL.md not fetched yet' : `${fmt(s.tokens.count)} tokens loaded before it acts`],
    ['safety', r.parts.safety, WEIGHTS.safety, a?.safety ? (a.safety.flags.length ? a.safety.flags.join(', ') : 'scan clean') : 'not measured — SKILL.md not fetched yet'],
    ['publisher', r.parts.publisher, WEIGHTS.publisher, s.publisher ? `${s.publisher.handle}: ${fmt(s.publisher.totalDownloads)} installs${s.publisher.official ? ', official' : ''}` : 'unknown'],
  ];
  const related = S.search(s.name.split(/[\s-]+/).slice(0, 2).join(' OR ') || 'agent', 5).filter(x => x.slug !== s.slug).slice(0, 4);
  const body = `<div class="wrap">
<section>
<div class="two">
<div>
<div class="eyebrow">${registryChip(s.source.registry)}${s.version ? ` · v${esc(s.version)}` : ''} · ${esc(s.lang.label)} · #${s.gateRank} of ${fmt(counts.total)}</div>
<h1>${esc(s.name)}</h1>
<p class="lede">${esc(s.summary)}</p>
<p class="tagrow" style="margin-top:20px">${pills(s, { max: 5 })}</p>
${s.ai ? `<div class="note"><div class="eyebrow"><b>agent review</b></div>
<p style="margin:8px 0 0">${esc(s.ai.note)}</p>
<div class="eyebrow" style="margin-top:8px">quality ${s.ai.quality}/5 · agent-fit ${s.ai.agentFit}/5 — reviews label a skill, they never move its score</div></div>` : ''}
<div style="margin-top:34px"><div class="eyebrow">agent score</div>
<div style="display:flex;align-items:baseline;gap:12px;margin-top:6px"><span style="font-size:52px;letter-spacing:-.05em;color:var(--acid);line-height:1">${r.score}</span><span class="eyebrow">/ 100 · ${r.tier} · <b>${r.coverage}% coverage</b>${r.unknowns.length ? ` — ${r.unknowns.length === 1 ? '1 axis' : `${r.unknowns.length} axes`} not measured, so excluded` : ''}</span></div>
<table class="axes" style="margin-top:16px">
${AX.map(([n, v, m, note]) => v == null
    ? `<tr class="off"><td>${n}<div class="lab">${esc(note)}</div></td><td style="width:110px"><div class="bar" style="max-width:100px"></div></td><td class="num" style="width:64px">—<span class="lab">/${m}</span></td></tr>`
    : `<tr><td>${n}<div class="lab">${esc(note)}</div></td><td style="width:110px"><div class="bar" style="max-width:100px"><i style="width:${(v / m) * 100}%"></i></div></td><td class="num" style="width:64px">${v.toFixed(1)}<span class="lab">/${m}</span></td></tr>`).join('')}
</table></div>
</div>
<div class="side">
<div class="eyebrow">install</div>
<div class="tabs" style="margin-top:10px">${inst.map(([t], i) => `<button type="button" class="${i === 0 ? 'on' : ''}">${esc(t)}</button>`).join('')}</div>
<div class="tabwrap">${inst.map(([, cmd], i) => `<div class="tabpane ${i === 0 ? 'on' : ''}"><pre class="term">${esc(cmd)}</pre>
<p><button class="pill" style="height:30px;padding:0 12px;cursor:pointer;background:transparent" data-copy="${esc(cmd)}">COPY</button></p></div>`).join('')}</div>
<div class="eyebrow" style="margin-top:6px">${s.source.registry === 'skills.sh' ? `works with all ${RUNTIMES.length} runtimes the skills CLI supports` : 'OpenClaw-native; copy SKILL.md for Claude Code'}</div>
<div class="eyebrow" style="margin-top:18px">publisher</div>
<div class="sk" style="margin:10px 0 18px">${avatar(s.publisher)}<div>${s.publisher
      ? `<a href="/publishers#${esc(s.publisher.handle)}"><b>${esc(s.publisher.displayName)}</b></a>${s.publisher.official ? ' ✓' : ''}
<div class="by">${fmt(s.publisher.totalDownloads)} installs · ${s.publisher.skillCount} skills · ${s.publisher.registries.map(registryChip).join(' ')}</div>`
      : '<span class="by">unknown</span>'}</div></div>
<table class="kv">
<tr><td>installs</td><td>${fmt(s.signals.downloads)}</td></tr>
<tr><td>stars</td><td>${fmt(s.signals.stars)}</td></tr>
<tr><td>context cost</td><td>${tok(s.tokens)} tok</td></tr>
<tr><td>language</td><td>${esc(s.lang.label)}</td></tr>
<tr><td>safety</td><td>${safetyPill(s)}</td></tr>
<tr><td>source</td><td>${s.source.resolved ? `<a href="${esc(s.source.url)}" rel="noopener">${s.source.registry} ↗</a>` : esc(s.source.registry)}</td></tr>
<tr><td>json</td><td><a href="/api/v1/skills/${s.slug}">api ↗</a></td></tr>
</table>
</div>
</div>
</section>
${s.skillMd ? `<section class="tight">
<div class="eyebrow">what your agent loads · ${tok(s.tokens)} tokens</div>
<details style="margin-top:12px"><summary>read SKILL.md — untrusted content, shown verbatim</summary><pre>${esc(s.skillMd.slice(0, 14_000))}${s.skillMd.length > 14_000 ? '\n… truncated' : ''}</pre></details>
</section>` : ''}
${related.length ? `<section class="tight"><div class="eyebrow">// related</div><div style="margin-top:16px">${table(related)}</div></section>` : ''}
</div>`;
  const md = `${mdHead(`${s.name} — Agent Score ${r.score}/100`, `/skills/${s.slug}`)}
**${r.score}/100 (${r.tier})** · coverage ${r.coverage}% · ${s.source.registry} · ${s.lang.label} · safety ${a?.safety?.grade ?? 'unscanned'}

${s.summary}

- publisher: ${s.publisher ? `${s.publisher.handle}${s.publisher.official ? ' (official)' : ''}, ${fmt(s.publisher.totalDownloads)} installs across ${s.publisher.skillCount} skills` : 'unknown'}
- install: \`${inst[0][1].split('\n')[0]}\`
- context cost: ${tok(s.tokens)} tokens · installs: ${fmt(s.signals.downloads)} · releases: ${s.signals.versions}
- score axes: ${Object.entries(r.parts).map(([k, v]) => `${k} ${v == null ? 'not measured' : `${v.toFixed(1)}/${WEIGHTS[k]}`}`).join(' · ')}
${a ? `- labels: ${a.apiNeeded.flag ? 'API key needed' : 'no API key'}${a.network ? ', network' : ''}${a.promo ? ', PROMO' : ''}` : ''}
${s.ai ? `- agent review: ${s.ai.label} — ${s.ai.note} (quality ${s.ai.quality}/5, agent-fit ${s.ai.agentFit}/5)` : ''}
- source: ${s.source.url}
- JSON: ${SITE}/api/v1/skills/${s.slug}
`;
  page(`/skills/${s.slug}`, layout({
    title: `${s.name} — Agent Score ${r.score}/100 | oxde agents`,
    desc: s.summary.slice(0, 150), path: `/skills/${s.slug}`, body, current: '/skills',
    jsonLd: {
      '@context': 'https://schema.org', '@type': 'SoftwareApplication', name: s.name,
      applicationCategory: 'DeveloperApplication', operatingSystem: 'Any', description: s.summary,
      url: `${SITE}/skills/${s.slug}`, inLanguage: s.lang.code,
      ...(s.publisher ? { author: { '@type': s.publisher.official ? 'Organization' : 'Person', name: s.publisher.displayName } } : {}),
      aggregateRating: { '@type': 'AggregateRating', ratingValue: r.score, bestRating: 100, ratingCount: 1 },
    },
  }), md);
}

// ——— home ———
{
  const top = byRank.slice(0, 12);
  const body = `<div class="wrap">
<section>
<div class="eyebrow">// the agent skills index</div>
<h1>Every agent skill,<br><em>scored on data.</em></h1>
<p class="lede">${fmt(counts.total)} skills indexed from ClawHub and skills.sh. Each gets one number from what can be measured — installs, freshness, maintenance, context cost, a safety scan of the SKILL.md, and the publisher's record. ${fmt(counts.published)} earn a page; the rest stay searchable in the API. Agents read this site as markdown.</p>
<div class="stats">
<div><div class="n">${fmt(counts.total)}</div><div class="k">skills indexed</div></div>
<div><div class="n">${fmt(counts.published)}</div><div class="k">pass the gate</div></div>
<div><div class="n">${fmt(counts.scanned)}</div><div class="k">SKILL.md scanned</div></div>
<div><div class="n">${counts.risky}</div><div class="k">flagged risky</div></div>
</div>
</section>
<section class="tight">
<div class="eyebrow">// top 12 by agent score</div>
<div style="margin-top:20px">${table(top)}</div>
<p style="margin-top:20px"><a href="/skills"><b>all ${fmt(counts.published)} ranked skills →</b></a></p>
</section>
<section class="tight">
<div class="eyebrow">// for agents</div>
<h2>This site is an API.</h2>
<pre class="term" style="margin-top:18px">$ curl oxde.ai/skills/${top[0].slug}
<span class="c"># → markdown. no HTML unless you ask for it.</span>
$ curl oxde.ai/api/v1/skills
<span class="c"># → ${fmt(counts.total)} skills, scored, JSON, no auth</span></pre>
<p class="lede">Every page has a <code>.md</code> twin. <a href="/llms.txt">llms.txt</a> · <a href="/api/v1/meta">meta</a> · <a href="/docs">how the score works</a></p>
</section>
</div>`;
  page('/', layout({
    title: 'oxde agents — every AI agent skill, scored on data',
    desc: `${fmt(counts.total)} AI agent skills from ClawHub and skills.sh with one Agent Score each: installs, freshness, maintenance, context cost, safety scan, publisher record.`,
    path: '/', body, current: '/',
    jsonLd: { '@context': 'https://schema.org', '@type': 'ItemList', name: 'Best AI skills for agents', itemListElement: top.map((s, i) => ({ '@type': 'ListItem', position: i + 1, url: `${SITE}/skills/${s.slug}` })) },
  }), `${mdHead('oxde agents — every AI agent skill, scored on data', '/')}
${fmt(counts.total)} skills indexed (clawhub ${fmt(registryCounts.clawhub ?? 0)}, skills.sh ${registryCounts['skills.sh'] ?? 0}); ${fmt(counts.published)} have pages, all are in the API.
Agent Score 0–100 = adoption 25 · freshness 15 · maintenance 10 · token cost 15 · safety 20 · publisher 15. Unmeasured axes are excluded and reported as coverage.

## Top 12
${mdTable(top)}

## Endpoints
- ${SITE}/api/v1/skills — full ${fmt(counts.total)}-skill catalog, JSON, no auth
- ${SITE}/api/v1/skills/{slug} — score breakdown, labels, install commands
- ${SITE}/api/v1/publishers — publisher table
- ${SITE}/llms-full.txt — whole catalog as markdown
`);
}

// ——— /skills ———
{
  const rows = byRank;
  const langs = [['all', 'all languages'], ...Object.entries(langCounts).filter(([, c]) => c > 5)
    .map(([c]) => [c, { en: 'English', zh: '中文', 'zh-en': '中文 + EN', ja: '日本語', ko: '한국어', ru: 'Русский', unknown: 'unknown' }[c] ?? c])];
  const shown = rows.length;
  const body = `<div class="wrap">
<section class="tight">
<div class="eyebrow">// ${fmt(counts.published)} skills with pages · ${fmt(counts.total)} indexed</div>
<h1>The index.</h1>
<input class="search" id="q" type="search" placeholder="filter by name, summary, publisher…" autocomplete="off">
<div class="filters" data-group="lang">${langs.map(([c, l], i) => `<button data-v="${c}" class="${i === 0 ? 'on' : ''}">${l}${c !== 'all' ? ` ${rows.filter(r => r.lang.code === c).length}` : ''}</button>`).join('')}</div>
<div class="filters" data-group="reg"><button data-v="all" class="on">both registries</button><button data-v="clawhub">clawhub</button><button data-v="skills.sh">skills.sh</button></div>
<div class="filters" data-group="safe"><button data-v="all" class="on">any safety</button><button data-v="safe">safe only</button><button data-v="review">needs review</button></div>
<p class="eyebrow" id="count" style="margin-top:14px"></p>
</section>
<section class="tight">${table(rows, { filterable: true })}
<p class="eyebrow" style="margin-top:22px">the other ${fmt(counts.total - counts.published)} indexed skills are in the <a href="/api/v1/skills">JSON API</a> and <a href="/llms-full.txt">llms-full.txt</a> — see <a href="/docs">how the gate works</a>.</p>
</section></div>`;
  const script = `(()=>{const rows=[...document.querySelectorAll('tbody tr')];const st={lang:'all',reg:'all',safe:'all',q:''};
const cnt=document.getElementById('count');
function apply(){let n=0;for(const r of rows){const ok=(st.lang==='all'||r.dataset.lang===st.lang)&&(st.reg==='all'||r.dataset.reg===st.reg)&&(st.safe==='all'||r.dataset.safe===st.safe)&&(!st.q||r.dataset.q.includes(st.q));r.classList.toggle('hidden',!ok);if(ok)n++}
cnt.textContent=n+' of ${shown} shown';}
document.querySelectorAll('.filters').forEach(g=>g.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{g.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));st[g.dataset.group]=b.dataset.v;apply()})));
document.getElementById('q').addEventListener('input',e=>{st.q=e.target.value.toLowerCase().trim();apply()});apply()})();`;
  page('/skills', layout({ title: `All ${counts.published} ranked AI agent skills | oxde agents`, desc: 'Every AI agent skill worth a page, ranked by Agent Score and filterable by language, registry and safety.', path: '/skills', body, current: '/skills', script }),
    `${mdHead(`${counts.published} ranked skills`, '/skills')}\n${mdTable(rows.slice(0, 500))}\n\nFull ${counts.total}-skill catalog: ${SITE}/api/v1/skills`);
}

// ——— /publishers ———
{
  const top = S.topPublishers(80);
  const body = `<div class="wrap">
<section class="tight">
<div class="eyebrow">// ${fmt(counts.publishers)} publishers</div>
<h1>Who ships them.</h1>
<p class="lede">Publisher record is 15 points of the Agent Score. Official orgs — verified makers on skills.sh — get full marks; everyone else is log-scaled by portfolio installs. No publisher may occupy more than ${PER_PUBLISHER_CAP} pages, so vendors who mass-publish wrappers can't flood the index.</p>
</section>
<section class="tight"><table><thead><tr><th class="rk">#</th><th>publisher</th><th>ships on</th><th class="num">skills</th><th class="num">installs</th><th class="m-hide">status</th></tr></thead><tbody>
${top.map((p, i) => `<tr id="${esc(p.handle)}"><td class="rk">${i + 1}</td>
<td><div class="sk">${avatar(p)}<div><b>${esc(p.displayName)}</b><div class="by">@${esc(p.handle)}</div></div></div></td>
<td><div class="tagrow">${p.registries.map(registryChip).join(' ')}</div></td>
<td class="num">${p.skillCount}</td><td class="num">${fmt(p.totalDownloads)}</td>
<td class="m-hide">${p.official ? '<span class="pill safe">OFFICIAL</span>' : '<span class="pill">COMMUNITY</span>'}</td></tr>`).join('')}
</tbody></table></section></div>`;
  page('/publishers', layout({ title: 'Skill publishers ranked | oxde agents', desc: 'Who publishes AI agent skills, which registries they ship on, ranked by installs.', path: '/publishers', body, current: '/publishers' }),
    `${mdHead('Publishers', '/publishers')}\n| # | publisher | registries | skills | installs | official |\n|--:|---|---|--:|--:|---|\n${top.map((p, i) => `| ${i + 1} | ${p.displayName} (@${p.handle}) | ${p.registries.join(', ')} | ${p.skillCount} | ${fmt(p.totalDownloads)} | ${p.official ? '✓' : ''} |`).join('\n')}`);
  out('api/v1/publishers.json', JSON.stringify({ generatedAt: meta.generatedAt, publishers: top }, null, 1));
}

// ——— /packs ———
{
  const body = `<div class="wrap">
<section class="tight"><div class="eyebrow">// packs</div><h1>One job. One paste.</h1>
<p class="lede">Top-scoring skills for a job, with the combined context cost stated up front.</p></section>
${PACKS.map(p => `<section class="tight"><div class="eyebrow">// ${esc(p.name.toLowerCase())} · ${fmt(p.ctxCost)}${p.unknown ? '+' : ''} tokens combined</div>
<h2>${esc(p.name)}</h2><p class="lede">${esc(p.thesis)}</p>
<div style="margin-top:20px">${table(p.skills)}</div>
<pre class="term" style="margin-top:18px">${p.skills.map(s => esc(installs(s)[0][1].split('\n')[0])).join('\n')}</pre>
<p><button class="pill" style="height:30px;padding:0 12px;cursor:pointer;background:transparent" data-copy="${esc(p.skills.map(s => installs(s)[0][1].split('\n')[0]).join(' && '))}">COPY ALL ${p.skills.length}</button></p></section>`).join('')}
</div>`;
  page('/packs', layout({ title: 'Skill packs | oxde agents', desc: 'Curated AI agent skill bundles with combined context cost stated up front.', path: '/packs', body, current: '/packs' }),
    `${mdHead('Packs', '/packs')}\n${PACKS.map(p => `## ${p.name}\n${p.thesis} — ${fmt(p.ctxCost)}${p.unknown ? '+' : ''} tokens\n\n${mdTable(p.skills)}`).join('\n\n')}`);
}

// ——— /docs ———
{
  const gr = Object.entries(gateReasons).filter(([k]) => k !== 'published').sort((a, b) => b[1] - a[1]);
  const body = `<div class="wrap">
<section class="tight"><div class="eyebrow">// docs</div><h1>How the score works.</h1>
<p class="lede">One number, 0–100, from data. The weights below are the literal constants in a pure scoring function with golden tests — changing one breaks the build until it's deliberately blessed.</p></section>
<section class="tight"><div class="eyebrow">// agent score · 100 points</div>
<table class="axes" style="margin-top:16px">
<tr><td>adoption<div class="lab">log-scaled installs against the catalog leader</div></td><td class="num">${WEIGHTS.adoption}</td></tr>
<tr><td>freshness<div class="lab">full marks inside 7 days, exponential decay after</div></td><td class="num">${WEIGHTS.freshness}</td></tr>
<tr><td>maintenance<div class="lab">releases shipped (6+ = full) plus a changelog</div></td><td class="num">${WEIGHTS.maintenance}</td></tr>
<tr><td>token cost<div class="lab">what SKILL.md spends from your context before the skill acts: ≤400 tok full marks, ≥6k near zero</div></td><td class="num">${WEIGHTS.tokenCost}</td></tr>
<tr><td>safety<div class="lab">static scan of SKILL.md — SAFE (clean) / REVIEW (agent directives or promotion) / RISKY (dangerous shell, possible exfiltration, credential harvesting, instruction-override attempts)</div></td><td class="num">${WEIGHTS.safety}</td></tr>
<tr><td>publisher<div class="lab">official org = full marks; otherwise log-scaled portfolio installs</div></td><td class="num">${WEIGHTS.publisher}</td></tr>
</table>
<div class="note" style="margin-top:24px"><b>Unmeasured axes are excluded, not guessed.</b> If a SKILL.md hasn't been fetched, token cost and safety are left out of the arithmetic entirely and the page reports <b>coverage</b> instead. A 90 at 65% coverage is a different claim from a 90 at 100%, and the site says so rather than hiding it behind a plausible-looking number.</div></section>
<section class="tight"><div class="eyebrow">// the gate</div><h2>${fmt(counts.total)} indexed. ${fmt(counts.published)} get a page.</h2>
<p class="lede">Publishing tens of thousands of thin auto-generated pages helps nobody and buries the good ones. Everything is indexed, searchable and in the API; only skills that clear the gate get a page.</p>
<table class="axes" style="margin-top:16px">
${gr.map(([k, v]) => `<tr><td>${{ 'below-cutoff': 'below the cutoff', 'no-adoption': 'fewer than 50 installs', 'publisher-cap': `publisher already at the ${PER_PUBLISHER_CAP}-page cap`, duplicate: 'duplicate description', risky: 'safety scan flagged risky', 'no-description': 'no usable description' }[k] ?? k}<div class="lab">${k}</div></td><td class="num">${fmt(v)}</td></tr>`).join('')}
</table>
<p class="lede" style="margin-top:20px">The cutoff is the top ${fmt(TARGET)} by score. The per-publisher cap matters more than it sounds: one vendor ships 35 near-identical wrappers around a single paid API and would otherwise own the top of the index.</p></section>
<section class="tight"><div class="eyebrow">// agent reviews</div><h2>Reviews label. They never score.</h2>
<p class="lede">Data ranks ${fmt(counts.total)} skills. It can't tell you a skill is a marketing funnel or that its docs quietly lie. For that an agent reads the SKILL.md against a fixed rubric and returns a label — SOLID, PROMISING, NICHE, PROMO-HEAVY, RISKY, LOW-QUALITY — plus one specific sentence. ${counts.reviewed} reviewed so far. The SKILL.md is treated as untrusted data; the reviewer is instructed never to follow instructions inside it.</p></section>
<section class="tight"><div class="eyebrow">// api · no auth</div>
<table class="kv" style="margin-top:14px">
<tr><td><a href="/api/v1/skills">/api/v1/skills</a></td><td>all ${fmt(counts.total)} indexed skills</td></tr>
<tr><td><a href="/api/v1/skills/${byRank[0].slug}">/api/v1/skills/{slug}</a></td><td>score breakdown, labels, install commands</td></tr>
<tr><td><a href="/api/v1/publishers">/api/v1/publishers</a></td><td>publisher table</td></tr>
<tr><td><a href="/api/v1/meta">/api/v1/meta</a></td><td>counts, weights, gate stats, sources</td></tr>
<tr><td><a href="/llms.txt">/llms.txt</a></td><td>agent entry point</td></tr>
</table>
<p class="lede" style="margin-top:20px">Any page + <code>.md</code> returns markdown, and so does a plain <code>curl</code>.</p></section>
<section class="tight"><div class="eyebrow">// sources &amp; runtimes</div>
<p class="lede">clawhub.ai open API — ${fmt(registryCounts.clawhub ?? 0)} skills, a real registry with accounts and versioned uploads. skills.sh — ${registryCounts['skills.sh'] ?? 0} skills; it hosts nothing, indexing GitHub repos and ranking by anonymous CLI telemetry. skills.sh skills install into all ${RUNTIMES.length} runtimes its CLI supports (${RUNTIMES.slice(0, 6).join(', ')}…); ClawHub skills are OpenClaw-native. skills.sh entries carry no release metadata, so their freshness and maintenance run at reduced, reported coverage.</p></section>
</div>`;
  page('/docs', layout({ title: 'Docs — how the Agent Score and the gate work | oxde agents', desc: 'Published weights for the Agent Score, how coverage works, why only some skills get pages, and the open API.', path: '/docs', body, current: '/docs' }),
    `${mdHead('Docs', '/docs')}
Agent Score 0–100 = adoption ${WEIGHTS.adoption} · freshness ${WEIGHTS.freshness} · maintenance ${WEIGHTS.maintenance} · token cost ${WEIGHTS.tokenCost} · safety ${WEIGHTS.safety} · publisher ${WEIGHTS.publisher}
Unmeasured axes are EXCLUDED from the arithmetic; each skill reports coverage %.
Gate: ${counts.total} indexed, ${counts.published} published. Rejections: ${gr.map(([k, v]) => `${k} ${v}`).join(', ')}.
Agent reviews label a skill; they never move the score.
API (no auth): /api/v1/skills · /api/v1/skills/{slug} · /api/v1/publishers · /api/v1/meta`);
}

// ——— API (all skills, published or not) ———
const apiSkill = (s) => ({
  slug: s.slug, name: s.name, summary: s.summary, topics: s.topics, version: s.version,
  score: { value: s.rating.score, max: MAX, tier: s.rating.tier, coverage: s.rating.coverage, parts: s.rating.parts, unmeasured: s.rating.unknowns },
  language: s.lang,
  labels: s.analysis ? { safety: s.analysis.safety, apiNeeded: s.analysis.apiNeeded, network: s.analysis.network, promo: s.analysis.promo, noCode: s.analysis.noCode } : null,
  agentReview: s.ai,
  tokens: s.tokens, signals: s.signals,
  registry: { name: s.source.registry, url: s.source.url, resolved: s.source.resolved },
  publisher: s.publisher ? { handle: s.publisher.handle, displayName: s.publisher.displayName, official: s.publisher.official, totalDownloads: s.publisher.totalDownloads, skillCount: s.publisher.skillCount, registries: s.publisher.registries } : null,
  install: Object.fromEntries(installs(s).map(([k, v]) => [k.toLowerCase().replace(/[^a-z]+/g, '-').replace(/^-|-$/g, ''), v])),
  page: s.published ? `${SITE}/skills/${s.slug}` : null,
  gate: { published: s.published, reason: s.gateReason, rank: s.gateRank },
  urls: { json: `${SITE}/api/v1/skills/${s.slug}`, ...(s.published ? { html: `${SITE}/skills/${s.slug}`, md: `${SITE}/skills/${s.slug}.md`, badge: `${SITE}/b/${s.slug}.svg` } : {}) },
});
out('api/v1/skills.json', JSON.stringify({
  generatedAt: meta.generatedAt, count: counts.total, published: counts.published, method: `${SITE}/docs`,
  skills: everything.map(s => ({ slug: s.slug, name: s.name, score: s.rating.score, coverage: s.rating.coverage, tier: s.rating.tier, registry: s.source.registry, publisher: s.publisher?.handle ?? null, language: s.lang.code, safety: s.analysis?.safety?.grade ?? null, tokens: s.tokens.count, installs: s.signals.downloads, published: s.published, url: `${SITE}/api/v1/skills/${s.slug}` })),
}));
for (const s of published) out(`api/v1/skills/${s.slug}.json`, JSON.stringify(apiSkill(s), null, 1));
out('api/v1/meta.json', JSON.stringify({
  name: 'oxde agents', generatedAt: meta.generatedAt,
  counts: { ...counts, byRegistry: registryCounts, byLanguage: langCounts },
  gate: { target: TARGET, perPublisherCap: PER_PUBLISHER_CAP, reasons: gateReasons },
  weights: WEIGHTS, max: MAX, note: 'Unmeasured axes are excluded from the score; each skill reports coverage %.',
  runtimes: RUNTIMES,
  endpoints: ['/api/v1/skills', '/api/v1/skills/{slug}', '/api/v1/publishers', '/api/v1/meta'],
  sources: JSON.parse(meta.sources ?? '[]'),
}, null, 1));

// ——— badges (published only) ———
const BAND = (r) => r.score >= 75 ? '#c8ff4d' : r.score >= 55 ? '#a8d64a' : r.score >= 35 ? '#ffc66d' : '#8d967f';
for (const s of published) {
  const t = `${s.rating.score}/100`, w = 14 + t.length * 7.2;
  out(`b/${s.slug}.svg`, `<svg xmlns="http://www.w3.org/2000/svg" width="${Math.round(90 + w)}" height="24" role="img" aria-label="agent score ${t}">
<rect width="90" height="24" fill="#0c0e0b"/><rect x="90" width="${Math.round(w)}" height="24" fill="#131610"/>
<text x="8" y="16" font-family="monospace" font-size="11" fill="#8d967f">AGENT SCORE</text>
<text x="97" y="16" font-family="monospace" font-size="11" font-weight="bold" fill="${BAND(s.rating)}">${t}</text></svg>`);
}

// ——— agent surfaces ———
out('llms.txt', `# oxde agents

> ${fmt(counts.total)} AI agent skills indexed from clawhub.ai and skills.sh, each scored 0–100 from data: adoption, freshness, maintenance, context cost, safety scan of SKILL.md, publisher record. Unmeasured axes are excluded and reported as coverage. ${fmt(counts.published)} skills have pages; all ${fmt(counts.total)} are in the API.

Every HTML page has a markdown twin at the same path + .md — or just curl any URL without an HTML Accept header.

## Core
- [Ranked index](${SITE}/skills.md)
- [Method, gate and weights](${SITE}/docs.md)
- [Publishers](${SITE}/publishers.md)
- [Packs](${SITE}/packs.md)
- [Full catalog, markdown](${SITE}/llms-full.txt)
- [Full catalog, JSON — no auth](${SITE}/api/v1/skills)
- [Counts, weights, gate stats](${SITE}/api/v1/meta)

## Languages
${Object.entries(langCounts).filter(([, c]) => c > 5).map(([c, n]) => `- ${c}: ${fmt(n)} skills`).join('\n')}

## Top 20
${byRank.slice(0, 20).map((s, i) => `${i + 1}. [${s.name} — ${s.rating.score}/100](${SITE}/skills/${s.slug}.md)`).join('\n')}
`);
out('llms-full.txt', `# oxde agents — full catalog (${fmt(counts.total)} skills, ${String(meta.generatedAt).slice(0, 10)})\n\nAgent Score 0–100 from data; coverage % states how much of the rubric was measurable. Method: ${SITE}/docs.md\n\n${mdTable(everything)}\n`);
out('robots.txt', `User-agent: *\nAllow: /\nSitemap: ${SITE}/sitemap.xml\n# agents: append .md to any page, or just curl it — index at ${SITE}/llms.txt\n`);
const urls = ['/', '/skills', '/publishers', '/packs', '/docs', ...published.map(s => `/skills/${s.slug}`)];
out('sitemap.xml', `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map(u => `<url><loc>${SITE}${u}</loc></url>`).join('\n')}\n</urlset>`);

for (const s of published) skillPage(s);

// Ship the database so agents can query the whole catalog locally — but slim.
// The working DB stores every SKILL.md twice (row + FTS index) and is ~93MB;
// dropping the bodies keeps search over name/summary and lands around a tenth of that.
{
  const slimPath = join(DIST, 'oxde.db');
  const slim = new DatabaseSync(slimPath);
  slim.exec(`PRAGMA journal_mode = OFF;
    CREATE TABLE publishers (handle TEXT PRIMARY KEY, display_name TEXT, image TEXT, skill_count INTEGER, total_downloads INTEGER, total_stars INTEGER, official INTEGER, registries TEXT);
    CREATE TABLE skills (slug TEXT PRIMARY KEY, name TEXT, summary TEXT, topics TEXT, registry TEXT, source_url TEXT, owner TEXT,
      downloads INTEGER, stars INTEGER, versions INTEGER, updated_at INTEGER, tokens INTEGER,
      lang_code TEXT, safety_grade TEXT, safety_flags TEXT, api_needed INTEGER, promo INTEGER,
      score INTEGER, tier TEXT, coverage INTEGER, ai_label TEXT, ai_note TEXT, published INTEGER, gate_reason TEXT);
    CREATE INDEX idx_score ON skills(score DESC);
    CREATE VIRTUAL TABLE skills_fts USING fts5(slug UNINDEXED, name, summary, tokenize='porter unicode61');`);
  const ins = slim.prepare(`INSERT INTO skills VALUES ($slug,$name,$summary,$topics,$registry,$source_url,$owner,$downloads,$stars,$versions,$updated_at,$tokens,$lang_code,$safety_grade,$safety_flags,$api_needed,$promo,$score,$tier,$coverage,$ai_label,$ai_note,$published,$gate_reason)`);
  const insF = slim.prepare('INSERT INTO skills_fts VALUES ($slug,$name,$summary)');
  const insP = slim.prepare('INSERT INTO publishers VALUES ($h,$d,$i,$sc,$td,$ts,$o,$r)');
  slim.exec('BEGIN');
  for (const p of S.publishers.values()) insP.run({ $h: p.handle, $d: p.displayName, $i: p.image, $sc: p.skillCount, $td: p.totalDownloads, $ts: p.totalStars, $o: p.official ? 1 : 0, $r: JSON.stringify(p.registries) });
  for (const s of everything) {
    ins.run({
      $slug: s.slug, $name: s.name, $summary: s.summary, $topics: JSON.stringify(s.topics),
      $registry: s.source.registry, $source_url: s.source.url, $owner: s.publisher?.handle ?? null,
      $downloads: s.signals.downloads, $stars: s.signals.stars, $versions: s.signals.versions,
      $updated_at: s.signals.updatedAt, $tokens: s.tokens.count, $lang_code: s.lang.code,
      $safety_grade: s.analysis?.safety?.grade ?? null, $safety_flags: JSON.stringify(s.analysis?.safety?.flags ?? []),
      $api_needed: s.analysis ? (s.analysis.apiNeeded.flag ? 1 : 0) : null,
      $promo: s.analysis ? (s.analysis.promo ? 1 : 0) : null,
      $score: s.rating.score, $tier: s.rating.tier, $coverage: s.rating.coverage,
      $ai_label: s.ai?.label ?? null, $ai_note: s.ai?.note ?? null,
      $published: s.published ? 1 : 0, $gate_reason: s.gateReason,
    });
    insF.run({ $slug: s.slug, $name: s.name, $summary: s.summary });
  }
  slim.exec('COMMIT'); slim.exec('VACUUM'); slim.close();
}

console.log(`build: ${urls.length} pages from ${fmt(counts.total)} indexed skills · ${fmt(counts.published)} published · ${counts.scanned} scanned · ${counts.risky} risky · ${counts.publishers} publishers`);
console.log(`shipped db: ${(statSync(join(DIST, 'oxde.db')).size / 1048576).toFixed(1)} MB (slim — SKILL.md bodies excluded)`);
S.close();
