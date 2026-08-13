import { Buffer } from 'node:buffer';
import fs from 'node:fs';
import http, { type IncomingMessage, type ServerResponse } from 'node:http';
import net from 'node:net';
import process from 'node:process';
import { Readable } from 'node:stream';
import consola, { LogLevels } from 'consola';
import { createProxyServer } from 'httpxy';
import { parseBody, readBody } from './body';
import { createMockEngine, type MockedAsyncCalls, type MockRequest } from './mock-engine';
import { serveStatisticsRenderer, STATISTICS_RENDERER_PATH } from './mocked-apis/statistics';
import { applyCors } from './setup';

consola.level = LogLevels.debug;

const port = Number.parseInt(process.env.PORT ?? '4243', 10);
const backend = process.env.BACKEND ?? 'http://127.0.0.1:4242';
const componentsDir = process.env.PREMIUM_COMPONENT_DIR;

let statisticsRendererDir: string | undefined;
if (componentsDir && fs.existsSync(componentsDir) && fs.statSync(componentsDir).isDirectory()) {
  consola.info('Enabling statistics renderer support');
  statisticsRendererDir = componentsDir;
}
else {
  consola.warn('PREMIUM_COMPONENT_DIR was not a valid directory, disabling statistics renderer support.');
}

let mockedAsyncCalls: MockedAsyncCalls = {};
if (fs.existsSync('async-mock.json')) {
  try {
    consola.info('Loading mock data from async-mock.json');
    const buffer = fs.readFileSync('async-mock.json');
    mockedAsyncCalls = JSON.parse(buffer.toString());
  }
  catch (error) {
    consola.error(error);
  }
}
else {
  consola.info('async-mock.json doesnt exist. No async_query mocking is enabled');
}

const engine = createMockEngine(mockedAsyncCalls);

/** Bodies are read off the request stream, so they are kept here for the response handlers. */
const requestBodies = new WeakMap<IncomingMessage, unknown>();

function describe(req: IncomingMessage): MockRequest {
  const url = req.url ?? '';
  return {
    body: requestBodies.get(req),
    method: req.method ?? 'GET',
    path: url.split('?')[0],
    url,
  };
}

function copyHeaders(proxyRes: IncomingMessage, res: ServerResponse, omit: string[] = []): void {
  for (const [key, value] of Object.entries(proxyRes.headers)) {
    if (value === undefined || omit.includes(key.toLocaleLowerCase()))
      continue;

    res.setHeader(key, value);
  }
}

/**
 * Reading the whole body is what lets a mock rewrite it with a correct
 * content-length, but it also breaks streaming, so it is only done for requests
 * the engine can actually rewrite. A compressed body is passed through: it would
 * have to be inflated to be parsed, and the backend does not compress in dev.
 */
function canRewrite(req: IncomingMessage, proxyRes: IncomingMessage): boolean {
  if (!engine.handles(describe(req)))
    return false;

  // Rewriting an error into a 200 would hide it: a 401 on the task endpoint
  // would read as "no tasks running" rather than as a failure.
  const status = proxyRes.statusCode ?? 200;
  if (status < 200 || status > 299)
    return false;

  if (proxyRes.headers['content-encoding'])
    return false;

  return (proxyRes.headers['content-type'] ?? '').toLocaleLowerCase().includes('application/json');
}

function onProxyRes(proxyRes: IncomingMessage, req: IncomingMessage, res: ServerResponse): void {
  if (!canRewrite(req, proxyRes)) {
    res.statusCode = proxyRes.statusCode ?? 200;
    copyHeaders(proxyRes, res);
    proxyRes.pipe(res);
    return;
  }

  const chunks: Buffer[] = [];
  proxyRes.on('data', (chunk: Buffer) => chunks.push(Buffer.from(chunk)));
  proxyRes.on('end', () => {
    const raw = Buffer.concat(chunks);
    let rewritten: unknown;
    try {
      rewritten = engine.transformResponse(describe(req), JSON.parse(raw.toString()));
    }
    catch (error) {
      consola.error(error);
    }

    if (rewritten === undefined) {
      res.statusCode = proxyRes.statusCode ?? 200;
      copyHeaders(proxyRes, res);
      res.end(raw);
      return;
    }

    const payload = Buffer.from(JSON.stringify(rewritten));
    res.statusCode = 200;
    res.statusMessage = 'OK';
    // The rewritten payload has its own length, and is never chunked.
    copyHeaders(proxyRes, res, ['content-length', 'transfer-encoding']);
    res.setHeader('content-length', payload.byteLength.toString());
    // Deliberately unlogged: the task poll runs on a timer, so a line per
    // rewrite is one every couple of seconds and drowns everything else. What is
    // worth seeing already logs itself — a mock task appearing and completing,
    // and each renderer bundle served.
    res.end(payload);
  });
}

const proxy = createProxyServer({ selfHandleResponse: true, target: backend, ws: true });

proxy.on('proxyRes', onProxyRes);

proxy.on('error', (error) => {
  consola.error(error);
});

const server = http.createServer((req, res) => {
  applyCors(res);

  const request = describe(req);

  if (statisticsRendererDir && request.method === 'GET' && request.path === STATISTICS_RENDERER_PATH) {
    serveStatisticsRenderer(statisticsRendererDir, res);
    return;
  }

  // A preflight for a mocked endpoint is answered here: the CORS headers above
  // are the whole response, so the backend hop would add nothing.
  if (request.method === 'OPTIONS' && engine.isMocked(request)) {
    res.statusCode = 200;
    res.end();
    return;
  }

  if (request.method === 'GET' || request.method === 'HEAD') {
    proxy.web(req, res).catch(error => consola.error(error));
    return;
  }

  readBody(req)
    .then(async (raw) => {
      requestBodies.set(req, parseBody(raw, req.headers['content-type'] ?? ''));
      await proxy.web(req, res, { buffer: Readable.from(raw) });
    })
    .catch(error => consola.error(error));
});

server.on('upgrade', (req, socket, head) => {
  // Node types the upgrade socket as Duplex, but HTTP/1.1 upgrades are always
  // net.Socket, which is what httpxy expects.
  if (!(socket instanceof net.Socket)) {
    socket.destroy();
    return;
  }
  proxy.ws(req, socket, {}, head).catch((error) => {
    consola.error(error);
    socket.destroy();
  });
});

server.listen(port, () => {
  consola.log(`Proxy server is running at http://127.0.0.1:${port}`);
  consola.log(`Forwarding requests to ${backend}`);
});
