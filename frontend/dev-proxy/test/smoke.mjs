// End-to-end smoke test for the dev-proxy: the parts the unit tests cannot
// reach — pass-through, the locally served statistics route, CORS, body
// forwarding and websocket upgrades — against a stub backend.
//
// Run with: pnpm run --filter @rotki/dev-proxy test:smoke
import { Buffer } from 'node:buffer';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

const BACKEND_PORT = 14999;
const PROXY_PORT = 14998;
const proxyDir = process.cwd();

const componentsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'dev-proxy-premium-'));
fs.mkdirSync(path.join(componentsDir, 'dist'));
fs.writeFileSync(path.join(componentsDir, 'dist', 'premium_components_v16.js'), 'console.log("bundle")');

// The proxy reads async-mock.json from its working directory. Keep a personal
// one untouched if it is there.
const mockPath = path.join(proxyDir, 'async-mock.json');
const hadMock = fs.existsSync(mockPath);
if (!hadMock) {
  fs.writeFileSync(mockPath, JSON.stringify({
    '/api/1/assets/updates': {
      GET: { message: '', result: { local_version: 2 } },
      POST: { message: '', result: { local_version: 1 } },
    },
  }));
}

const received = [];
const backend = http.createServer((req, res) => {
  const chunks = [];
  req.on('data', chunk => chunks.push(chunk));
  req.on('end', () => {
    received.push({ body: Buffer.concat(chunks).toString(), method: req.method, url: req.url });
    res.setHeader('Content-Type', 'application/json');
    if (req.url === '/api/1/tasks/') {
      // Deliberately split across two chunks: the old res.write override parsed
      // each chunk on its own and dropped the body when it was not whole JSON.
      const payload = JSON.stringify({ message: '', result: { completed: [], pending: [1] } });
      const half = Math.floor(payload.length / 2);
      res.write(payload.slice(0, half));
      res.end(payload.slice(half));
      return;
    }
    res.end(JSON.stringify({ message: '', result: { from: 'backend' } }));
  });
});
backend.on('upgrade', (req, socket) => {
  socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n');
  socket.end();
});
await new Promise(resolve => backend.listen(BACKEND_PORT, resolve));

const proxy = spawn('tsx', ['src/index.ts'], {
  cwd: proxyDir,
  env: {
    ...process.env,
    BACKEND: `http://127.0.0.1:${BACKEND_PORT}`,
    PORT: String(PROXY_PORT),
    PREMIUM_COMPONENT_DIR: componentsDir,
  },
});
let proxyLog = '';
proxy.stdout.on('data', data => (proxyLog += data));
proxy.stderr.on('data', data => (proxyLog += data));

function request(method, url, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({ headers, host: '127.0.0.1', method, path: url, port: PROXY_PORT }, (res) => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('end', () => resolve({
        body: Buffer.concat(chunks).toString(),
        headers: res.headers,
        status: res.statusCode,
      }));
    });
    req.on('error', reject);
    if (body)
      req.write(body);
    req.end();
  });
}

function upgrade() {
  return new Promise((resolve, reject) => {
    const req = http.request({
      headers: {
        'Connection': 'Upgrade',
        'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
        'Sec-WebSocket-Version': '13',
        'Upgrade': 'websocket',
      },
      host: '127.0.0.1',
      path: '/ws/',
      port: PROXY_PORT,
    });
    req.on('upgrade', res => resolve(res.statusCode));
    req.on('response', res => reject(new Error(`no upgrade, got ${res.statusCode}`)));
    req.on('error', reject);
    req.end();
  });
}

async function waitForProxy() {
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      await request('GET', '/health');
      return;
    }
    catch {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }
  throw new Error(`proxy never came up:\n${proxyLog}`);
}

const results = [];

function check(name, ok, detail) {
  results.push({ detail, name, ok: !!ok });
}

try {
  await waitForProxy();

  const renderer = await request('GET', '/api/1/statistics/renderer');
  check('statistics renderer served locally', JSON.parse(renderer.body).result === 'console.log("bundle")', renderer.body);
  check('statistics renderer never reaches the backend', !received.some(r => r.url === '/api/1/statistics/renderer'));
  check('cors header present', renderer.headers['access-control-allow-origin'] === '*', renderer.headers['access-control-allow-origin']);

  const passthrough = await request('GET', '/api/1/settings');
  check('GET passes through', JSON.parse(passthrough.body).result?.from === 'backend', passthrough.body);

  const tasks = await request('GET', '/api/1/tasks/');
  check('task status keeps the backend ids, from a chunked response', JSON.parse(tasks.body).result?.pending?.includes(1), tasks.body);

  const postBody = JSON.stringify({ async_query: false, name: 'value' });
  const post = await request('POST', '/api/1/settings', postBody, { 'Content-Type': 'application/json' });
  const forwarded = received.find(r => r.url === '/api/1/settings' && r.method === 'POST');
  check('POST body reaches the backend intact', forwarded?.body === postBody, forwarded?.body);
  check('POST response passes through', JSON.parse(post.body).result?.from === 'backend', post.body);

  const mocked = await request('POST', '/api/1/assets/updates', JSON.stringify({ async_query: true }), { 'Content-Type': 'application/json' });
  check('async_query body gets a mocked task id', typeof JSON.parse(mocked.body).result?.task_id === 'number', mocked.body);
  check('rewritten response declares its own length', Number(mocked.headers['content-length']) === Buffer.byteLength(mocked.body), mocked.headers['content-length']);

  const mockedUrl = await request('GET', '/api/1/assets/updates?async_query=true');
  check('async_query url gets a mocked task id', typeof JSON.parse(mockedUrl.body).result?.task_id === 'number', mockedUrl.body);

  const preflight = await request('OPTIONS', '/api/1/assets/updates');
  check('preflight for a mocked path is answered locally', preflight.status === 200, String(preflight.status));

  check('websocket upgrade forwarded', (await upgrade()) === 101);
}
finally {
  proxy.kill();
  backend.close();
  if (!hadMock)
    fs.rmSync(mockPath);
  fs.rmSync(componentsDir, { force: true, recursive: true });
}

for (const result of results)
  process.stdout.write(`${result.ok ? 'PASS' : 'FAIL'}  ${result.name}${result.ok ? '' : `  -> ${result.detail}`}\n`);

const failed = results.filter(result => !result.ok).length;
if (failed > 0) {
  process.stdout.write(`\n--- proxy log ---\n${proxyLog}\n`);
  process.exit(1);
}
process.exit(0);
