// Read-only and rejected-request checks against a deployed site. Creates no posts.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { errorsFor } from '../lib/validation.js';

const base = process.argv[2];
if (!base || new URL(base).protocol !== 'https:') throw new Error('検査する実際のHTTPS URLを指定してください');
const get = path => fetch(base + path, { signal: AbortSignal.timeout(20000) });
const homepage = await get('/');
assert.equal(homepage.status, 200, 'トップページが匿名で閲覧できること');
assert.ok((await homepage.text()).includes('テーマ広場'));
const list = await get('/api/themes');
assert.equal(list.status, 200, '本番のBlobストアに接続できること');
assert.equal(list.headers.get('cache-control'), 'no-store');
const page = await list.json(); assert.ok(Array.isArray(page.themes));
for (const record of page.themes) {
  const { submitted_at, ...theme } = record; assert.ok(submitted_at); assert.deepEqual(errorsFor(theme), []);
}
assert.equal((await get('/api/themes?id=' + randomUUID())).status, 404);
const noKey = await fetch(base + '/api/themes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}', signal: AbortSignal.timeout(20000) });
assert.equal(noKey.status, 401, 'キーなしの投稿を拒否すること');
if (process.argv[3]) {
  const token = (await readFile(process.argv[3], 'utf8')).trim();
  const invalid = await fetch(base + '/api/themes', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }, body: '{}', signal: AbortSignal.timeout(20000) });
  assert.equal(invalid.status, 422, '設定したキーで認証した後、形式検査が働くこと');
}
console.log('本番URLで匿名閲覧・Blob接続・404・投稿認証・JSON検査を確認しました。投稿は作成していません。');
