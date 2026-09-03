export const ENGINE_VERSION = '0.2.0';
export const STATE_SCHEMA_VERSION = 2;
export const MAX_EVIDENCE = 250;
export const SOURCE_WEIGHTS = Object.freeze({
  primary: 1.0,
  secondary: 0.7,
  inference: 0.4,
});

const STANCES = new Set(['supports', 'contradicts', 'context']);
const SOURCE_TYPES = new Set(Object.keys(SOURCE_WEIGHTS));
const TRACKING_PARAMS = new Set(['gclid', 'fbclid', 'msclkid']);

function asDate(value) {
  if (value instanceof Date) return value;
  const d = new Date(value ?? Date.now());
  return Number.isNaN(d.getTime()) ? new Date() : d;
}

function isoNow(now) {
  return asDate(now).toISOString();
}

function cleanText(value, max = 4000) {
  return String(value ?? '').trim().slice(0, max);
}

function normalizeKeyText(value) {
  return cleanText(value, 1000)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function clampReliability(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 3;
  return Math.min(5, Math.max(1, Math.round(n)));
}

function resolveMutationOptions(nowOrOptions, maybeOptions = {}) {
  if (nowOrOptions instanceof Date || typeof nowOrOptions === 'string' || typeof nowOrOptions === 'number') {
    return { now: asDate(nowOrOptions), actor: maybeOptions.actor ?? 'human' };
  }
  const options = nowOrOptions && typeof nowOrOptions === 'object' ? nowOrOptions : {};
  return { now: asDate(options.now), actor: options.actor ?? maybeOptions.actor ?? 'human' };
}

function appendAudit(state, type, details = {}, options = {}) {
  const audit = Array.isArray(state.audit) ? state.audit : [];
  const seq = audit.length + 1;
  const at = isoNow(options.now);
  const event = {
    seq,
    eventId: `audit-${String(seq).padStart(4, '0')}`,
    type,
    actor: cleanText(options.actor || 'system', 40) || 'system',
    at,
    claimRevision: Number.isInteger(state.claimRevision) ? state.claimRevision : 0,
    details,
  };
  return [...audit, event];
}

function normalizeHttpUrl(value) {
  const raw = cleanText(value, 1000);
  if (!raw) return { url: '', identityKey: '', familyKey: '' };

  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error('sourceUrl must be a valid http or https URL');
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('sourceUrl must use http or https');
  }
  if (url.username || url.password) {
    throw new Error('sourceUrl must not contain embedded credentials');
  }

  url.hash = '';
  for (const key of [...url.searchParams.keys()]) {
    if (key.toLowerCase().startsWith('utm_') || TRACKING_PARAMS.has(key.toLowerCase())) {
      url.searchParams.delete(key);
    }
  }
  url.searchParams.sort();
  url.pathname = url.pathname.replace(/\/{2,}/g, '/');
  if (url.pathname.length > 1) url.pathname = url.pathname.replace(/\/+$/, '');

  const normalized = url.toString();
  return {
    url: normalized,
    identityKey: `url:${normalized.toLowerCase()}`,
    familyKey: `host:${url.hostname.toLowerCase()}`,
  };
}

function sourceKeys(sourceUrl, sourceLabel) {
  if (cleanText(sourceUrl, 1000)) return normalizeHttpUrl(sourceUrl);
  const labelKey = normalizeKeyText(sourceLabel);
  return {
    url: '',
    identityKey: `label:${labelKey}`,
    familyKey: `label:${labelKey}`,
  };
}

function normalizeObservedAt(value, now = new Date()) {
  const raw = cleanText(value, 80);
  if (!raw) return null;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) throw new Error('observedAt must be a valid date');
  const day = d.toISOString().slice(0, 10);
  const today = asDate(now).toISOString().slice(0, 10);
  if (day > today) throw new Error('observedAt cannot be in the future');
  return day;
}

export function createInitialState(options = {}) {
  const now = asDate(options.now);
  const base = {
    schemaVersion: STATE_SCHEMA_VERSION,
    engineVersion: ENGINE_VERSION,
    caseId: `case-${now.getTime()}`,
    claimRevision: 0,
    claim: '',
    decisionContext: '',
    evidence: [],
    conflicts: [],
    verdict: null,
    audit: [],
    updatedAt: isoNow(now),
  };
  return {
    ...base,
    audit: appendAudit(base, 'case-created', { schemaVersion: STATE_SCHEMA_VERSION, engineVersion: ENGINE_VERSION }, { now, actor: 'system' }),
  };
}

