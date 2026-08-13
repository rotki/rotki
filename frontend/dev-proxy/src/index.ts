import { Buffer } from 'node:buffer';
import fs from 'node:fs';
import http, { type IncomingMessage, type ServerResponse } from 'node:http';
import net from 'node:net';
import process from 'node:process';
import { Readable } from 'node:stream';
import consola, { LogLevels } from 'consola';
import { createProxyServer } from 'httpxy';
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

let mockedAsyncCalls: { [url: string]: any } = {};
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

/** Bodies are read off the request stream, so they are kept here for the response handlers. */
const requestBodies = new WeakMap<IncomingMessage, any>();

function manipulateResponse(res: ServerResponse, callback: (original: any) => any): void {
  // eslint-disable-next-line @typescript-eslint/unbound-method
  const originalWrite = res.write;

  res.write = (chunk: any): boolean => {
    const response = chunk.toString();
    try {
      const payload = JSON.stringify(callback(JSON.parse(response)));
      if (!res.headersSent)
        res.setHeader('content-length', payload.length.toString());

      res.statusCode = 200;
      res.statusMessage = 'OK';
      originalWrite.call(res, payload, 'utf8');
      return true;
    }
    catch (error: any) {
      consola.error(error);
      return false;
    }
  };
}

let mockTaskId = 100000;
const mockAsync: {
  pending: number[];
  completed: number[];

  taskResponses: { [task: number]: any };
} = {
  completed: [],
  pending: [],
  taskResponses: {},
};

const counter: { [url: string]: { [method: string]: number } } = {};

setInterval(() => {
  const pending = mockAsync.pending;
  const completed = mockAsync.completed;
  if (pending.length > 0)
    consola.log(`detected ${pending.length} pending tasks: ${pending.toString()}`);

  while (pending.length > 0) {
    const task = pending.pop();
    if (task)
      completed.push(task);
  }

  if (completed.length > 0)
    consola.log(`detected ${completed.length} completed tasks: ${completed.toString()}`);
}, 8000);

function createResult(result: unknown): Record<string, unknown> {
  return {
    message: '',
    result,
  };
}

function handleTasksStatus(res: ServerResponse): void {
  manipulateResponse(res, (data) => {
    const result = data.result;
    if (result?.pending)
      result.pending.push(...mockAsync.pending);
    else result.pending = mockAsync.pending;

    if (result?.completed)
      result.completed.push(...mockAsync.completed);
    else result.completed = mockAsync.completed;

    return data;
  });
}

function handleTaskRequest(url: string, tasks: string, res: ServerResponse): void {
  const task = url.replace(tasks, '');
  try {
    const taskId = Number.parseInt(task);
    if (Number.isNaN(taskId))
      return;

    if (mockAsync.completed.includes(taskId)) {
      const outcome = mockAsync.taskResponses[taskId];
      manipulateResponse(res, () =>
        createResult({
          outcome,
          status: 'completed',
        }));
      delete mockAsync.taskResponses[taskId];
      const index = mockAsync.completed.indexOf(taskId);
      mockAsync.completed.splice(index, 1);
    }
    else if (mockAsync.pending.includes(taskId)) {
      manipulateResponse(res, () =>
        createResult({
          outcome: null,
          status: 'pending',
        }));
    }
  }
  catch (error) {
    consola.error(error);
  }
}

function increaseCounter(baseUrl: string, method: string): void {
  if (!counter[baseUrl])
    counter[baseUrl] = { [method]: 1 };
  else if (!counter[baseUrl][method])
    counter[baseUrl][method] = 1;
  else counter[baseUrl][method] += 1;
}

function getCounter(baseUrl: string, method: string): number {
  return counter[baseUrl]?.[method] ?? 0;
}

