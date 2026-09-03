import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../app.js', import.meta.url), 'utf8');

test('UI contract contains every v0.2 provenance surface used by app.js', () => {
  for (const id of ['claim', 'decision-context', 'evidence-list', 'conflict-list', 'audit-list', 'audit-empty', 'verdict', 'webmcp-status', 'tool-console']) {
    assert.match(html, new RegExp(`id=["']${id}["']`), `missing #${id}`);
  }
});

test('rendered source links use noopener and noreferrer', () => {
  assert.match(app, /rel=\\?"noopener noreferrer\\?"/);
});

test('app has no remote script dependency', () => {
  assert.doesNotMatch(html, /<script[^>]+src=["']https?:\/\//i);
  assert.match(html, /src=["']\.\/app\.js["']/);
});