export function normalizeState(raw, options = {}) {
  const now = asDate(options.now);
  if (!raw || typeof raw !== 'object') return createInitialState({ now });

  const claim = cleanText(raw.claim, 4000);
  const claimRevision = Number.isInteger(raw.claimRevision) && raw.claimRevision >= 0
    ? raw.claimRevision
    : (claim ? 1 : 0);
  const evidence = Array.isArray(raw.evidence) ? raw.evidence.slice(0, MAX_EVIDENCE).map((e, idx) => {
    let keys;
    try {
      keys = sourceKeys(e.sourceUrl, e.sourceLabel || `Legacy source ${idx + 1}`);
    } catch {
      keys = sourceKeys('', e.sourceLabel || `Legacy source ${idx + 1}`);
    }
    let observedAt = null;
    try {
      observedAt = normalizeObservedAt(e.observedAt, now);
    } catch {
      observedAt = null;
    }
    return {
      id: cleanText(e.id, 80) || `ev-${String(idx + 1).padStart(3, '0')}`,
      stance: STANCES.has(String(e.stance).toLowerCase()) ? String(e.stance).toLowerCase() : 'context',
      sourceType: SOURCE_TYPES.has(String(e.sourceType).toLowerCase()) ? String(e.sourceType).toLowerCase() : 'inference',
      sourceLabel: cleanText(e.sourceLabel, 300) || `Legacy source ${idx + 1}`,
      sourceUrl: keys.url,
      sourceIdentityKey: keys.identityKey,
      sourceFamilyKey: keys.familyKey,
      excerpt: cleanText(e.excerpt, 4000),
      observedAt,
      reliability: clampReliability(e.reliability),
      claimRevision: Number.isInteger(e.claimRevision) && e.claimRevision >= 0 ? e.claimRevision : claimRevision,
      addedAt: cleanText(e.addedAt, 80) || isoNow(now),
    };
  }) : [];

  const base = {
    schemaVersion: STATE_SCHEMA_VERSION,
    engineVersion: ENGINE_VERSION,
    caseId: cleanText(raw.caseId, 120) || `case-${now.getTime()}`,
    claimRevision,
    claim,
    decisionContext: cleanText(raw.decisionContext, 2000),
    evidence,
    conflicts: [],
    verdict: null,
    audit: Array.isArray(raw.audit)
      ? raw.audit.slice(-1000).map((event, idx) => ({
          seq: idx + 1,
          eventId: cleanText(event?.eventId, 80) || `audit-${String(idx + 1).padStart(4, '0')}`,
          type: cleanText(event?.type, 80) || 'legacy-event',
          actor: cleanText(event?.actor, 40) || 'unknown',
          at: cleanText(event?.at, 80) || isoNow(now),
          claimRevision: Number.isInteger(event?.claimRevision) ? event.claimRevision : claimRevision,
          details: event?.details && typeof event.details === 'object' ? event.details : {},
        }))
      : [],
    updatedAt: isoNow(now),
  };
  const needsMigrationEvent = raw.schemaVersion !== STATE_SCHEMA_VERSION || !Array.isArray(raw.audit);
  if (!needsMigrationEvent) return base;
  return {
    ...base,
    audit: appendAudit(base, 'state-migrated', { fromSchemaVersion: raw.schemaVersion ?? 1, evidenceCount: evidence.length }, { now, actor: 'system' }),
  };
}

