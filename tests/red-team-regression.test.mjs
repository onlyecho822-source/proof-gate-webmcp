import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MAX_EVIDENCE,
  createInitialState,
  normalizeState,
  setClaim,
  addEvidence,
  analyzeConflicts,
  evaluateCase,
  recordEvaluation,
} from '../engine.mjs';

const NOW = new Date('2026-09-01T00:00:00Z');

function supportingPrimary(state, label, url, excerpt = 'supports') {
  return addEvidence(state, {
    stance: 'supports',
    sourceType: 'primary',
    sourceLabel: label,
    sourceUrl: url,
    excerpt,
    observedAt: '2026-08-31',
    reliability: 5,
  }, NOW);
}

test('P0 claim change does not launder evidence into the new claim', () => {
  let s = setClaim(createInitialState(), { claim: 'Claim A', decisionContext: 'Decide A' }, { now: NOW });
  s = supportingPrimary(s, 'A', 'https://one.test/a');
  s = supportingPrimary(s, 'B', 'https://two.test/b');
  assert.equal(evaluateCase(s, NOW).status, 'SUPPORTED');

  s = setClaim(s, { claim: 'Unrelated Claim B' }, { now: NOW });
  const verdict = evaluateCase(s, NOW);
  assert.equal(verdict.status, 'INSUFFICIENT');
  assert.equal(verdict.metrics.evidenceCount, 0);
  assert.equal(verdict.metrics.historyEvidenceCount, 2);
});

test('P0 duplicate source family cannot manufacture independent primary support', () => {
  let s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  s = supportingPrimary(s, 'Copy A', 'https://same.test/report');
  s = supportingPrimary(s, 'Copy B', 'https://same.test/report');
  const verdict = evaluateCase(s, NOW);
  assert.notEqual(verdict.status, 'SUPPORTED');
  assert.notEqual(verdict.confidence, 'high');
  assert.equal(verdict.metrics.supportPrimaryFamilies, 1);
});

test('P0 context-only primary records do not elevate support confidence', () => {
  let s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  s = addEvidence(s, { stance:'supports', sourceType:'secondary', sourceLabel:'Secondary', sourceUrl:'https://sec.test/x', excerpt:'support', observedAt:'2026-08-31', reliability:5 }, NOW);
  s = addEvidence(s, { stance:'context', sourceType:'primary', sourceLabel:'Context A', sourceUrl:'https://ctx-a.test/x', excerpt:'context', observedAt:'2026-08-31', reliability:5 }, NOW);
  s = addEvidence(s, { stance:'context', sourceType:'primary', sourceLabel:'Context B', sourceUrl:'https://ctx-b.test/x', excerpt:'context', observedAt:'2026-08-31', reliability:5 }, NOW);
  const verdict = evaluateCase(s, NOW);
  assert.notEqual(verdict.status, 'SUPPORTED');
  assert.notEqual(verdict.confidence, 'high');
  assert.equal(verdict.metrics.supportPrimaryFamilies, 0);
});

test('P0 unsafe URL schemes are rejected', () => {
  const s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  assert.throws(() => addEvidence(s, {
    stance:'supports', sourceType:'primary', sourceLabel:'Bad URL',
    sourceUrl:'javascript:alert(document.domain)', excerpt:'x', observedAt:'2026-08-31', reliability:5,
  }, NOW), /http or https/);
});

test('P0 source URLs with embedded credentials are rejected', () => {
  const s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  assert.throws(() => addEvidence(s, {
    stance:'supports', sourceType:'primary', sourceLabel:'Credential URL',
    sourceUrl:'https://user:secret@example.test/report', excerpt:'x', observedAt:'2026-08-31', reliability:5,
  }, NOW), /embedded credentials/);
});

test('P0 omitted evidence date remains unknown and is surfaced', () => {
  let s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  s = addEvidence(s, {
    stance:'supports', sourceType:'primary', sourceLabel:'Unknown date', sourceUrl:'https://date.test/x', excerpt:'x', reliability:5,
  }, NOW);
  assert.equal(s.evidence[0].observedAt, null);
  assert.ok(analyzeConflicts(s, NOW).some((x) => x.type === 'date-unknown'));
});

