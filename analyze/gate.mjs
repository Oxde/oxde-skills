import { isDeprecated } from './heuristics.mjs';

// analyze/gate.mjs — decides which skills earn their own page.
// Everything stays in the database and the API; the gate only controls publication.
// Pure function over the scored rows, so the decision is reproducible and testable.
//
// Publishing 39k thin auto-pages would dilute the domain and help nobody. The gate
// keeps the pages worth reading and leaves the long tail queryable.

export const TARGET = 3000;

// Vendors mass-publish near-identical wrappers around one paid API (CellCog alone
// ships 35). Ranking them all wastes the index, so each publisher gets a cap and the
// rest are demoted — still in the DB, just not given a page.
export const PER_PUBLISHER_CAP = 6;

const norm = (s) => (s ?? '').toLowerCase().replace(/[^a-z0-9一-鿿]+/g, ' ').trim();

export function gate(rows, { target = TARGET, cap = PER_PUBLISHER_CAP } = {}) {
  const out = new Map();
  const ranked = [...rows].sort((a, b) =>
    b.rating.score - a.rating.score ||
    b.rating.coverage - a.rating.coverage ||
    b.signals.downloads - a.signals.downloads);

  const perPublisher = new Map();
  const seenSummary = new Set();
  let rank = 0;

  for (const r of ranked) {
    const reject = (reason) => out.set(r.slug, { published: false, reason, rank: null });

    // hard exclusions first — these are never publishable regardless of score
    if (r.analysis?.safety?.grade === 'risky') { reject('risky'); continue; }
    // the author says it's dead. Release dates can still look fresh, so trust the prose.
    if (r.analysis?.deprecated || isDeprecated(r.summary)) { reject('deprecated'); continue; }
    if ((r.signals.downloads ?? 0) < 50) { reject('no-adoption'); continue; }
    if (!r.summary || r.summary.length < 24) { reject('no-description'); continue; }

    // near-duplicate copy: same blurb republished under many slugs
    const key = `${r.owner ?? ''}::${norm(r.summary).slice(0, 90)}`;
    if (seenSummary.has(key)) { reject('duplicate'); continue; }

    // vendor flooding: cap how many pages any one publisher can occupy.
    // Only applies to KNOWN publishers — an unfetched owner is missing data, not
    // evidence that 36k skills share one author.
    if (r.owner) {
      const used = perPublisher.get(r.owner) ?? 0;
      if (used >= cap) { reject('publisher-cap'); continue; }
      perPublisher.set(r.owner, used + 1);
    }

    if (rank >= target) { reject('below-cutoff'); continue; }

    seenSummary.add(key);
    out.set(r.slug, { published: true, reason: 'published', rank: ++rank });
  }
  return out;
}