export function setClaim(state, input, options = {}) {
  const { now, actor } = resolveMutationOptions(options);
  const nextClaim = cleanText(input?.claim, 4000);
  if (!nextClaim) throw new Error('claim is required');

  const priorClaim = cleanText(state.claim, 4000);
  const claimChanged = priorClaim !== nextClaim;
  const contextProvided = Object.prototype.hasOwnProperty.call(input ?? {}, 'decisionContext');
  const nextContext = contextProvided ? cleanText(input.decisionContext, 2000) : cleanText(state.decisionContext, 2000);
  const nextRevision = claimChanged ? (Number(state.claimRevision) || 0) + 1 : (Number(state.claimRevision) || 0);

  let next = {
    ...state,
    schemaVersion: STATE_SCHEMA_VERSION,
    engineVersion: ENGINE_VERSION,
    claim: nextClaim,
    claimRevision: nextRevision,
    decisionContext: nextContext,
    conflicts: [],
    verdict: null,
    updatedAt: isoNow(now),
  };

  const eventType = claimChanged ? 'claim-set' : 'claim-context-updated';
  next = {
    ...next,
    audit: appendAudit(next, eventType, {
      previousClaim: priorClaim || null,
      claim: nextClaim,
      decisionContext: nextContext || null,
      evidenceExcludedByRevision: claimChanged ? getActiveEvidence(state).length : 0,
    }, { now, actor }),
  };
  return next;
}

export function addEvidence(state, input, nowOrOptions = new Date(), maybeOptions = {}) {
  const { now, actor } = resolveMutationOptions(nowOrOptions, maybeOptions);
  if (!state.claim) throw new Error('set a claim before adding evidence');
  if (!Array.isArray(state.evidence)) throw new Error('state evidence ledger is invalid');
  if (state.evidence.length >= MAX_EVIDENCE) throw new Error(`evidence limit reached (${MAX_EVIDENCE})`);

  const stance = cleanText(input?.stance, 30).toLowerCase();
  const sourceType = cleanText(input?.sourceType, 30).toLowerCase();
  if (!STANCES.has(stance)) throw new Error('stance must be supports, contradicts, or context');
  if (!SOURCE_TYPES.has(sourceType)) throw new Error('sourceType must be primary, secondary, or inference');

  const sourceLabel = cleanText(input?.sourceLabel, 300);
  const excerpt = cleanText(input?.excerpt, 4000);
  if (!sourceLabel) throw new Error('sourceLabel is required');
  if (!excerpt) throw new Error('excerpt is required');

  const keys = sourceKeys(input?.sourceUrl, sourceLabel);
  const observedAt = normalizeObservedAt(input?.observedAt, now);
  const id = `ev-${String(state.evidence.length + 1).padStart(3, '0')}`;
  const evidence = {
    id,
    stance,
    sourceType,
    sourceLabel,
    sourceUrl: keys.url,
    sourceIdentityKey: keys.identityKey,
    sourceFamilyKey: keys.familyKey,
    excerpt,
    observedAt,
    reliability: clampReliability(input?.reliability),
    claimRevision: Number(state.claimRevision) || 0,
    addedAt: isoNow(now),
  };

  let next = {
    ...state,
    evidence: [...state.evidence, evidence],
    conflicts: [],
    verdict: null,
    updatedAt: isoNow(now),
  };
  next = {
    ...next,
    audit: appendAudit(next, 'evidence-added', {
      evidenceId: evidence.id,
      stance,
      sourceType,
      sourceFamilyKey: evidence.sourceFamilyKey,
      observedAt,
    }, { now, actor }),
  };
  return next;
}

export function getActiveEvidence(state) {
  const revision = Number(state.claimRevision) || 0;
  return (Array.isArray(state.evidence) ? state.evidence : []).filter((e) => Number(e.claimRevision) === revision);
}

function weightedValue(item) {
  return item.reliability * SOURCE_WEIGHTS[item.sourceType];
}

function ageDays(dateString, now = new Date()) {
  if (!dateString) return null;
  const d = new Date(dateString);
  if (Number.isNaN(d.getTime())) return null;
  return Math.floor((asDate(now).getTime() - d.getTime()) / 86400000);
}

function sampleIds(items, max = 12) {
  return items.slice(0, max).map((x) => x.id);
}

