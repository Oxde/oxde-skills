// server.mjs — static server with content negotiation.
// Browsers (Accept: text/html) get HTML. Everything else — curl, agents, fetch —
// gets the markdown twin when one exists. ?format=md forces it. /api/* is JSON.
import { createServer } from 'node:http';
import { readFileSync, existsSync, statSync } from 'node:fs';
import { join, normalize, extname } from 'node:path';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIST = join(dirname(fileURLToPath(import.meta.url)), 'dist');
const PORT = process.env.PORT || 4871;
const MIME = {
  '.html': 'text/html; charset=utf-8', '.md': 'text/markdown; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.png': 'image/png', '.ico': 'image/x-icon',
};

const safe = (p) => {
  const full = normalize(join(DIST, p));
  return full.startsWith(DIST) ? full : null;
};
const exists = (p) => p && existsSync(p) && statSync(p).isFile();

createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  let path = decodeURIComponent(url.pathname);
  const accept = req.headers.accept || '';
  const wantsMd = url.searchParams.get('format') === 'md' || !accept.includes('text/html');

  const send = (file, extra = {}) => {
    const type = MIME[extname(file)] || 'application/octet-stream';
    res.writeHead(200, { 'content-type': type, 'access-control-allow-origin': '*', 'x-oxde': 'agents-welcome', ...extra });
    res.end(readFileSync(file));
  };

  // /api/v1/foo → foo.json (extensionless JSON routes)
  if (path.startsWith('/api/')) {
    const f = safe(path.endsWith('.json') ? path : `${path}.json`);
    if (exists(f)) return send(f);
    res.writeHead(404, { 'content-type': 'application/json' });
    return res.end(JSON.stringify({ error: 'not_found', hint: '/api/v1/meta lists endpoints' }));
  }

  // explicit .md twin: /skills/foo.md → /skills/foo/index.md
  if (path.endsWith('.md')) {
    const direct = safe(path);
    const nested = safe(path.replace(/\.md$/, '/index.md'));
    const rootIdx = path === '/index.md' ? safe('/index.md') : null;
    for (const f of [direct, nested, rootIdx]) if (exists(f)) return send(f);
  }

  // static assets (badges, llms.txt, sitemap…)
  if (extname(path)) {
    const f = safe(path);
    if (exists(f)) return send(f);
  }

  // page routes: negotiate html vs md twin
  const base = path === '/' ? '' : path.replace(/\/$/, '');
  const htmlF = safe(`${base}/index.html`);
  const mdF = safe(`${base}/index.md`);
  if (wantsMd && exists(mdF)) return send(mdF, { vary: 'accept' });
  if (exists(htmlF)) return send(htmlF, { vary: 'accept' });

  res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
  res.end(`404 — nothing at ${path}\ntry /skills, /llms.txt, or /api/v1/meta\n`);
}).listen(PORT, () => console.log(`oxde agents → http://localhost:${PORT}`));