test('P0 future observation dates are rejected', () => {
  const s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  assert.throws(() => addEvidence(s, {
    stance:'supports', sourceType:'primary', sourceLabel:'Future', sourceUrl:'https://future.test/x', excerpt:'x', observedAt:'2026-09-02', reliability:5,
  }, NOW), /future/);
});

test('P1 different paths on one host remain one conservative source family', () => {
  let s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  s = supportingPrimary(s, 'Article A', 'https://news.test/a');
  s = supportingPrimary(s, 'Article B', 'https://news.test/b');
  const verdict = evaluateCase(s, NOW);
  assert.equal(verdict.metrics.supportPrimaryFamilies, 1);
  assert.ok(verdict.conflicts.some((x) => x.type === 'source-concentration'));
});

test('P1 direct contradiction is aggregated instead of exploding pairwise', () => {
  let s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  for (let i = 0; i < 5; i += 1) {
    s = addEvidence(s, { stance:'supports', sourceType:'secondary', sourceLabel:`S${i}`, sourceUrl:`https://s${i}.test/x`, excerpt:'support', observedAt:'2026-08-31', reliability:3 }, NOW);
    s = addEvidence(s, { stance:'contradicts', sourceType:'secondary', sourceLabel:`C${i}`, sourceUrl:`https://c${i}.test/x`, excerpt:'contradict', observedAt:'2026-08-31', reliability:3 }, NOW);
  }
  const direct = analyzeConflicts(s, NOW).filter((x) => x.type === 'direct-contradiction');
  assert.equal(direct.length, 1);
  assert.equal(direct[0].supportCount, 5);
  assert.equal(direct[0].contradictCount, 5);
});

test('P1 evidence ledger fails closed at the configured bound', () => {
  const seeded = {
    ...setClaim(createInitialState(), { claim: 'X' }, { now: NOW }),
    evidence: Array.from({ length: MAX_EVIDENCE }, (_, i) => ({
      id:`ev-${i}`, stance:'context', sourceType:'inference', sourceLabel:`L${i}`, sourceUrl:'', sourceIdentityKey:`label:l${i}`, sourceFamilyKey:`label:l${i}`, excerpt:'x', observedAt:null, reliability:1, claimRevision:1, addedAt:NOW.toISOString(),
    })),
  };
  assert.throws(() => addEvidence(seeded, {
    stance:'context', sourceType:'inference', sourceLabel:'overflow', excerpt:'x', reliability:1,
  }, NOW), /evidence limit reached/);
});

test('P1 restored browser state revalidates unsafe persisted URLs', () => {
  const restored = normalizeState({
    schemaVersion: 1,
    caseId: 'legacy',
    claimRevision: 1,
    claim: 'X',
    evidence: [{
      id:'ev-001', stance:'supports', sourceType:'primary', sourceLabel:'Legacy', sourceUrl:'javascript:alert(1)', excerpt:'x', observedAt:'2026-08-31', reliability:5, claimRevision:1,
    }],
  }, { now: NOW });
  assert.equal(restored.evidence[0].sourceUrl, '');
  assert.match(restored.evidence[0].sourceFamilyKey, /^label:/);
  assert.ok(restored.audit.some((x) => x.type === 'state-migrated'));
});

test('P1 evaluation recording appends lineage without mutating the claim', () => {
  let s = setClaim(createInitialState(), { claim: 'X' }, { now: NOW });
  s = supportingPrimary(s, 'A', 'https://a.test/x');
  const beforeClaim = s.claim;
  const beforeEvents = s.audit.length;
  const evaluation = evaluateCase(s, NOW);
  s = recordEvaluation(s, evaluation, { now: NOW, actor: 'agent' });
  assert.equal(s.claim, beforeClaim);
  assert.equal(s.audit.length, beforeEvents + 1);
  assert.equal(s.audit.at(-1).type, 'case-evaluated');
  assert.equal(s.audit.at(-1).actor, 'agent');
});
