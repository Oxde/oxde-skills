// ingest/clawhub.mjs — pull the ClawHub open catalog into data/catalog.json
// Zero deps. Node 20+. Usage: node ingest/clawhub.mjs
// Adapter contract: emits RawSkill[] — the only file that knows ClawHub's schema.

import { writeFileSync, mkdirSync, existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'data', 'catalog.json');
const API = 'https://clawhub.ai/api/v1';
const DETAIL_TOP_N = 60; // fetch full SKILL.md for top N by downloads → measured token cost

async function getJSON(url, tries = 5) {
  for (let i = 0; i < tries; i++) {
    const res = await fetch(url, { headers: { 'user-agent': 'oxde-agents-ingest/0.1 (+https://oxde.ai)' } });
    if (res.ok) return res.json();
    const body = await res.text().then(t => t.slice(0, 120));
    if ((res.status === 503 || res.status === 429) && i < tries - 1) {
      const wait = 1500 * (i + 1) ** 2;
      console.error(`   ${res.status} on ${url.slice(0, 60)}… retry in ${wait}ms`);
      await new Promise(r => setTimeout(r, wait));
      continue;
    }
    throw new Error(`GET ${url} -> ${res.status} ${body}`);
  }
}

async function fetchList() {
  // ClawHub paginates via ?limit=&cursor= (probe both shapes; fall back to single page)
  const items = [];
  let cursor;
  for (let page = 0; page < 400; page++) { // uncapped in practice; 400×100 is a runaway guard
    const url = `${API}/skills?limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`;
    const body = await getJSON(url);
    const batch = body.items ?? body.skills ?? [];
    items.push(...batch);
    cursor = body.nextCursor ?? body.cursor ?? null;
    if (!cursor || batch.length === 0) break;
    await new Promise(r => setTimeout(r, 900)); // stay under their rate limit
  }
  // dedupe by slug (defensive)
  const seen = new Map();
  for (const it of items) if (!seen.has(it.slug)) seen.set(it.slug, it);
  return [...seen.values()];
}

const approxTokens = (s) => (s ? Math.round(s.length / 4) : null);

function normalize(item, detail) {
  const stats = item.stats ?? {};
  const full = detail?.skill?.description && detail.skill.description.length > (item.summary?.length ?? 0) + 50
    ? detail.skill.description : null;
  return {
    slug: item.slug,
    name: item.displayName || item.slug,
    summary: (item.summary || '').trim(),
    topics: item.topics ?? [],
    version: item.tags?.latest ?? null,
    source: { registry: 'clawhub', url: `https://clawhub.ai/skills/${item.slug}` },
    signals: {
      downloads: stats.downloads ?? 0,
      installs: stats.installs ?? 0,
      stars: stats.stars ?? 0,
      versions: stats.versions ?? 1,
      updatedAt: item.updatedAt ?? null,
      createdAt: item.createdAt ?? null,
      hasChangelog: Boolean(item.latestVersion?.changelog),
      license: item.latestVersion?.license ?? null,
    },
    tokens: full
      ? { count: approxTokens(full), method: 'measured' } // chars/4 over the real SKILL.md
      : { count: null, method: 'unknown' },
    skillMdBytes: full ? full.length : null,
  };
}

async function main() {
  mkdirSync(join(ROOT, 'data'), { recursive: true });
  let list;
  try {
    list = await fetchList();
  } catch (err) {
    // A source that fails never breaks the build: keep last snapshot, warn loudly.
    if (existsSync(OUT)) {
      console.error(`!! ingest failed (${err.message}) — keeping last committed snapshot`);
      process.exit(0);
    }
    throw err;
  }
  list.sort((a, b) => (b.stats?.downloads ?? 0) - (a.stats?.downloads ?? 0));

  const details = new Map();
  for (const item of list.slice(0, DETAIL_TOP_N)) {
    try {
      details.set(item.slug, await getJSON(`${API}/skills/${item.slug}`));
      await new Promise(r => setTimeout(r, 120)); // be polite
    } catch { /* detail is enrichment, not required */ }
  }

  const catalog = {
    generatedAt: new Date().toISOString(),
    source: 'clawhub.ai /api/v1 (open)',
    count: list.length,
    skills: list.map(it => normalize(it, details.get(it.slug))),
  };
  writeFileSync(OUT, JSON.stringify(catalog, null, 1));
  const measured = catalog.skills.filter(s => s.tokens.method === 'measured').length;
  console.log(`catalog: ${catalog.count} skills, ${measured} with measured token cost -> ${OUT}`);
}

main();
