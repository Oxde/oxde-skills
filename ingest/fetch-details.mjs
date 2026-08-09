// ingest/fetch-details.mjs — pull full detail (owner, avatar, SKILL.md) for top N ClawHub skills.
// Writes one JSON per slug into data/details/. Resumable: skips slugs already on disk.
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DIR = join(ROOT, 'data', 'details');
const N = process.argv[2] === 'all' ? Infinity : Number(process.argv[2] ?? 300);
mkdirSync(DIR, { recursive: true });

const catalog = JSON.parse(readFileSync(join(ROOT, 'data', 'catalog.json'), 'utf8'));
// tested skills always get a detail fetch, however obscure — their pages are the product
const testedSlugs = new Set(readdirSync(join(ROOT, 'content', 'tested')).map(f => f.replace(/\.json$/, '')));
const byDownloads = [...catalog.skills].sort((a, b) => b.signals.downloads - a.signals.downloads);
const top = [
  ...byDownloads.filter(s => testedSlugs.has(s.slug)),
  ...byDownloads.filter(s => !testedSlugs.has(s.slug)).slice(0, N),
];

let ok = 0, skip = 0, fail = 0;
for (const s of top) {
  const f = join(DIR, `${s.slug}.json`);
  if (existsSync(f)) { skip++; continue; }
  for (let i = 0; i < 4; i++) {
    try {
      const res = await fetch(`https://clawhub.ai/api/v1/skills/${s.slug}`, { headers: { 'user-agent': 'oxde-agents-ingest/0.2 (+https://oxde.ai)' } });
      if (res.status === 503 || res.status === 429) { await new Promise(r => setTimeout(r, 2500 * (i + 1))); continue; }
      if (!res.ok) throw new Error(String(res.status));
      writeFileSync(f, JSON.stringify(await res.json()));
      ok++;
      break;
    } catch (e) {
      if (i === 3) { fail++; console.error(`fail ${s.slug}: ${e.message}`); }
    }
  }
  await new Promise(r => setTimeout(r, 350));
  if ((ok + fail) % 50 === 0 && ok + fail > 0) console.log(`progress: ${ok} ok / ${skip} cached / ${fail} fail`);
}
console.log(`details: ${ok} fetched, ${skip} cached, ${fail} failed -> data/details/`);