function handleAsyncQuery(url: string, req: IncomingMessage, res: ServerResponse): void {
  const mockedUrls = Object.keys(mockedAsyncCalls);
  const baseUrl = url.split('?')[0];
  const index = mockedUrls.findIndex(value => value.includes(baseUrl));

  if (index < 0)
    return;

  const method = req.method ?? 'GET';
  increaseCounter(baseUrl, method);

  const response = mockedAsyncCalls[mockedUrls[index]]?.[method];
  if (!response)
    return;

  let pendingResponse: any;
  if (Array.isArray(response)) {
    const number = getCounter(baseUrl, method) - 1;
    if (number < response.length)
      pendingResponse = response[number];
    else pendingResponse = response.at(-1);
  }
  else if (typeof response === 'object') {
    pendingResponse = response;
  }
  else {
    pendingResponse = {
      message: 'There is something wrong with this mock',
      result: null,
    };
  }

  const taskId = mockTaskId++;
  mockAsync.pending.push(taskId);
  mockAsync.taskResponses[taskId] = pendingResponse;
  manipulateResponse(res, () => ({
    message: '',
    result: {
      task_id: taskId,
    },
  }));
}

function isAsyncQuery(req: IncomingMessage): boolean {
  return req.method !== 'GET' && requestBodies.get(req)?.async_query === true;
}

function isPreflight(req: IncomingMessage): boolean {
  const mockedUrls = Object.keys(mockedAsyncCalls);
  const baseUrl = (req.url ?? '').split('?')[0];
  const index = mockedUrls.findIndex(value => value.includes(baseUrl));
  return req.method === 'OPTIONS' && index >= 0;
}

function mockPreflight(res: ServerResponse): void {
  // eslint-disable-next-line @typescript-eslint/unbound-method
  const originalWrite = res.write;

  res.write = (chunk: any): boolean => {
    try {
      if (!res.headersSent)
        applyCors(res);

      res.statusCode = 200;
      res.statusMessage = 'OK';
      originalWrite.call(res, chunk, 'utf8');
      return true;
    }
    catch {
      return false;
    }
  };
}

function hasResponse(req: IncomingMessage): boolean {
  const mockResponse = mockedAsyncCalls[req.url ?? ''];
  return !!mockResponse && !!mockResponse[req.method ?? 'GET'];
}

function onProxyRes(req: IncomingMessage, res: ServerResponse): void {
  let handled = false;
  const url = req.url ?? '';
  const method = req.method ?? 'GET';
  const tasks = '/api/1/tasks/';
  if (url.indexOf('async_query') > 0) {
    handleAsyncQuery(url, req, res);
    handled = true;
  }
  else if (url === tasks) {
    handleTasksStatus(res);
    handled = true;
  }
  else if (url.startsWith(tasks)) {
    handleTaskRequest(url, tasks, res);
    handled = true;
  }
  else if (isAsyncQuery(req)) {
    handleAsyncQuery(url, req, res);
    handled = true;
  }
  else if (isPreflight(req)) {
    mockPreflight(res);
    handled = true;
  }
  else if (hasResponse(req)) {
    manipulateResponse(res, () => {
      const response = mockedAsyncCalls[url][method];
      if (Array.isArray(response)) {
        const index = getCounter(url, method);
        let responseIndex = index;
        if (index > response.length - 1)
          responseIndex = response.length - 1;

        increaseCounter(url, method);
        return response[responseIndex];
      }
      return response;
    });
    handled = true;
  }

  if (handled)
    consola.info('Handled request:', method, url);
}

/**
 * Reads the request body so the mock handlers can inspect `async_query`. The raw
 * bytes are replayed to the backend through the proxy's `buffer` option, so the
 * forwarded request stays byte-identical to the original.
 */
async function readBody(req: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks);
}

function parseBody(raw: Buffer, contentType: string): any {
  if (raw.length === 0)
    return undefined;

  const type = contentType.toLocaleLowerCase();
  if (type.startsWith('application/json')) {
    try {
      return JSON.parse(raw.toString());
    }
    catch {
      return undefined;
    }
  }
  if (type.startsWith('application/x-www-form-urlencoded'))
    return Object.fromEntries(new URLSearchParams(raw.toString()));

  return undefined;
}

const proxy = createProxyServer({ target: backend, ws: true });

proxy.on('proxyRes', (_proxyRes, req, res) => {
  onProxyRes(req, res);
});

proxy.on('error', (error) => {
  consola.error(error);
});

const server = http.createServer((req, res) => {
  applyCors(res);

  const path = (req.url ?? '').split('?')[0];
  if (statisticsRendererDir && req.method === 'GET' && path === STATISTICS_RENDERER_PATH) {
    serveStatisticsRenderer(statisticsRendererDir, res);
    return;
  }

  const method = req.method ?? 'GET';
  if (method === 'GET' || method === 'HEAD') {
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
