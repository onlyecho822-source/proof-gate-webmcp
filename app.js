import {
  createInitialState,
  normalizeState,
  setClaim,
  addEvidence,
  getActiveEvidence,
  analyzeConflicts,
  evaluateCase,
  recordEvaluation,
  loadDemoCase,
} from './engine.mjs';
import { createToolDefinitions, registerAndVerifyTools } from './webmcp-tools.mjs';

const els = {
  claim: document.querySelector('#claim'),
  decision: document.querySelector('#decision-context'),
  evidenceList: document.querySelector('#evidence-list'),
  evidenceEmpty: document.querySelector('#evidence-empty'),
  conflictList: document.querySelector('#conflict-list'),
  conflictEmpty: document.querySelector('#conflict-empty'),
  auditList: document.querySelector('#audit-list'),
  auditEmpty: document.querySelector('#audit-empty'),
  verdict: document.querySelector('#verdict'),
  confidence: document.querySelector('#confidence'),
  rationale: document.querySelector('#rationale'),
  supportMetric: document.querySelector('#support-metric'),
  contradictMetric: document.querySelector('#contradict-metric'),
  evidenceMetric: document.querySelector('#evidence-metric'),
  conflictMetric: document.querySelector('#conflict-metric'),
  webmcpStatus: document.querySelector('#webmcp-status'),
  webmcpDetail: document.querySelector('#webmcp-detail'),
  toolCount: document.querySelector('#tool-count'),
  toast: document.querySelector('#toast'),
  consoleTool: document.querySelector('#console-tool'),
  consoleArgs: document.querySelector('#console-args'),
  consoleOutput: document.querySelector('#console-output'),
  evidenceDialog: document.querySelector('#evidence-dialog'),
  evidenceForm: document.querySelector('#evidence-form'),
};

let state = createInitialState();
let lastEvaluation = evaluateCase(state);

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => els.toast.classList.remove('show'), 2200);
}

function persist() {
  localStorage.setItem('proof-gate-case-v2', JSON.stringify(state));
}

function restore() {
  const raw = localStorage.getItem('proof-gate-case-v2') ?? localStorage.getItem('proof-gate-case-v1');
  if (!raw) return;
  try {
    state = normalizeState(JSON.parse(raw));
  } catch {
    state = createInitialState();
  }
}

function renderEvidence() {
  const activeIds = new Set(getActiveEvidence(state).map((e) => e.id));
  els.evidenceEmpty.hidden = state.evidence.length > 0;
  els.evidenceList.innerHTML = state.evidence.map((e) => {
    const active = activeIds.has(e.id);
    const date = e.observedAt || 'date unknown';
    const link = e.sourceUrl
      ? `<a href="${escapeHtml(e.sourceUrl)}" target="_blank" rel="noopener noreferrer">source ↗</a>`
      : '<span>no URL</span>';
    return `
      <article class="evidence-card stance-${escapeHtml(e.stance)} ${active ? '' : 'historical-evidence'}">
        <div class="evidence-head">
          <span class="eyebrow">${escapeHtml(e.id)} · ${escapeHtml(e.sourceType)} · claim v${escapeHtml(e.claimRevision)}</span>
          <span class="stance-pill">${active ? escapeHtml(e.stance) : 'history only'}</span>
        </div>
        <h3>${escapeHtml(e.sourceLabel)}</h3>
        <p>${escapeHtml(e.excerpt)}</p>
        <div class="evidence-meta">
          <span>Reliability ${escapeHtml(e.reliability)}/5</span>
          <span>${escapeHtml(date)}</span>
          <span>${escapeHtml(e.sourceFamilyKey || 'source family unknown')}</span>
          ${link}
        </div>
        ${active ? '' : '<small class="binding-note">Excluded from the current verdict because the claim changed after this evidence was recorded.</small>'}
      </article>`;
  }).join('');
}

function renderConflicts() {
  const issues = analyzeConflicts(state);
  state = { ...state, conflicts: issues };
  els.conflictEmpty.hidden = issues.length > 0;
  els.conflictList.innerHTML = issues.map((issue) => `
    <article class="conflict-card severity-${escapeHtml(issue.severity)}">
      <span class="eyebrow">${escapeHtml(issue.type)}</span>
      <p>${escapeHtml(issue.message)}</p>
      <small>${escapeHtml((issue.evidenceIds || []).join(' · '))}</small>
    </article>
  `).join('');
}

function renderAudit() {
  const events = Array.isArray(state.audit) ? state.audit.slice(-10).reverse() : [];
  if (!els.auditList || !els.auditEmpty) return;
  els.auditEmpty.hidden = events.length > 0;
  els.auditList.innerHTML = events.map((event) => `
    <article class="audit-card">
      <div class="evidence-head">
        <span class="eyebrow">${escapeHtml(event.eventId)} · ${escapeHtml(event.type)}</span>
        <span class="stance-pill">v${escapeHtml(event.claimRevision)}</span>
      </div>
      <p>${escapeHtml(event.actor)} · ${escapeHtml(event.at)}</p>
      <small>${escapeHtml(JSON.stringify(event.details))}</small>
    </article>
  `).join('');
}

function renderVerdict() {
  lastEvaluation = evaluateCase(state);
  const v = lastEvaluation;
  els.verdict.textContent = v.status;
  els.verdict.dataset.status = v.status;
  els.confidence.textContent = `${v.confidence} confidence · claim v${v.claimRevision}`;
  els.rationale.textContent = v.rationale;
  els.supportMetric.textContent = v.metrics.supportScore;
  els.contradictMetric.textContent = v.metrics.contradictScore;
  els.evidenceMetric.textContent = v.metrics.evidenceCount;
  els.conflictMetric.textContent = v.metrics.conflictCount;
}

