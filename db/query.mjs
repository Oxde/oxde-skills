// db/query.mjs — the only place that knows SQL. Returns plain skill objects
// shaped exactly like the renderer expects, so site code never touches the DB.
import { DatabaseSync } from 'node:sqlite';

const J = (s, d) => { try { return s ? JSON.parse(s) : d; } catch { return d; } };

// FTS5 has its own query grammar — a bare skill name full of dots, slashes or CJK
// is a syntax error, not a search. Reduce any input to quoted terms joined by OR.
export function ftsQuery(input) {
  const terms = String(input)
    .split(/\s+OR\s+|\s+/)
    .map(t => t.replace(/["'()*:^-]/g, '').trim())
    .filter(t => t.length >= 2 && !/^(and|or|not|the|for|with|use|your)$/i.test(t))
    .slice(0, 12)
    .map(t => `"${t}"`);
  return terms.length ? terms.join(' OR ') : null;
}

export function open(path) {
  const db = new DatabaseSync(path, { readOnly: true });

  const pubs = new Map();
  for (const p of db.prepare('SELECT * FROM publishers').all()) {
    pubs.set(p.handle, {
      handle: p.handle, displayName: p.display_name, image: p.image,
      skillCount: p.skill_count, totalDownloads: p.total_downloads, totalStars: p.total_stars,
      official: Boolean(p.official), registries: J(p.registries, []),
    });
  }

  const hydrate = (r) => ({
    slug: r.slug, name: r.name, summary: r.summary, topics: J(r.topics, []),
    version: r.version, icon: r.icon,
    source: { registry: r.registry, url: r.source_url, resolved: Boolean(r.source_resolved) },
    signals: {
      downloads: r.downloads, installs: r.downloads, stars: r.stars, versions: r.versions,
      hasChangelog: Boolean(r.has_changelog), createdAt: r.created_at, updatedAt: r.updated_at, license: r.license,
    },
    tokens: { count: r.tokens, method: r.token_method },
    lang: { code: r.lang_code, label: r.lang_label },
    analysis: r.safety_grade ? {
      safety: { grade: r.safety_grade, flags: J(r.safety_flags, []) },
      apiNeeded: { flag: Boolean(r.api_needed), envVars: J(r.api_env, []) },
      network: Boolean(r.network), promo: Boolean(r.promo), noCode: Boolean(r.no_code),
      language: { code: r.lang_code, label: r.lang_label },
    } : null,
    skillMd: r.skill_md,
    rating: {
      score: r.score, tier: r.tier, coverage: r.coverage,
      parts: J(r.score_parts, {}), unknowns: J(r.unmeasured, []),
    },
    ai: r.ai_label ? { label: r.ai_label, note: r.ai_note, quality: r.ai_quality, agentFit: r.ai_fit } : null,
    publisher: r.owner ? pubs.get(r.owner) ?? null : null,
    published: Boolean(r.published), gateReason: r.gate_reason, gateRank: r.gate_rank,
  });

  const all = (sql, params = {}) => db.prepare(sql).all(params).map(hydrate);

  return {
    db, publishers: pubs,
    meta: Object.fromEntries(db.prepare('SELECT key,value FROM meta').all().map(m => [m.key, m.value])),
    counts: {
      total: db.prepare('SELECT COUNT(*) c FROM skills').get().c,
      published: db.prepare('SELECT COUNT(*) c FROM skills WHERE published=1').get().c,
      scanned: db.prepare('SELECT COUNT(*) c FROM skills WHERE skill_md IS NOT NULL').get().c,
      reviewed: db.prepare('SELECT COUNT(*) c FROM skills WHERE ai_label IS NOT NULL').get().c,
      risky: db.prepare("SELECT COUNT(*) c FROM skills WHERE safety_grade='risky'").get().c,
      publishers: pubs.size,
    },
    langCounts: Object.fromEntries(db.prepare('SELECT lang_code, COUNT(*) c FROM skills GROUP BY lang_code ORDER BY c DESC').all().map(r => [r.lang_code, r.c])),
    registryCounts: Object.fromEntries(db.prepare('SELECT registry, COUNT(*) c FROM skills GROUP BY registry').all().map(r => [r.registry, r.c])),
    gateReasons: Object.fromEntries(db.prepare('SELECT gate_reason r, COUNT(*) c FROM skills GROUP BY r ORDER BY c DESC').all().map(r => [r.r, r.c])),
    publishedSkills: () => all('SELECT * FROM skills WHERE published=1 ORDER BY score DESC, downloads DESC'),
    topSkills: (n) => all('SELECT * FROM skills WHERE published=1 ORDER BY score DESC, downloads DESC LIMIT $n', { $n: n }),
    allSkills: () => all('SELECT * FROM skills ORDER BY score DESC, downloads DESC'),
    // FTS5 across name, summary and the full SKILL.md. Input is always sanitized;
    // an unusable query returns [] rather than throwing mid-build.
    search: (q, n = 30) => {
      const fq = ftsQuery(q);
      if (!fq) return [];
      try {
        return all(
          `SELECT s.* FROM skills_fts f JOIN skills s ON s.slug = f.slug
           WHERE skills_fts MATCH $q AND s.published = 1 ORDER BY s.score DESC LIMIT $n`, { $q: fq, $n: n });
      } catch { return []; }
    },
    topPublishers: (n) => db.prepare(
      'SELECT * FROM publishers ORDER BY total_downloads DESC LIMIT $n').all({ $n: n })
      .map(p => ({
        handle: p.handle, displayName: p.display_name, image: p.image, skillCount: p.skill_count,
        totalDownloads: p.total_downloads, totalStars: p.total_stars,
        official: Boolean(p.official), registries: J(p.registries, []),
      })),
    close: () => db.close(),
  };
}
