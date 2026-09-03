import test from 'node:test';
import assert from 'node:assert/strict';
import { createToolDefinitions, registerAndVerifyTools } from '../webmcp-tools.mjs';

test('P0/P1 WebMCP tools mark returned evidence as untrusted content', () => {
  const tools = createToolDefinitions({
    getState: () => ({ evidence: [] }),
    setState: () => {},
    render: () => {},
    now: () => new Date('2026-09-01T00:00:00Z'),
  });
  const evidenceReturning = new Set([
    'proofgate.get_case',
    'proofgate.add_evidence',
    'proofgate.identify_conflicts',
    'proofgate.evaluate_case',
    'proofgate.export_case',
  ]);
  for (const tool of tools) {
    if (evidenceReturning.has(tool.name)) {
      assert.equal(tool.annotations?.untrustedContentHint, true, `${tool.name} must flag untrusted evidence content`);
    }
  }
});

test('P0 native WebMCP contract registers and enumerates every tool in a compatible modelContext', async () => {
  const registered = [];
  const modelContext = {
    async registerTool(tool) { registered.push(tool); },
    async getTools() { return registered.map(({ name, annotations }) => ({ name, annotations })); },
  };
  const tools = createToolDefinitions({ getState: () => ({}), setState: () => {}, render: () => {} });
  const receipt = await registerAndVerifyTools(modelContext, tools);
  assert.equal(receipt.registrationCount, tools.length);
  assert.equal(receipt.enumerationVerified, true);
  assert.deepEqual(new Set(receipt.registeredNames), new Set(tools.map((t) => t.name)));
});

test('P1 readOnlyHint matches actual tool mutation behavior', () => {
  const tools = createToolDefinitions({ getState: () => ({}), setState: () => {}, render: () => {} });
  const byName = new Map(tools.map((t) => [t.name, t]));
  assert.equal(byName.get('proofgate.get_case').annotations?.readOnlyHint, true);
  assert.equal(byName.get('proofgate.export_case').annotations?.readOnlyHint, true);
  assert.equal(byName.get('proofgate.identify_conflicts').annotations?.readOnlyHint, true);
  assert.notEqual(byName.get('proofgate.evaluate_case').annotations?.readOnlyHint, true, 'evaluate_case records an audit event and is not read-only');
});
