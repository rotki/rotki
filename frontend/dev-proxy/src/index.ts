import fs from 'node:fs';
import * as querystring from 'node:querystring';
import process from 'node:process';
import { Buffer } from 'node:buffer';
import { json, urlencoded } from 'body-parser';
import express, { type Request, type Response } from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import logger from 'loglevel';
import { statistics } from './mocked-apis/statistics';
import { enableCors } from './setup';
import type * as http from 'node:http';

logger.setDefaultLevel('debug');

const server = express();

const port = process.env.PORT || 4243;
const backend = process.env.BACKEND || 'http://127.0.0.1:4242';
const componentsDir = process.env.PREMIUM_COMPONENT_DIR;

enableCors(server);

if (
  componentsDir
  && fs.existsSync(componentsDir)
  && fs.statSync(componentsDir).isDirectory()
) {
  logger.info('Enabling statistics renderer support');
  statistics(server, componentsDir);
}
else {
  logger.warn(
    'PREMIUM_COMPONENT_DIR was not a valid directory, disabling statistics renderer support.',
  );
}

let mockedAsyncCalls: { [url: string]: any } = {};
if (fs.existsSync('async-mock.json')) {
  try {
    logger.info('Loading mock data from async-mock.json');
    const buffer = fs.readFileSync('async-mock.json');
    mockedAsyncCalls = JSON.parse(buffer.toString());
  }
  catch (error) {
    logger.error(error);
  }
}
else {
  logger.info(
    'async-mock.json doesnt exist. No async_query mocking is enabled',
  );
}

function manipulateResponse(res: Response, callback: (original: any) => any) {
  const originalWrite = res.write;

  res.write = (chunk: any) => {
    const response = chunk.toString();
    try {
      const payload = JSON.stringify(callback(JSON.parse(response)));
      res.header('content-length', payload.length.toString());
      res.status(200);
      res.statusMessage = 'OK';
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      originalWrite.call(res, payload);
      return true;
    }
    catch (error: any) {
      logger.error(error);
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
  pending: [],
  completed: [],
  taskResponses: {},
};

const counter: { [url: string]: { [method: string]: number } } = {};

setInterval(() => {
  const pending = mockAsync.pending;
  const completed = mockAsync.completed;
  if (pending.length > 0)
    logger.log(`detected ${pending.length} pending tasks: ${pending.toString()}`);

  while (pending.length > 0) {
    const task = pending.pop();
    if (task)
      completed.push(task);
  }

  if (completed.length > 0)
    logger.log(`detected ${completed.length} completed tasks: ${completed.toString()}`);
}, 8000);

function createResult(result: unknown): Record<string, unknown> {
  return {
    result,
    message: '',
  };
}

function handleTasksStatus(res: Response) {
  manipulateResponse(res, (data) => {
    const result = data.result;
    if (result && result.pending)
      result.pending.push(...mockAsync.pending);
    else
      result.pending = mockAsync.pending;

    if (result && result.completed)
      result.completed.push(...mockAsync.completed);
    else
      result.completed = mockAsync.completed;

    return data;
  });
}

function handleTaskRequest(url: string, tasks: string, res: Response) {
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
    logger.error(error);
  }
}

function increaseCounter(baseUrl: string, method: string) {
  if (!counter[baseUrl])
    counter[baseUrl] = { [method]: 1 };
  else if (!counter[baseUrl][method])
    counter[baseUrl][method] = 1;
  else
    counter[baseUrl][method] += 1;
}

function getCounter(baseUrl: string, method: string): number {
  return counter[baseUrl]?.[method] ?? 0;
}

function handleAsyncQuery(url: string, req: Request, res: Response) {
  const mockedUrls = Object.keys(mockedAsyncCalls);
  const baseUrl = url.split('?')[0];
  const index = mockedUrls.findIndex(value => value.includes(baseUrl));

  if (index < 0)
    return;

  increaseCounter(baseUrl, req.method);

  const response = mockedAsyncCalls[mockedUrls[index]]?.[req.method];
  if (!response)
    return;

  let pendingResponse: any;
  if (Array.isArray(response)) {
    const number = getCounter(baseUrl, req.method) - 1;
    if (number < response.length)
      pendingResponse = response[number];
    else
      pendingResponse = response.at(-1);
  }
  else if (typeof response === 'object') {
    pendingResponse = response;
  }
  else {
    pendingResponse = {
      result: null,
      message: 'There is something wrong with this mock',
    };
  }

  const taskId = mockTaskId++;
  mockAsync.pending.push(taskId);
  mockAsync.taskResponses[taskId] = pendingResponse;
  manipulateResponse(res, () => ({
    result: {
      task_id: taskId,
    },
    message: '',
  }));
}

function isAsyncQuery(req: Request) {
  return (
    req.method !== 'GET'
    && req.rawHeaders.findIndex(h =>
      h.toLocaleLowerCase().includes('application/json'),
    )
    && req.body
    && req.body.async_query === true
  );
}

function isPreflight(req: Request) {
  const mockedUrls = Object.keys(mockedAsyncCalls);
  const baseUrl = req.url.split('?')[0];
  const index = mockedUrls.findIndex(value => value.includes(baseUrl));
  return req.method === 'OPTIONS' && index >= 0;
}

function onProxyReq(
  proxyReq: http.ClientRequest,
  req: Request,
  _res: Response,
) {
  if (!req.body)
    return;

  const contentType = proxyReq.getHeader('Content-Type') ?? '';
  const writeBody = (bodyData: string) => {
    proxyReq.setHeader('Content-Length', Buffer.byteLength(bodyData));
    proxyReq.write(bodyData);
  };

  const ct = contentType.toString().toLocaleLowerCase();
  if (ct.startsWith('application/json'))
    writeBody(JSON.stringify(req.body));

  if (ct.startsWith('application/x-www-form-urlencoded'))
    writeBody(querystring.stringify(req.body));
}

function mockPreflight(res: Response) {
  const originalWrite = res.write;

  res.write = (chunk: any) => {
    try {
      res.header('Access-Control-Allow-Origin', '*');
      res.header(
        'Access-Control-Allow-Headers',
        'X-Requested-With,content-type',
      );
      res.header(
        'Access-Control-Allow-Methods',
        'GET, POST, OPTIONS, PUT, PATCH, DELETE',
      );
      res.header('Access-Control-Allow-Credentials', 'true');
      res.status(200);
      res.statusMessage = 'OK';
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      originalWrite.call(res, chunk);
      return true;
    }
    catch {
      return false;
    }
  };
}

function hasResponse(req: Request) {
  const mockResponse = mockedAsyncCalls[req.url];
  return !!mockResponse && !!mockResponse[req.method];
}

function onProxyRes(
  proxyRes: http.IncomingMessage,
  req: Request,
  res: Response,
) {
  let handled = false;
  const url = req.url;
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
      const response = mockedAsyncCalls[req.url][req.method];
      if (Array.isArray(response)) {
        const index = getCounter(req.url, req.method);
        let responseIndex = index;
        if (index > response.length - 1)
          responseIndex = response.length - 1;

        increaseCounter(req.url, req.method);
        return response[responseIndex];
      }
      return response;
    });
    handled = true;
  }

  if (handled)
    logger.info('Handled request:', req.method, req.url);
}

server.use(urlencoded({ extended: true }));
server.use(json());
server.use(
  createProxyMiddleware({
    target: backend,
    onProxyRes,
    onProxyReq,
    ws: true,
  }),
);

server.listen(port, () => {
  logger.log(`Proxy server is running at http://127.0.0.1:${port}`);
});
