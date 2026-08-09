// db/build-db.mjs — fold every raw source into one SQLite file with FTS5 search.
// Requires Node 24+ (node:sqlite is built in; zero dependencies).
//   ~/.nvm/versions/node/v24.18.0/bin/node db/build-db.mjs
//
// This is the single source of truth the site builds from. It stores raw signals,
// derived analysis, the Agent Score, and the publish gate decision for every skill.
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { agentScore } from '../rating/rating.mjs';
import { analyzeSkillMd, detectLanguage } from '../analyze/heuristics.mjs';
import { gate } from '../analyze/gate.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DB_PATH = join(ROOT, 'data', 'oxde.db');
const read = (p, d = null) => existsSync(p) ? JSON.parse(readFileSync(p, 'utf8')) : d;

const catalog = read(join(ROOT, 'data', 'catalog.json'));
const skillssh = read(join(ROOT, 'data', 'skillssh.json'), { skills: [], officialOrgs: [], agents: [], topics: [] });
const aiReviews = read(join(ROOT, 'analyze', 'llm-labels.json'), {});
const detailsDir = join(ROOT, 'data', 'details');

rmSync(DB_PATH, { force: true });
mkdirSync(dirname(DB_PATH), { recursive: true });
const db = new DatabaseSync(DB_PATH);
db.exec('PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL;');

db.exec(`
CREATE TABLE publishers (
  handle TEXT PRIMARY KEY, display_name TEXT, image TEXT,
  skill_count INTEGER DEFAULT 0, total_downloads INTEGER DEFAULT 0, total_stars INTEGER DEFAULT 0,
  official INTEGER DEFAULT 0, registries TEXT
);
CREATE TABLE skills (
  slug TEXT PRIMARY KEY, name TEXT, summary TEXT, topics TEXT, version TEXT, icon TEXT,
  registry TEXT, source_url TEXT, source_resolved INTEGER, owner TEXT,
  downloads INTEGER, stars INTEGER, versions INTEGER, has_changelog INTEGER,
  created_at INTEGER, updated_at INTEGER, license TEXT,
  tokens INTEGER, token_method TEXT,
  lang_code TEXT, lang_label TEXT,
  safety_grade TEXT, safety_flags TEXT,
  api_needed INTEGER, api_env TEXT, network INTEGER, promo INTEGER, no_code INTEGER,
  skill_md TEXT,
  score INTEGER, tier TEXT, coverage INTEGER, score_parts TEXT, unmeasured TEXT,
  ai_label TEXT, ai_note TEXT, ai_quality INTEGER, ai_fit INTEGER,
  published INTEGER, gate_reason TEXT, gate_rank INTEGER
);
CREATE INDEX idx_score ON skills(score DESC);
CREATE INDEX idx_published ON skills(published, score DESC);
CREATE INDEX idx_lang ON skills(lang_code);
CREATE INDEX idx_registry ON skills(registry);
CREATE INDEX idx_owner ON skills(owner);
CREATE VIRTUAL TABLE skills_fts USING fts5(slug UNINDEXED, name, summary, skill_md, tokenize='porter unicode61');
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
`);

// ——— details ———
const details = new Map();
if (existsSync(detailsDir)) for (const f of readdirSync(detailsDir)) {
  try { details.set(f.replace(/\.json$/, ''), JSON.parse(readFileSync(join(detailsDir, f), 'utf8'))); } catch { /* partial file mid-write */ }
}

// ——— publishers ———
const officialSet = new Set(skillssh.officialOrgs.map(o => o.org.toLowerCase()));
const pubs = new Map();
const touchPub = (handle, { displayName, image, downloads = 0, stars = 0, registry }) => {
  const p = pubs.get(handle) ?? {
    handle, displayName: displayName ?? handle, image: image ?? null,
    skillCount: 0, totalDownloads: 0, totalStars: 0,
    official: officialSet.has(handle.toLowerCase()) ? 1 : 0, registries: new Set(),
  };
  p.skillCount++; p.totalDownloads += downloads; p.totalStars += stars;
  p.registries.add(registry);
  if (displayName && p.displayName === handle) p.displayName = displayName;
  if (image && !p.image) p.image = image;
  pubs.set(handle, p);
  return p;
};

