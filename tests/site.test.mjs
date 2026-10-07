import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHandler } from '../lib/themes.js';
import { createStorage } from '../lib/storage.js';
import { errorsFor, MAX_BYTES } from '../lib/validation.js';

const fixture = JSON.parse(await readFile(new URL('./public-theme.fixture.json', import.meta.url), 'utf8'));
const token = 'unit-test-only-token-at-least-24-characters';
function request(body = fixture, options = {}) {
  return new Request('https://test.example/api/themes', { method: 'POST', body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }, ...options });
}
function setup() {
  const records = new Map();
  const storage = {
    async get(id) { return records.get(id) || null; },
    async insert(id, record) { if (records.has(id)) return false; records.set(id, record); return true; },
    async page() { return { records: [...records.values()], cursor: null }; },
  };
  return { records, handle: createHandler({ env: { THEME_SUBMIT_TOKEN: token }, storageFactory: () => storage }) };
}

test('posts a valid theme, persists it, and exposes it on list and detail', async () => {
  const { handle } = setup();
  const response = await handle(request());
  assert.equal(response.status, 201);
  assert.equal((await response.json()).id, fixture.id);
  const list = await (await handle(new Request('https://test.example/api/themes'))).json();
  assert.equal(list.themes.length, 1);
  assert.equal(list.themes[0].author.nickname, fixture.author.nickname);
  assert.ok(list.themes[0].submitted_at);
  const detail = await (await handle(new Request('https://test.example/api/themes?id=' + fixture.id))).json();
  assert.equal(detail.theme.rq, fixture.theme.rq);
});
test('retries and concurrent identical submissions never produce duplicate posts', async () => {
  const { handle, records } = setup();
  const results = await Promise.all([handle(request()), handle(request()), handle(request())]);
  assert.deepEqual(results.map(result => result.status).sort(), [200, 200, 201]);
  assert.equal(records.size, 1);
  const retry = await handle(request());
  assert.equal((await retry.json()).duplicate, true);
});
test('same ID with different content conflicts and preserves the original', async () => {
  const { handle, records } = setup();
  await handle(request());
  const edited = structuredClone(fixture); edited.theme.rq = '別の問い';
  assert.equal((await handle(request(edited))).status, 409);
  assert.equal(records.get(fixture.id).theme.rq, fixture.theme.rq);
});
test('requires a configured submission key and rejects unauthenticated posts before opening storage', async () => {
  let opened = false;
  const factory = () => { opened = true; throw new Error('should not run'); };
  const missing = createHandler({ env: {}, storageFactory: factory });
  assert.equal((await missing(request())).status, 503);
  const protectedHandler = createHandler({ env: { THEME_SUBMIT_TOKEN: token }, storageFactory: factory });
  assert.equal((await protectedHandler(request(fixture, { headers: { 'Content-Type': 'application/json' } }))).status, 401);
  assert.equal(opened, false);
});
test('rejects private session fields, invalid JSON, and invalid source evidence', async () => {
  const { handle } = setup();
  assert.equal((await handle(request({ ...fixture, student: { own_words: ['private'] } }))).status, 422);
  assert.equal((await handle(request(fixture, { body: '{broken' }))).status, 400);
  const claim = structuredClone(fixture); claim.theme.novelty.status = 'search_scoped';
  assert.equal((await handle(request(claim))).status, 422);
  claim.theme.novelty.status = 'unverified'; claim.theme.technology.availability = 'verified';
  assert.ok(errorsFor(claim).length);
});
test('rejects oversized bodies without trusting the content-length header', async () => {
  const { handle } = setup();
  assert.equal((await handle(request(fixture, { body: ' '.repeat(MAX_BYTES + 1) }))).status, 413);
});
test('handles not-found, invalid IDs, unsupported methods, and storage failures explicitly', async () => {
  const { handle } = setup();
  assert.equal((await handle(new Request('https://test.example/api/themes?id=' + fixture.id))).status, 404);
  assert.equal((await handle(new Request('https://test.example/api/themes?id=../private'))).status, 400);
  assert.equal((await handle(new Request('https://test.example/api/themes', { method: 'DELETE' }))).status, 405);
  const offline = createHandler({ env: {} });
  assert.equal((await offline(new Request('https://test.example/api/themes'))).status, 503);
  assert.throws(() => createStorage({ VERCEL: '1', THEME_STORAGE: 'local' }));
});
test('local durable storage survives a new instance, protects simultaneous inserts, and paginates', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'theme-site-test-'));
  try {
    const env = { THEME_STORAGE: 'local', THEME_LOCAL_DATA_DIR: directory };
    const storage = createStorage(env);
    const writes = await Promise.all([storage.insert(fixture.id, fixture), storage.insert(fixture.id, fixture)]);
    assert.deepEqual(writes.sort(), [false, true]);
    assert.deepEqual(await createStorage(env).get(fixture.id), fixture);
    for (let index = 1; index <= 51; index++) await storage.insert(String(index).padStart(8, '0') + '-0000-4000-8000-000000000000', fixture);
    const first = await storage.page(); assert.equal(first.records.length, 50); assert.ok(first.cursor);
    const second = await storage.page(first.cursor); assert.equal(second.records.length, 2); assert.equal(second.cursor, null);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
