const $ = (id) => document.getElementById(id);
let currentDecisionId = null;
let currentRecommendedWorld = null;

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function statusClass(status) {
  return String(status || 'idle').toLowerCase();
}

function setStatus(status) {
  const el = $('status');
  el.textContent = status || 'UNKNOWN';
  el.className = `status ${statusClass(status)}`;
}

function renderDecision(payload) {
  const d = payload.decision;
  currentDecisionId = payload.decision_id;
  currentRecommendedWorld = d.recommended_world_id;
  setStatus(d.current_status);

  const intent = d.intent_frame || {};
  $('summary').className = '';
  $('summary').innerHTML = `
    <div class="decision-summary">
      <div><span>Production</span><strong>${esc(d.project_title)}</strong></div>
      <div><span>Revision</span><strong>${esc(d.case_revision)}</strong></div>
      <div><span>Operational objective</span><strong>${esc(intent.operational_objective || '')}</strong></div>
      <div><span>Recommended world</span><strong>${esc(d.recommended_world_id || 'none')}</strong></div>
    </div>`;

  $('route').innerHTML = (d.mode_trace || []).map((e, i) => `
    <article class="mode-card">
      <div class="mode-num">${String(i + 1).padStart(2, '0')}</div>
      <div><strong>${esc(e.mode)}</strong><p>${esc(e.reason)}</p><small>${esc(e.output_summary)}</small></div>
    </article>`).join('');

  const constraints = d.open_constraints || [];
  $('constraints').className = 'stack';
  $('constraints').innerHTML = constraints.length ? constraints.map(c => `
    <article class="constraint ${esc(c.severity)}">
      <div class="row"><strong>${esc(c.kind)}</strong><span>${esc(c.severity)}</span></div>
      <p>${esc(c.message)}</p>
      <small>Blocks: ${esc((c.blocks || []).join(', ') || 'decision confidence')}</small>
    </article>`).join('') : '<div class="success-card">No active release blockers in this revision.</div>';

  const worlds = d.worlds || [];
  $('worlds').className = 'stack';
  $('worlds').innerHTML = worlds.length ? worlds.map(w => `
    <article class="world ${w.id === d.recommended_world_id ? 'recommended' : ''}">
      <div class="row"><strong>${esc(w.id)}${w.id === d.recommended_world_id ? ' · MINIMUM USEFUL' : ''}</strong><span>${w.pareto_optimal ? 'Pareto' : ''}</span></div>
      <p>${esc(w.label)}</p>
      <small>${esc(w.explanation)}</small>
    </article>`).join('') : '<div class="empty">No counterfactual worlds required.</div>';

  const evidence = d.evidence || [];
  $('evidence').className = 'stack';
  $('evidence').innerHTML = evidence.length ? evidence.map(e => `
    <article class="evidence-card">
      <div class="row"><strong>${esc(e.source_label)}</strong><span>r${esc(e.claim_revision)}</span></div>
      <p>${esc(e.excerpt)}</p>
      ${e.source_url ? `<a href="${esc(e.source_url)}" target="_blank" rel="noopener noreferrer">source ↗</a>` : ''}
      <small>${esc(e.provenance)} · ${esc(e.source_family)}</small>
    </article>`).join('') : '<div class="empty">No evidence records in this decision.</div>';

  $('receipt').className = 'stack';
  $('receipt').innerHTML = (d.public_receipt || []).map(line => `<div class="receipt-line">${esc(line)}</div>`).join('');

  const canApprove = d.current_status === 'CONDITIONAL' && d.recommended_world_id;
  $('approveBtn').disabled = !canApprove;
  $('authorityText').textContent = canApprove
    ? `Recommended ${d.recommended_world_id} is stopped at AUTHORITY. Approval creates revision ${Number(d.case_revision) + 1} and PROOF runs again.`
    : 'No consequential creative mutation is awaiting authority.';
}

async function loadDemo() {
  $('demoBtn').disabled = true;
  $('demoBtn').textContent = 'Routing…';
  $('authorityResult').innerHTML = '';
  try {
    const res = await fetch('/api/demo');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    renderDecision(await res.json());
  } catch (err) {
    setStatus('ERROR');
    $('summary').textContent = `Demo failed: ${err.message}`;
  } finally {
    $('demoBtn').disabled = false;
    $('demoBtn').textContent = 'Run deterministic demo';
  }
}

async function checkRuntime() {
  $('runtimeBtn').disabled = true;
  try {
    const res = await fetch('/api/runtime');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const r = await res.json();
    const items = [
      ['Parallel Search', r.parallel_configured],
      ['Gemini / Vertex', r.google_configured],
      ['Google ADK', r.adk_importable],
    ];
    $('runtime').innerHTML = items.map(([name, ok]) => `
      <div><span>${esc(name)}</span><strong class="${ok ? 'ok' : 'hold'}">${ok ? 'configured' : 'HOLD'}</strong></div>`).join('');
  } catch (err) {
    $('runtime').innerHTML = `<div><span>Runtime check</span><strong class="hold">${esc(err.message)}</strong></div>`;
  } finally {
    $('runtimeBtn').disabled = false;
  }
}

async function approveWorld() {
  if (!currentDecisionId || !currentRecommendedWorld) return;
  $('approveBtn').disabled = true;
  $('approveBtn').textContent = 'Applying authority…';
  try {
    const res = await fetch('/api/authority', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        decision_id: currentDecisionId,
        world_id: currentRecommendedWorld,
        approved: true,
        note: 'Producer approval from Release Path demo UI'
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    $('authorityResult').innerHTML = `<div class="success-card"><strong>AUTHORITY RECORDED</strong><br>${esc(data.message || '')}<br>${esc((data.changes || []).join(' · '))}</div>`;
    if (data.decision) renderDecision({decision_id: data.decision_id, package: data.package, decision: data.decision});
  } catch (err) {
    $('authorityResult').innerHTML = `<div class="error-card">Authority failed: ${esc(err.message)}</div>`;
  } finally {
    $('approveBtn').textContent = 'Approve recommended world';
  }
}

$('demoBtn').addEventListener('click', loadDemo);
$('runtimeBtn').addEventListener('click', checkRuntime);
$('approveBtn').addEventListener('click', approveWorld);
checkRuntime();
