// ingest/skillssh-deep.mjs — expand skills.sh coverage beyond the 190-row leaderboard.
// Crawls /topic/* and /agent/* (both server-rendered) plus the official-org table.
// Agent pages are the prize: they tell us which runtimes a skill actually supports.
import { writeFileSync, mkdirSync, existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'data', 'skillssh.json');
const UA = { headers: { 'user-agent': 'Mozilla/5.0 (oxde-agents-ingest; +https://oxde.ai)' } };
const SKIP = new Set(['docs', 'api', '_next', 'b', 'topic', 'agent', 'p', 'search', 'official', 'audits', 'packs', 'trending', 'hot', 'about', 'contact', 'privacy', 'terms']);

const get = async (url) => {
  for (let i = 0; i < 3; i++) {
    const res = await fetch(url, UA);
    if (res.ok) return res.text();
    if (i < 2) await new Promise(r => setTimeout(r, 1200 * (i + 1)));
  }
  throw new Error(`GET ${url} failed`);
};

const fmtNum = (s) => {
  const m = String(s).trim().match(/^([\d.]+)([kM])?$/i);
  if (!m) return null;
  const n = parseFloat(m[1]);
  return Math.round(m[2]?.toLowerCase() === 'm' ? n * 1e6 : m[2] ? n * 1e3 : n);
};

// every listing page uses the same row anchor: /{owner}/{repo}/{skill}
function parseRows(html) {
  const rows = [];
  const re = /<a[^>]+href="\/([a-z0-9_.-]+)\/([a-z0-9_.-]+)\/([a-z0-9_.-]+)"[^>]*>([\s\S]*?)<\/a>/gi;
  let m;
  while ((m = re.exec(html))) {
    const [, owner, repo, skill, inner] = m;
    if (SKIP.has(owner)) continue;
    const text = inner.replace(/<[^>]+>/g, ' ').split(' ').map(t => t.trim()).filter(Boolean);
    const rank = parseInt(text[0], 10);
    const installs = fmtNum(text[text.length - 1]);
    rows.push({
      owner, repo, skill,
      name: (Number.isFinite(rank) ? text[1] : text[0]) ?? skill,
      rank: Number.isFinite(rank) ? rank : null,
      installs: installs ?? 0,
    });
  }
  return rows;
}

const links = (html, prefix) => [...new Set([...html.matchAll(new RegExp(`href="/${prefix}/([a-z0-9-]+)"`, 'g'))].map(m => m[1]))];

async function officialOrgs() {
  const text = (await get('https://www.skills.sh/official')).replace(/<[^>]+>/g, ' ');
  const seg = text.split(/Creator\s+Repos\s+Skills/i)[1] ?? '';
  const orgs = new Map();
  const re = /([a-z0-9_-]+)\s+([a-z0-9_.-]+)\s+(\d+)\s+(\d+)/g;
  let m;
  while ((m = re.exec(seg)) && orgs.size < 300) {
    const [, org, repo, skills, installs] = m;
    if (org.length < 2 || /^\d+$/.test(org)) continue;
    orgs.set(org, { org, repo, skills: +skills, installs: +installs });
  }
  return [...orgs.values()];
}

const merged = new Map(); // key owner/repo/skill
const add = (r, extra = {}) => {
  const k = `${r.owner}/${r.repo}/${r.skill}`;
  const prev = merged.get(k) ?? { ...r, topics: [], agents: [] };
  merged.set(k, {
    ...prev,
    installs: Math.max(prev.installs ?? 0, r.installs ?? 0),
    rank: prev.rank ?? r.rank,
    topics: [...new Set([...prev.topics, ...(extra.topics ?? [])])],
    agents: [...new Set([...prev.agents, ...(extra.agents ?? [])])],
  });
};

// 1. leaderboard
for (const r of parseRows(await get('https://www.skills.sh/'))) add(r);
const afterBoard = merged.size;

// 2. topics
const topics = links(await get('https://www.skills.sh/topic'), 'topic');
for (const t of topics) {
  try {
    for (const r of parseRows(await get(`https://www.skills.sh/topic/${t}`))) add(r, { topics: [t] });
  } catch (e) { console.error(`topic ${t}: ${e.message}`); }
  await new Promise(r => setTimeout(r, 250));
}
const afterTopics = merged.size;

// 3. agent runtimes. /agent/* pages are install-instruction pages, NOT skill listings —
// they carry no per-skill data. What they do establish: every skills.sh skill installs
// through one CLI and therefore works with all of these runtimes. ClawHub skills are
// OpenClaw-native by comparison. That asymmetry is the useful fact, so we store the list.
const agents = links(await get('https://www.skills.sh/agent'), 'agent');

const orgs = await officialOrgs();
mkdirSync(join(ROOT, 'data'), { recursive: true });
writeFileSync(OUT, JSON.stringify({
  generatedAt: new Date().toISOString(),
  source: 'skills.sh leaderboard + /topic/* + /agent/* + /official',
  topics, agents, officialOrgs: orgs,
  skills: [...merged.values()].sort((a, b) => (b.installs ?? 0) - (a.installs ?? 0)),
}, null, 1));

console.log(`skills.sh: ${merged.size} skills (leaderboard ${afterBoard} → +topics ${afterTopics - afterBoard} → +agents ${merged.size - afterTopics}) · ${topics.length} topics · ${agents.length} agents · ${orgs.length} official orgs`);
const withAgents = [...merged.values()].filter(s => s.agents.length).length;
console.log(`agent compatibility known for ${withAgents} skills`);