for (const s of catalog.skills) {
  const o = details.get(s.slug)?.owner;
  if (o?.handle) touchPub(o.handle, { displayName: o.displayName, image: o.image, downloads: s.signals.downloads, stars: s.signals.stars, registry: 'clawhub' });
}
for (const r of skillssh.skills) {
  touchPub(r.owner, { image: `https://avatars.githubusercontent.com/${r.owner}`, downloads: r.installs, registry: 'skills.sh' });
}
const maxPublisherDownloads = Math.max(1, ...[...pubs.values()].map(p => p.totalDownloads));

// ——— rows ———
const taken = new Set();
const uniq = (want) => { let s = want, i = 2; while (taken.has(s)) s = `${want}-${i++}`; taken.add(s); return s; };
const rows = [];

for (const s of catalog.skills) {
  const d = details.get(s.slug);
  const md = d?.skill?.description && d.skill.description.length > 200 ? d.skill.description : null;
  const a = md ? analyzeSkillMd(md) : null;
  const owner = d?.owner?.handle ?? null;
  rows.push({
    slug: uniq(s.slug), name: s.name, summary: s.summary, topics: s.topics, version: s.version,
    icon: d?.skill?.icon ?? null, registry: 'clawhub', owner,
    sourceUrl: owner ? `https://clawhub.ai/${owner}/skills/${s.slug}` : 'https://clawhub.ai',
    sourceResolved: owner ? 1 : 0,
    signals: s.signals, analysis: a,
    tokens: a ? { count: a.tokens, method: 'measured' } : { count: null, method: 'unknown' },
    lang: a?.language ?? detectLanguage(`${s.name} ${s.summary}`),
    skillMd: md, ai: aiReviews[s.slug] ?? null,
    publisher: owner ? pubs.get(owner) : null,
  });
}
for (const r of skillssh.skills) {
  rows.push({
    slug: uniq(r.skill), name: r.name === r.skill ? r.skill.replace(/-/g, ' ') : r.name,
    summary: `${r.name} by ${r.owner} — ${r.installs ? `${r.installs.toLocaleString()} installs ` : ''}via the skills CLI${r.topics?.length ? `, tagged ${r.topics.join(', ')}` : ''}. Installs into any of ${skillssh.agents.length} agent runtimes.`,
    topics: r.topics ?? [], version: null, icon: null, registry: 'skills.sh', owner: r.owner,
    sourceUrl: `https://www.skills.sh/${r.owner}/${r.repo}/${r.skill}`, sourceResolved: 1,
    signals: { downloads: r.installs ?? 0, installs: r.installs ?? 0, stars: 0, versions: 1, updatedAt: null, createdAt: null, hasChangelog: false, license: null },
    analysis: null, tokens: { count: null, method: 'unknown' },
    lang: { code: 'en', label: 'English' }, skillMd: null, ai: null,
    publisher: pubs.get(r.owner) ?? null,
  });
}

// ——— score ———
const ctx = { maxDownloads: Math.max(...rows.map(r => r.signals.downloads)), now: Date.now(), maxPublisherDownloads };
for (const r of rows) r.rating = agentScore(r, ctx);

// ——— gate ———
const gated = gate(rows);

// ——— write ———
const insSkill = db.prepare(`INSERT INTO skills VALUES (
 $slug,$name,$summary,$topics,$version,$icon,$registry,$source_url,$source_resolved,$owner,
 $downloads,$stars,$versions,$has_changelog,$created_at,$updated_at,$license,
 $tokens,$token_method,$lang_code,$lang_label,$safety_grade,$safety_flags,
 $api_needed,$api_env,$network,$promo,$no_code,$skill_md,
 $score,$tier,$coverage,$score_parts,$unmeasured,
 $ai_label,$ai_note,$ai_quality,$ai_fit,$published,$gate_reason,$gate_rank)`);
