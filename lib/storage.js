import { mkdir, readFile, readdir, writeFile, link, unlink } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { get, put, list } from '@vercel/blob';

// Each submission has its own immutable file; there is no shared index to overwrite.
export function createStorage(env = process.env) {
  if (env.THEME_STORAGE === 'local') {
    if (env.VERCEL) throw new Error('Vercelでローカル保存は利用できません');
    const directory = resolve(env.THEME_LOCAL_DATA_DIR || '.theme-site-data');
    return {
      async get(id) {
        try { return JSON.parse(await readFile(join(directory, id + '.json'), 'utf8')); }
        catch (error) { if (error.code === 'ENOENT') return null; throw error; }
      },
      async insert(id, record) {
        await mkdir(directory, { recursive: true });
        const temp = join(directory, '.' + randomUUID() + '.tmp');
        try {
          await writeFile(temp, JSON.stringify(record), { flag: 'wx', mode: 0o600 });
          // Link only after the complete file is written, with exclusive creation.
          await link(temp, join(directory, id + '.json'));
          return true;
        } catch (error) { if (error.code === 'EEXIST') return false; throw error; }
        finally { await unlink(temp).catch(() => {}); }
      },
      async page(cursor) {
        let files;
        try { files = (await readdir(directory)).filter(name => /^[0-9a-f-]+\.json$/i.test(name)).sort(); }
        catch (error) { if (error.code === 'ENOENT') return { records: [], cursor: null }; throw error; }
        const start = cursor ? files.findIndex(name => name > cursor) : 0;
        const batch = start < 0 ? [] : files.slice(start, start + 50);
        const records = await Promise.all(batch.map(name => this.get(name.slice(0, -5))));
        return { records, cursor: start >= 0 && start + 50 < files.length ? batch.at(-1) : null };
      },
    };
  }
  if (!(env.BLOB_READ_WRITE_TOKEN || (env.BLOB_STORE_ID && env.VERCEL_OIDC_TOKEN))) {
    throw new Error('Private Blobストアが接続されていません');
  }
  return {
    async get(id) {
      const result = await get(`themes/${id}.json`, { access: 'private' });
      if (!result) return null;
      if (result.statusCode !== 200) throw new Error('Blobの読み取りに失敗しました');
      return JSON.parse(await new Response(result.stream).text());
    },
    async insert(id, record) {
      try {
        await put(`themes/${id}.json`, JSON.stringify(record), {
          access: 'private', addRandomSuffix: false, allowOverwrite: false, contentType: 'application/json',
        });
        return true;
      } catch (error) {
        // SDK versions differ in the error type for an existing pathname.
        // Re-read the immutable key; the handler compares the actual contents.
        if (await this.get(id)) return false;
        throw error;
      }
    },
    async page(cursor) {
      const page = await list({ prefix: 'themes/', limit: 50, ...(cursor ? { cursor } : {}) });
      const records = [];
      // Limit simultaneous storage reads for a small seminar deployment.
      for (let offset = 0; offset < page.blobs.length; offset += 8) {
        const batch = await Promise.all(page.blobs.slice(offset, offset + 8).map(blob =>
          this.get(blob.pathname.slice('themes/'.length, -'.json'.length))));
        records.push(...batch.filter(Boolean));
      }
      return { records, cursor: page.hasMore ? page.cursor : null };
    },
  };
}
