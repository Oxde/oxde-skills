// rating/rating.mjs — the Agent Score. Pure functions only: no network, no fs.
// Published methodology: /docs mirrors WEIGHTS exactly.
//
// One number, 0–100, computed from data for EVERY skill. No human half, no cap.
// Agent reviews are a separate layer (see analyze/) — they label a skill, they never move its score.

export const WEIGHTS = {
  adoption: 25,    // log-scaled installs vs. catalog leader
  freshness: 15,   // days since last release, exponential decay
  maintenance: 10, // release count + changelog discipline
  tokenCost: 15,   // context tokens the skill spends before doing anything
  safety: 20,      // static scan of SKILL.md: injection, exfil, dangerous shell
  publisher: 15,   // track record: official org, portfolio installs
};
export const MAX = 100;

const DAY = 86_400_000;
const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));

export function adoptionScore(downloads, maxDownloads) {
  if (!downloads || downloads <= 0) return 0;
  return clamp(Math.log10(downloads + 1) / Math.log10((maxDownloads || 1) + 1), 0, 1) * WEIGHTS.adoption;
}

export function freshnessScore(updatedAt, now = Date.now()) {
  if (!updatedAt) return WEIGHTS.freshness * 0.25; // unknown ≠ dead, but never full marks
  const days = clamp((now - updatedAt) / DAY, 0, 3650);
  return days <= 7 ? WEIGHTS.freshness : WEIGHTS.freshness * Math.exp(-(days - 7) / 90);
}

export function maintenanceScore({ versions = 1, hasChangelog = false }) {
  const W = WEIGHTS.maintenance;
  return clamp((versions - 1) / 5, 0, 1) * (W - 3) + (hasChangelog ? 3 : 0);
}

// what the skill costs your context window before it does anything
export function tokenCostScore(tokens) {
  const W = WEIGHTS.tokenCost;
  if (tokens?.count == null) return { score: null, unknown: true };
  const t = tokens.count;
  return { score: t <= 400 ? W : t <= 1200 ? W * 0.8 : t <= 3000 ? W * 0.55 : t <= 6000 ? W * 0.3 : W * 0.1, unknown: false };
}

export function safetyScore(safety) {
  const W = WEIGHTS.safety;
  if (!safety?.grade) return { score: null, unknown: true };
  return { score: { safe: W, review: W * 0.65, risky: W * 0.15 }[safety.grade] ?? W * 0.5, unknown: false };
}

export function publisherScore(pub, maxPublisherDownloads = 1) {
  const W = WEIGHTS.publisher;
  if (!pub) return W * 0.4; // unknown publisher: below par, not zero
  if (pub.official) return W;
  const ratio = Math.log10((pub.totalDownloads ?? 0) + 1) / Math.log10(maxPublisherDownloads + 1);
  return clamp(0.3 + ratio * 0.7, 0, 1) * W;
}

// An unmeasured axis is EXCLUDED from the score, not given a middle guess.
// Scoring on a flat constant made 74% of a 39k catalog collapse into one band —
// and it quietly credits skills nobody has scanned. Instead we score over the
// axes we actually measured and publish `coverage`, so a 90 at 65% coverage is
// visibly a different claim from a 90 at 100%.
export function agentScore(skill, ctx) {
  const token = tokenCostScore(skill.tokens);
  const safe = safetyScore(skill.analysis?.safety);
  const parts = {
    adoption: adoptionScore(skill.signals.downloads, ctx.maxDownloads),
    freshness: freshnessScore(skill.signals.updatedAt, ctx.now),
    maintenance: maintenanceScore(skill.signals),
    tokenCost: token.score,
    safety: safe.score,
    publisher: publisherScore(skill.publisher, ctx.maxPublisherDownloads),
  };
  const measured = Object.entries(parts).filter(([, v]) => v != null);
  const availableWeight = measured.reduce((a, [k]) => a + WEIGHTS[k], 0);
  const earned = measured.reduce((a, [, v]) => a + v, 0);
  const score = clamp((earned / availableWeight) * MAX, 0, MAX);
  const unknowns = Object.entries(parts).filter(([, v]) => v == null).map(([k]) => k);
  return {
    score: Math.round(score),
    parts,
    unknowns,
    coverage: Math.round((availableWeight / MAX) * 100),
    tier: score >= 75 ? 'strong' : score >= 55 ? 'good' : score >= 35 ? 'fair' : 'weak',
  };
}