const insFts = db.prepare('INSERT INTO skills_fts VALUES ($slug,$name,$summary,$skill_md)');
const insPub = db.prepare('INSERT INTO publishers VALUES ($handle,$display_name,$image,$skill_count,$total_downloads,$total_stars,$official,$registries)');

db.exec('BEGIN');
for (const p of pubs.values()) insPub.run({
  $handle: p.handle, $display_name: p.displayName, $image: p.image, $skill_count: p.skillCount,
  $total_downloads: p.totalDownloads, $total_stars: p.totalStars, $official: p.official,
  $registries: JSON.stringify([...p.registries]),
});
for (const r of rows) {
  const a = r.analysis, g = gated.get(r.slug);
  insSkill.run({
    $slug: r.slug, $name: r.name, $summary: r.summary, $topics: JSON.stringify(r.topics ?? []),
    $version: r.version, $icon: r.icon, $registry: r.registry, $source_url: r.sourceUrl,
    $source_resolved: r.sourceResolved, $owner: r.owner,
    $downloads: r.signals.downloads, $stars: r.signals.stars, $versions: r.signals.versions,
    $has_changelog: r.signals.hasChangelog ? 1 : 0, $created_at: r.signals.createdAt, $updated_at: r.signals.updatedAt,
    $license: r.signals.license,
    $tokens: r.tokens.count, $token_method: r.tokens.method,
    $lang_code: r.lang.code, $lang_label: r.lang.label,
    $safety_grade: a?.safety?.grade ?? null, $safety_flags: JSON.stringify(a?.safety?.flags ?? []),
    $api_needed: a ? (a.apiNeeded.flag ? 1 : 0) : null, $api_env: JSON.stringify(a?.apiNeeded?.envVars ?? []),
    $network: a ? (a.network ? 1 : 0) : null, $promo: a ? (a.promo ? 1 : 0) : null, $no_code: a ? (a.noCode ? 1 : 0) : null,
    $skill_md: r.skillMd,
    $score: r.rating.score, $tier: r.rating.tier, $coverage: r.rating.coverage,
    $score_parts: JSON.stringify(r.rating.parts), $unmeasured: JSON.stringify(r.rating.unknowns),
    $ai_label: r.ai?.label ?? null, $ai_note: r.ai?.note ?? null, $ai_quality: r.ai?.quality ?? null, $ai_fit: r.ai?.agentFit ?? null,
    $published: g.published ? 1 : 0, $gate_reason: g.reason, $gate_rank: g.rank,
  });
  insFts.run({ $slug: r.slug, $name: r.name, $summary: r.summary, $skill_md: r.skillMd ?? '' });
}
const insMeta = db.prepare('INSERT INTO meta VALUES ($k,$v)');
for (const [k, v] of Object.entries({
  generatedAt: catalog.generatedAt,
  sources: JSON.stringify(['clawhub.ai /api/v1 (open)', skillssh.source ?? 'skills.sh']),
  runtimes: JSON.stringify(skillssh.agents ?? []),
  skillsshTopics: JSON.stringify(skillssh.topics ?? []),
})) insMeta.run({ $k: k, $v: String(v) });
db.exec('COMMIT');
db.exec('PRAGMA optimize;');

const one = (sql) => db.prepare(sql).get();
const n = one('SELECT COUNT(*) c FROM skills').c;
const pub = one('SELECT COUNT(*) c FROM skills WHERE published=1').c;
const scanned = one('SELECT COUNT(*) c FROM skills WHERE skill_md IS NOT NULL').c;
console.log(`db: ${n} skills · ${pub} published (${(pub / n * 100).toFixed(1)}%) · ${scanned} scanned · ${pubs.size} publishers -> data/oxde.db`);
console.log('gate reasons:', db.prepare('SELECT gate_reason r, COUNT(*) c FROM skills GROUP BY r ORDER BY c DESC').all().map(x => `${x.r} ${x.c}`).join(' · '));
db.close();