function render() {
  els.claim.value = state.claim;
  els.decision.value = state.decisionContext;
  renderEvidence();
  renderConflicts();
  renderAudit();
  renderVerdict();
  persist();
}

const toolDefinitions = createToolDefinitions({
  getState: () => state,
  setState: (next) => { state = next; },
  render,
  now: () => new Date(),
});
const toolMap = new Map(toolDefinitions.map((tool) => [tool.name, tool]));
window.proofGateTools = toolMap;

async function registerWebMCP() {
  const mc = document.modelContext;
  if (!mc || typeof mc.registerTool !== 'function') {
    els.webmcpStatus.textContent = 'Local mode';
    els.webmcpStatus.dataset.mode = 'local';
    els.webmcpDetail.textContent = 'Native WebMCP is unavailable in this browser. The local inspector exercises the same handlers.';
    els.toolCount.textContent = `${toolDefinitions.length} tool handlers ready`;
    return;
  }

  try {
    const receipt = await registerAndVerifyTools(mc, toolDefinitions);
    els.webmcpStatus.textContent = 'WebMCP registered';
    els.webmcpStatus.dataset.mode = 'live';
    if (receipt.enumerationVerified) {
      els.webmcpDetail.textContent = 'All tools registered and page enumeration verified. Browser-agent invocation still requires live competition verification.';
    } else if (receipt.enumerationSupported) {
      els.webmcpDetail.textContent = 'Tools registered, but page enumeration did not confirm the complete set. Browser-agent verification remains pending.';
    } else {
      els.webmcpDetail.textContent = 'Tools registered. This browser does not expose page enumeration, so browser-agent verification remains pending.';
    }
    els.toolCount.textContent = `${receipt.registrationCount}/${toolDefinitions.length} tools registered`;
  } catch (error) {
    els.webmcpStatus.textContent = 'WebMCP blocked';
    els.webmcpStatus.dataset.mode = 'blocked';
    els.webmcpDetail.textContent = `Native API detected, but registration failed: ${error?.message || error}`;
    els.toolCount.textContent = 'Registration incomplete';
  }
}

function syncClaimFromForm() {
  const claim = els.claim.value.trim();
  if (!claim) return;
  state = setClaim(state, { claim, decisionContext: els.decision.value }, { actor: 'human' });
  render();
}

els.claim.addEventListener('change', syncClaimFromForm);
els.decision.addEventListener('change', syncClaimFromForm);

document.querySelector('#add-evidence').addEventListener('click', () => els.evidenceDialog.showModal());
document.querySelector('#close-evidence').addEventListener('click', () => els.evidenceDialog.close());

document.querySelector('#evaluate').addEventListener('click', () => {
  const evaluation = evaluateCase(state);
  state = recordEvaluation(state, evaluation, { actor: 'human' });
  render();
  showToast('Case evaluated and added to audit lineage');
});

document.querySelector('#load-demo').addEventListener('click', () => {
  state = loadDemoCase(createInitialState());
  render();
  showToast('Fictional demo case loaded');
});

document.querySelector('#reset-case').addEventListener('click', () => {
  state = createInitialState();
  render();
  showToast('Case reset');
});

document.querySelector('#download-json').addEventListener('click', () => {
  const payload = {
    exportedAt: new Date().toISOString(),
    schemaVersion: state.schemaVersion,
    engineVersion: state.engineVersion,
    case: state,
    evaluation: evaluateCase(state),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${state.caseId}-v${state.claimRevision}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Versioned case JSON downloaded');
});

els.evidenceForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const form = new FormData(els.evidenceForm);
  try {
    state = addEvidence(state, Object.fromEntries(form.entries()), new Date(), { actor: 'human' });
    render();
    els.evidenceForm.reset();
    els.evidenceDialog.close();
    showToast('Evidence added and bound to current claim');
  } catch (error) {
    showToast(error.message);
  }
});

for (const tool of toolDefinitions) {
  const option = document.createElement('option');
  option.value = tool.name;
  option.textContent = tool.name;
  els.consoleTool.appendChild(option);
}

function seedConsoleArgs() {
  const name = els.consoleTool.value;
  const seeds = {
    'proofgate.get_case': {},
    'proofgate.set_claim': { claim: 'A specific claim to test', decisionContext: 'What decision depends on it?' },
    'proofgate.add_evidence': {
      stance: 'supports',
      sourceType: 'primary',
      sourceLabel: 'Source label',
      sourceUrl: 'https://example.com/source',
      excerpt: 'Concise observation from the source.',
      observedAt: '2026-09-01',
      reliability: 4,
    },
    'proofgate.identify_conflicts': {},
    'proofgate.evaluate_case': {},
    'proofgate.export_case': {},
  };
  els.consoleArgs.value = JSON.stringify(seeds[name] ?? {}, null, 2);
}

els.consoleTool.addEventListener('change', seedConsoleArgs);
document.querySelector('#run-tool').addEventListener('click', async () => {
  const tool = toolMap.get(els.consoleTool.value);
  try {
    const input = JSON.parse(els.consoleArgs.value || '{}');
    const result = await tool.execute(input);
    els.consoleOutput.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    els.consoleOutput.textContent = `ERROR: ${error.message}`;
  }
});

document.querySelector('#toggle-console').addEventListener('click', () => {
  document.querySelector('#tool-console').classList.toggle('open');
});

restore();
render();
seedConsoleArgs();
registerWebMCP();
