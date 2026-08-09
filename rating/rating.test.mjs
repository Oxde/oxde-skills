// node --test rating/  — golden fixtures for the Agent Score.
// Changing a weight MUST break a test: score drift is a brand event, not a side effect.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  WEIGHTS, MAX, adoptionScore, freshnessScore, maintenanceScore,
  tokenCostScore, safetyScore, publisherScore, agentScore,
} from './rating.mjs';

const NOW = Date.UTC(2026, 7, 8); // frozen
const ctx = { maxDownloads: 472_766, now: NOW, maxPublisherDownloads: 12_476_000 };

const skill = (over = {}) => ({
  slug: 'fixture',
  signals: { downloads: 10_000, updatedAt: NOW - 3 * 86_400_000, versions: 4, hasChangelog: true, ...over.signals },
  tokens: over.tokens ?? { count: 800, method: 'measured' },
  // `in` not `??` — an explicit null must survive, that's the unscanned case
  analysis: 'analysis' in over ? over.analysis : { safety: { grade: 'safe', flags: [] } },
  publisher: 'publisher' in over ? over.publisher : { handle: 'dev', totalDownloads: 50_000, official: false },
});

test('weights sum to 100 — one number, no halves', () => {
  assert.equal(Object.values(WEIGHTS).reduce((a, b) => a + b, 0), MAX);
});

test('adoption: zero scores zero, leader scores full', () => {
  assert.equal(adoptionScore(0, ctx.maxDownloads), 0);
  assert.equal(Math.round(adoptionScore(ctx.maxDownloads, ctx.maxDownloads)), WEIGHTS.adoption);
});

test('freshness: this week full, stale near zero, unknown 25%', () => {
  assert.equal(freshnessScore(NOW - 2 * 86_400_000, NOW), WEIGHTS.freshness);
  assert.ok(freshnessScore(NOW - 400 * 86_400_000, NOW) < 1);
  assert.equal(freshnessScore(null, NOW), WEIGHTS.freshness * 0.25);
});

test('maintenance: 6 releases + changelog = full', () => {
  assert.equal(maintenanceScore({ versions: 6, hasChangelog: true }), WEIGHTS.maintenance);
  assert.equal(maintenanceScore({ versions: 1, hasChangelog: false }), 0);
});

test('token cost: lean full, bloated near zero, unknown excluded', () => {
  assert.equal(tokenCostScore({ count: 300 }).score, WEIGHTS.tokenCost);
  assert.ok(tokenCostScore({ count: 9000 }).score <= 2);
  const u = tokenCostScore({ count: null });
  assert.ok(u.unknown);
  assert.equal(u.score, null, 'unmeasured must be null, never a middle guess');
});

test('safety: safe full, risky near zero, unscanned excluded', () => {
  assert.equal(safetyScore({ grade: 'safe' }).score, WEIGHTS.safety);
  assert.ok(safetyScore({ grade: 'risky' }).score < 4);
  const u = safetyScore(null);
  assert.ok(u.unknown);
  assert.equal(u.score, null);
});

test('publisher: official full, unknown below par', () => {
  assert.equal(publisherScore({ official: true }), WEIGHTS.publisher);
  assert.equal(publisherScore(null), WEIGHTS.publisher * 0.4);
});

test('fully measured skill: 100% coverage, no unknowns, capped at 100', () => {
  const best = skill({
    signals: { downloads: ctx.maxDownloads, updatedAt: NOW, versions: 9, hasChangelog: true },
    tokens: { count: 100, method: 'measured' }, publisher: { official: true },
  });
  const r = agentScore(best, ctx);
  assert.ok(r.score <= MAX);
  assert.equal(r.unknowns.length, 0);
  assert.equal(r.coverage, 100);
  assert.equal(r.tier, 'strong');
});

test('unscanned skill: both axes excluded, coverage drops to 65%', () => {
  const r = agentScore(skill({ tokens: { count: null }, analysis: null }), ctx);
  assert.deepEqual(r.unknowns.sort(), ['safety', 'tokenCost']);
  assert.equal(r.coverage, 100 - WEIGHTS.tokenCost - WEIGHTS.safety);
});

test('unmeasured axes are excluded, not credited at half', () => {
  // same skill, once scanned clean and once unscanned. The unscanned one must not
  // inherit points it never earned — its score comes only from measured axes.
  const scanned = agentScore(skill(), ctx);
  const unscanned = agentScore(skill({ tokens: { count: null }, analysis: null }), ctx);
  assert.equal(unscanned.parts.safety, null);
  assert.equal(unscanned.parts.tokenCost, null);
  assert.ok(scanned.coverage > unscanned.coverage);
});

test('risky safety costs ~17 pts vs safe', () => {
  const a = agentScore(skill(), ctx).score;
  const c = agentScore(skill({ analysis: { safety: { grade: 'risky', flags: ['dangerous-shell'] } } }), ctx).score;
  assert.ok(a - c >= 15, `expected ≥15, got ${a - c}`);
});
