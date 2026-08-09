// analyze/llm-harness.mjs — batch AI review of top skills via `claude -p` (haiku).
// Only the best skills get AI review; the rest are scored by data analysis alone.
// Usage: node analyze/llm-harness.mjs [N]   (default 10; resumable, skips done slugs)
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'analyze', 'llm-labels.json');
const N = Number(process.argv[2] ?? 10);
const MODEL = 'claude-haiku-4-5-20251001'; // cheap batch labeler

const PROMPT = readFileSync(join(ROOT, 'analyze', 'PROMPT.md'), 'utf8')
  .split('```')[1].trim();

const catalog = JSON.parse(readFileSync(join(ROOT, 'data', 'catalog.json'), 'utf8'));
const detailsDir = join(ROOT, 'data', 'details');
const have = new Set(readdirSync(detailsDir).map(f => f.replace(/\.json$/, '')));
const top = [...catalog.skills].sort((a, b) => b.signals.downloads - a.signals.downloads)
  .filter(s => have.has(s.slug)).slice(0, N);

const labels = existsSync(OUT) ? JSON.parse(readFileSync(OUT, 'utf8')) : {};
let done = 0;
for (const s of top) {
  if (labels[s.slug]) { done++; continue; }
  const detail = JSON.parse(readFileSync(join(detailsDir, `${s.slug}.json`), 'utf8'));
  const md = (detail.skill?.description ?? '').slice(0, 24_000); // cap input
  if (md.length < 200) continue;
  const prompt = PROMPT.replace('{{SKILL_MD}}', md);
  try {
    // Fixed argv — MODEL is a constant; untrusted SKILL.md travels via stdin only,
    // never through a shell string (the `claude` bin is a shell wrapper, hence zsh -c).
    const raw = execFileSync('/bin/zsh', ['-c', `claude -p --model ${MODEL} --output-format text`], {
      input: prompt, encoding: 'utf8', timeout: 120_000, maxBuffer: 1024 * 1024,
    }).trim();
    const json = raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1);
    const parsed = JSON.parse(json);
    if (!['solid', 'promising', 'niche', 'promo-heavy', 'risky', 'low-quality'].includes(parsed.label)) throw new Error(`bad label ${parsed.label}`);
    labels[s.slug] = { ...parsed, model: MODEL, at: new Date().toISOString().slice(0, 10) };
    writeFileSync(OUT, JSON.stringify(labels, null, 1));
    done++;
    console.log(`${s.slug}: ${parsed.label} q${parsed.quality} fit${parsed.agentFit} — ${parsed.note}`);
  } catch (e) {
    console.error(`skip ${s.slug}: ${String(e.message).slice(0, 120)}`);
  }
}
console.log(`llm labels: ${done}/${top.length} -> ${OUT}`);
