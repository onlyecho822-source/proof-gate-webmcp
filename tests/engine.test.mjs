import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialState,
  setClaim,
  addEvidence,
  analyzeConflicts,
  evaluateCase,
  loadDemoCase,
} from '../engine.mjs';

test('empty case is insufficient', () => {
  const verdict = evaluateCase(createInitialState(), new Date('2026-09-01T00:00:00Z'));
  assert.equal(verdict.status, 'INSUFFICIENT');
  assert.equal(verdict.metrics.evidenceCount, 0);
});

test('claim is required', () => {
  assert.throws(() => setClaim(createInitialState(), { claim: '   ' }), /claim is required/);
});

test('invalid evidence stance fails closed', () => {
  const s = setClaim(createInitialState(), { claim: 'X' });
  assert.throws(() => addEvidence(s, {
    stance: 'maybe', sourceType: 'primary', sourceLabel: 'A', excerpt: 'B', reliability: 3,
  }), /stance must/);
});

test('two independent primary supporting sources can support a claim', () => {
  let s = setClaim(createInitialState(), { claim: 'X' });
  s = addEvidence(s, { stance:'supports', sourceType:'primary', sourceLabel:'A', sourceUrl:'https://a.test', excerpt:'A', observedAt:'2026-08-31', reliability:5 });
  s = addEvidence(s, { stance:'supports', sourceType:'primary', sourceLabel:'B', sourceUrl:'https://b.test', excerpt:'B', observedAt:'2026-08-31', reliability:4 });
  const verdict = evaluateCase(s, new Date('2026-09-01T00:00:00Z'));
  assert.equal(verdict.status, 'SUPPORTED');
  assert.equal(verdict.confidence, 'high');
});

test('material opposing evidence produces contested verdict', () => {
  let s = setClaim(createInitialState(), { claim: 'X' });
  s = addEvidence(s, { stance:'supports', sourceType:'primary', sourceLabel:'A', sourceUrl:'https://a.test', excerpt:'A', observedAt:'2026-08-31', reliability:5 });
  s = addEvidence(s, { stance:'contradicts', sourceType:'primary', sourceLabel:'B', sourceUrl:'https://b.test', excerpt:'B', observedAt:'2026-08-31', reliability:5 });
  const verdict = evaluateCase(s, new Date('2026-09-01T00:00:00Z'));
  assert.equal(verdict.status, 'CONTESTED');
  assert.ok(verdict.conflicts.some((x) => x.type === 'direct-contradiction'));
});

test('duplicate source URL is surfaced as concentration', () => {
  let s = setClaim(createInitialState(), { claim: 'X' });
  s = addEvidence(s, { stance:'supports', sourceType:'secondary', sourceLabel:'A', sourceUrl:'https://same.test/a', excerpt:'A', observedAt:'2026-08-31', reliability:3 });
  s = addEvidence(s, { stance:'context', sourceType:'secondary', sourceLabel:'B', sourceUrl:'https://same.test/a', excerpt:'B', observedAt:'2026-08-31', reliability:3 });
  const issues = analyzeConflicts(s, new Date('2026-09-01T00:00:00Z'));
  assert.ok(issues.some((x) => x.type === 'source-concentration'));
});

test('old evidence is flagged', () => {
  let s = setClaim(createInitialState(), { claim: 'X' });
  s = addEvidence(s, { stance:'supports', sourceType:'primary', sourceLabel:'A', excerpt:'A', observedAt:'2024-01-01', reliability:5 });
  const issues = analyzeConflicts(s, new Date('2026-09-01T00:00:00Z'));
  assert.ok(issues.some((x) => x.type === 'stale-evidence'));
});

test('demo case remains contested', () => {
  const s = loadDemoCase(createInitialState());
  const verdict = evaluateCase(s, new Date('2026-09-01T00:00:00Z'));
  assert.equal(verdict.status, 'CONTESTED');
  assert.equal(verdict.metrics.evidenceCount, 4);
});
