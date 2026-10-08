// Pilote de rendu : sert le projet en local, ouvre Chromium sans écran, capture chaque image.
//   node render.mjs still 1.0,6.5,12 [--w 960 --h 540]   -> output/stills/*.png
//   node render.mjs frames --from 0 --to 1860 [--jobs 3]  -> output/frames/%05d.png
import { createRequire } from 'module';
import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const require = createRequire(import.meta.url);
const pwPath = process.env.PW || path.join(process.env.NODE_GLOBAL || '/opt/node22/lib/node_modules', 'playwright');
const { chromium } = require(pwPath);
const ROOT = path.dirname(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const mode = argv[0];
const opt = (name, def) => { const i = argv.indexOf('--' + name); return i >= 0 ? argv[i + 1] : def; };
const W = +opt('w', 1920), H = +opt('h', 1080);
const T = JSON.parse(fs.readFileSync(path.join(ROOT, 'timeline.json')));
const FPS = T.fps;

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.ttf': 'font/ttf', '.otf': 'font/otf' };

function serve() {
  const srv = http.createServer((req, res) => {
    const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
    if (!p.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
    fs.readFile(p, (e, d) => {
      if (e) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
      res.end(d);
    });
  });
  return new Promise((r) => srv.listen(0, '127.0.0.1', () => r(srv)));
}

async function openPage(srv) {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  page.on('pageerror', (e) => console.error('pageerror:', e.message));
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') { const s = m.text(); if (!s.includes('GL Driver')) console.error('console:', s); } });
  await page.goto(`http://127.0.0.1:${srv.address().port}/index.html?w=${W}&h=${H}`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  return { browser, page };
}

async function shoot(page, t, file) {
  await page.evaluate((tt) => window.renderAt(tt), t);
  await page.screenshot({ path: file, type: 'png', clip: { x: 0, y: 0, width: W, height: H } });
}

if (mode === 'still') {
  const times = (argv[1] || '0').split(',').map(Number);
  const out = opt('out', path.join(ROOT, 'output', 'stills'));
  fs.mkdirSync(out, { recursive: true });
  const srv = await serve();
  const { browser, page } = await openPage(srv);
  for (const t of times) {
    const f = path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`);
    const a = Date.now();
    await shoot(page, t, f);
    console.log(f, `${Date.now() - a} ms`);
  }
  await browser.close(); srv.close();
} else if (mode === 'frames') {
  const from = +opt('from', 0), to = +opt('to', Math.round(T.duration * FPS));
  const jobs = +opt('jobs', 1);
  const out = opt('out', path.join(ROOT, 'output', 'frames'));
  fs.mkdirSync(out, { recursive: true });
  if (jobs > 1) {
    // découpe en tranches entrelacées pour équilibrer la charge
    const kids = [];
    for (let j = 0; j < jobs; j++) {
      kids.push(new Promise((res, rej) => {
        const c = spawn(process.execPath, [fileURLToPath(import.meta.url), 'frames', '--from', String(from), '--to', String(to),
          '--w', String(W), '--h', String(H), '--out', out, '--stride', String(jobs), '--offset', String(j)], { stdio: 'inherit' });
        c.on('exit', (code) => (code === 0 ? res() : rej(new Error('job ' + j + ' code ' + code))));
      }));
    }
    await Promise.all(kids);
  } else {
    const stride = +opt('stride', 1), offset = +opt('offset', 0);
    const srv = await serve();
    const { browser, page } = await openPage(srv);
    const a = Date.now();
    let n = 0;
    for (let i = from + offset; i < to; i += stride) {
      const f = path.join(out, `${String(i).padStart(5, '0')}.png`);
      if (fs.existsSync(f) && !argv.includes('--force')) continue;
      await shoot(page, i / FPS, f);
      n++;
      if (n % 30 === 0) console.log(`[job ${offset}] ${i}/${to}  ${((Date.now() - a) / n).toFixed(0)} ms/img`);
    }
    await browser.close(); srv.close();
  }
} else {
  console.log('usage: node render.mjs still t1,t2 | frames --from a --to b [--jobs n]');
}
