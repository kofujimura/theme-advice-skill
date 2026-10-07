import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { Readable } from 'node:stream';
import { handleThemes } from '../lib/themes.js';

if (process.env.THEME_STORAGE !== 'local') throw new Error('ローカル開発では.env.localでTHEME_STORAGE=localを設定してください');
const root = resolve('web');
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml' };
const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/api/themes') {
      const init = { method: req.method, headers: req.headers };
      if (!['GET', 'HEAD'].includes(req.method)) Object.assign(init, { body: Readable.toWeb(req), duplex: 'half' });
      const response = await handleThemes(new Request(url, init));
      res.writeHead(response.status, Object.fromEntries(response.headers));
      res.end(Buffer.from(await response.arrayBuffer()));
      return;
    }
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
    const path = resolve(root, '.' + decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname));
    if (!path.startsWith(root + '/')) { res.writeHead(403); res.end(); return; }
    const content = await readFile(path);
    res.writeHead(200, { 'Content-Type': types[extname(path)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    res.end(req.method === 'HEAD' ? undefined : content);
  } catch (error) { res.writeHead(error.code === 'ENOENT' ? 404 : 500); res.end('読み込めませんでした'); }
});
server.listen(Number(process.env.PORT || 3210), '127.0.0.1', () => {
  console.log(`テーマ広場: http://localhost:${server.address().port}`);
});