function groupBy(items, keyFn) {
  const groups = new Map();
  for (const item of items) {
    const key = keyFn(item);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  return groups;
}

export function analyzeConflicts(state, now = new Date()) {
  const issues = [];
  const active = getActiveEvidence(state);
  const supports = active.filter((e) => e.stance === 'supports');
  const contradicts = active.filter((e) => e.stance === 'contradicts');

  if (supports.length && contradicts.length) {
    issues.push({
      type: 'direct-contradiction',
      severity: 'high',
      evidenceIds: [...sampleIds(supports, 6), ...sampleIds(contradicts, 6)],
      supportCount: supports.length,
      contradictCount: contradicts.length,
      message: `${supports.length} supporting record(s) conflict with ${contradicts.length} contradicting record(s).`,
    });
  }

  const families = groupBy(active, (e) => e.sourceFamilyKey || e.sourceIdentityKey || normalizeKeyText(e.sourceLabel));
  for (const [familyKey, group] of families) {
    if (group.length > 1) {
      issues.push({
        type: 'source-concentration',
        severity: 'medium',
        evidenceIds: sampleIds(group),
        sourceFamilyKey: familyKey,
        sourceCount: group.length,
        message: `${group.length} records resolve to the same source family; they do not count as independent sources.`,
      });
    }
  }

  for (const e of active) {
    if (!e.observedAt) {
      issues.push({
        type: 'date-unknown',
        severity: 'medium',
        evidenceIds: [e.id],
        message: `${e.id} has no observation/publication date; freshness is unknown.`,
      });
      continue;
    }
    const age = ageDays(e.observedAt, now);
    if (age !== null && age > 365) {
      issues.push({
        type: 'stale-evidence',
        severity: 'medium',
        evidenceIds: [e.id],
        ageDays: age,
        message: `${e.id} is ${age} days old; freshness should be rechecked.`,
      });
    }
  }

  if (active.length > 0 && !active.some((e) => e.sourceType === 'primary')) {
    issues.push({
      type: 'provenance-gap',
      severity: 'medium',
      evidenceIds: sampleIds(active),
      message: 'No primary evidence is present; the current claim depends on secondary reporting or inference.',
    });
  }

  const historical = (state.evidence ?? []).filter((e) => Number(e.claimRevision) !== Number(state.claimRevision));
  if (historical.length > 0) {
    issues.push({
      type: 'prior-claim-evidence',
      severity: 'low',
      evidenceIds: sampleIds(historical),
      historicalCount: historical.length,
      message: `${historical.length} evidence record(s) are bound to earlier claim revisions and are excluded from the current verdict.`,
    });
  }

  return issues;
}

function scoreUniqueFamilies(items) {
  const groups = groupBy(items, (e) => e.sourceFamilyKey || e.sourceIdentityKey || normalizeKeyText(e.sourceLabel));
  let score = 0;
  for (const group of groups.values()) {
    score += Math.max(...group.map(weightedValue));
  }
  return score;
}

function countPrimaryFamilies(items) {
  const keys = new Set(items.filter((e) => e.sourceType === 'primary').map((e) => e.sourceFamilyKey || e.sourceIdentityKey));
  keys.delete('');
  return keys.size;
}

export function evaluateCase(state, now = new Date()) {
  const active = getActiveEvidence(state);
  const supports = active.filter((e) => e.stance === 'supports');
  const contradicts = active.filter((e) => e.stance === 'contradicts');
  const contexts = active.filter((e) => e.stance === 'context');

  const supportScore = scoreUniqueFamilies(supports);
  const contradictScore = scoreUniqueFamilies(contradicts);
  const contextScore = scoreUniqueFamilies(contexts);
  const conflicts = analyzeConflicts(state, now);
  const highConflicts = conflicts.filter((x) => x.severity === 'high').length;
  const supportPrimaryFamilies = countPrimaryFamilies(supports);
  const contradictPrimaryFamilies = countPrimaryFamilies(contradicts);
  const primaryCount = active.filter((e) => e.sourceType === 'primary').length;
  const substantive = supportScore + contradictScore;
  const freshnessUncertain = conflicts.some((x) => x.type === 'date-unknown' || x.type === 'stale-evidence');

  let status = 'INSUFFICIENT';
  let confidence = 'low';
  let rationale = 'Not enough substantive evidence has been recorded for the current claim revision.';

  if (substantive >= 3) {
    if (supportScore > 0 && contradictScore > 0 && Math.max(supportScore, contradictScore) / Math.min(supportScore, contradictScore) < 1.75) {
      status = 'CONTESTED';
      confidence = highConflicts > 0 ? 'high' : 'medium';
      rationale = 'Material evidence points in opposing directions; the contradiction should be resolved before action.';
    } else if (supportScore >= Math.max(3, contradictScore * 1.75)) {
      const independentlySupported = supportPrimaryFamilies >= 2 && highConflicts === 0;
      status = independentlySupported ? 'SUPPORTED' : 'PLAUSIBLE';
      confidence = independentlySupported && !freshnessUncertain ? 'high' : 'medium';
      rationale = independentlySupported
        ? 'At least two independent primary source families materially support the current claim without a strong unresolved contradiction.'
        : 'The evidence leans toward support, but primary-source independence is not strong enough for a supported verdict.';
    } else if (contradictScore >= Math.max(3, supportScore * 1.75)) {
      const primaryRefutation = contradictPrimaryFamilies >= 1;
      status = primaryRefutation ? 'REFUTED' : 'CONTESTED';
      confidence = primaryRefutation && !freshnessUncertain ? 'high' : 'medium';
      rationale = primaryRefutation
        ? 'Independent primary contradictory evidence materially outweighs supporting evidence for the current claim.'
        : 'Contradictory evidence dominates, but primary sourcing is still insufficient for a refuted verdict.';
    } else {
      status = 'PLAUSIBLE';
      confidence = 'medium';
      rationale = 'The evidence has direction, but the margin is not decisive.';
    }
  }

  return {
    engineVersion: ENGINE_VERSION,
    claimRevision: Number(state.claimRevision) || 0,
    status,
    confidence,
    rationale,
    metrics: {
      supportScore: Number(supportScore.toFixed(2)),
      contradictScore: Number(contradictScore.toFixed(2)),
      contextScore: Number(contextScore.toFixed(2)),
      evidenceCount: active.length,
      historyEvidenceCount: (state.evidence ?? []).length - active.length,
      primaryCount,
      supportPrimaryFamilies,
      contradictPrimaryFamilies,
      conflictCount: conflicts.length,
    },
    conflicts,
  };
}

export function recordEvaluation(state, evaluation, options = {}) {
  const { now, actor } = resolveMutationOptions(options);
  let next = {
    ...state,
    verdict: evaluation,
    conflicts: evaluation.conflicts,
    updatedAt: isoNow(now),
  };
  next = {
    ...next,
    audit: appendAudit(next, 'case-evaluated', {
      status: evaluation.status,
      confidence: evaluation.confidence,
      activeEvidenceCount: evaluation.metrics.evidenceCount,
      conflictCount: evaluation.metrics.conflictCount,
      engineVersion: evaluation.engineVersion,
    }, { now, actor }),
  };
  return next;
}

export function loadDemoCase(state, options = {}) {
  const now = asDate(options.now);
  let next = setClaim(state, {
    claim: 'The vendor reduced customer-support ticket volume by 40% after deployment.',
    decisionContext: 'A procurement lead must decide whether the claimed outcome is strong enough to justify a larger rollout.',
  }, { now, actor: 'system' });
  next = addEvidence(next, {
    stance: 'supports', sourceType: 'secondary', sourceLabel: 'Vendor case study (fictional demo)',
    sourceUrl: 'https://vendor.example/case-study', excerpt: 'The vendor reports a 40% reduction in support tickets across selected accounts.',
    observedAt: '2026-08-28', reliability: 3,
  }, now, { actor: 'system' });
  next = addEvidence(next, {
    stance: 'supports', sourceType: 'secondary', sourceLabel: 'Implementation partner summary (fictional demo)',
    sourceUrl: 'https://partner.example/summary', excerpt: 'An implementation partner reports similar reductions in the subset of queues migrated to the new workflow.',
    observedAt: '2026-08-29', reliability: 3,
  }, now, { actor: 'system' });
  next = addEvidence(next, {
    stance: 'contradicts', sourceType: 'primary', sourceLabel: 'Customer ticket export (fictional demo)',
    sourceUrl: 'https://customer.example/ticket-export', excerpt: 'The customer export shows ticket volume declined from 1,000 to 780, a 22% reduction over the measured period.',
    observedAt: '2026-08-31', reliability: 5,
  }, now, { actor: 'system' });
  next = addEvidence(next, {
    stance: 'context', sourceType: 'primary', sourceLabel: 'Measurement note (fictional demo)',
    sourceUrl: 'https://measurement.example/note', excerpt: 'The 40% figure excludes two high-volume support queues that remained on the legacy workflow.',
    observedAt: '2026-08-31', reliability: 4,
  }, now, { actor: 'system' });
  return next;
}
