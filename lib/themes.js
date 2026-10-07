import { createHash, timingSafeEqual } from 'node:crypto';
import { createStorage } from './storage.js';
import { canonical, errorsFor, MAX_BYTES, UUID } from './validation.js';

function json(value, status = 200, extra = {}) {
  return Response.json(value, { status, headers: {
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...extra,
  } });
}

function authorized(request, token) {
  const supplied = request.headers.get('authorization') || '';
  const digest = value => createHash('sha256').update(value).digest();
  return timingSafeEqual(digest(supplied), digest('Bearer ' + token));
}

async function readBody(request) {
  if (Number(request.headers.get('content-length')) > MAX_BYTES) return null;
  const reader = request.body?.getReader();
  if (!reader) return '';
  const chunks = [];
  let length = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.byteLength;
    if (length > MAX_BYTES) { await reader.cancel(); return null; }
    chunks.push(value);
  }
  return Buffer.concat(chunks).toString('utf8');
}

export function createHandler({ env = process.env, storageFactory = () => createStorage(env) } = {}) {
  return async function handle(request) {
    const url = new URL(request.url);
    if (!['GET', 'POST'].includes(request.method)) return json({ error: 'GETまたはPOSTを使用してください' }, 405, { Allow: 'GET, POST' });
    let id = url.searchParams.get('id');
    if (id && !UUID.test(id)) return json({ error: 'テーマIDが違います' }, 400);
    id = id?.toLowerCase();
    const cursor = url.searchParams.get('cursor');
    if (cursor && cursor.length > 2000) return json({ error: 'カーソルが長すぎます' }, 400);

    if (request.method === 'POST') {
      const token = env.THEME_SUBMIT_TOKEN;
      if (!token || token.length < 24 || /\s/.test(token)) return json({ error: 'サイトの送信キーが未設定です' }, 503);
      if (!authorized(request, token)) return json({ error: '送信キーを確認してください' }, 401);
      if (!(request.headers.get('content-type') || '').toLowerCase().startsWith('application/json')) {
        return json({ error: 'application/jsonで送信してください' }, 415);
      }
    }

    let storage;
    try { storage = storageFactory(); }
    catch { return json({ error: 'テーマの保存先が未設定です。先生に確認してください' }, 503); }
    try {
      if (request.method === 'GET') {
        if (id) {
          const record = await storage.get(id);
          return record ? json(record) : json({ error: 'このテーマは見つかりませんでした' }, 404);
        }
        const page = await storage.page(cursor);
        return json({ themes: page.records, next_cursor: page.cursor });
      }
      const body = await readBody(request);
      if (body === null) return json({ error: 'JSONは64 KiB以内にしてください' }, 413);
      let theme;
      try { theme = JSON.parse(body); }
      catch { return json({ error: 'JSONを読み取れませんでした' }, 400); }
      const errors = errorsFor(theme);
      if (errors.length) return json({ error: '共有JSONの形式を確認してください', details: errors.slice(0, 10) }, 422);
      // Canonical lower-case key also handles a client's upper-case UUID safely.
      const key = theme.id.toLowerCase();
      const existing = await storage.get(key);
      const response = duplicate => json({ id: theme.id, duplicate, view_path: '/?theme=' + key }, duplicate ? 200 : 201);
      const compare = record => {
        const { submitted_at, ...payload } = record;
        return canonical(payload) === canonical(theme);
      };
      if (existing) return compare(existing) ? response(true) : json({ error: '同じIDで違う内容は投稿できません' }, 409);
      const inserted = await storage.insert(key, { ...theme, submitted_at: new Date().toISOString() });
      if (inserted) return response(false);
      // Another invocation may have completed the same upload concurrently.
      const concurrent = await storage.get(key);
      return concurrent && compare(concurrent) ? response(true) : json({ error: '同じIDで違う内容は投稿できません' }, 409);
    } catch (error) {
      // Avoid logging the payload or a storage exception that could contain credentials.
      console.error('Theme API operation failed:', error.name || 'Error');
      return json({ error: '保存先に接続できませんでした。少し待って同じJSONで再試行してください' }, 503);
    }
  };
}

export const handleThemes = createHandler();
